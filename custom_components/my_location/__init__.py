"""MY Location integration."""

from __future__ import annotations

import logging
import os
import ssl
from http import HTTPStatus
from typing import Any

import aiohttp
from aiohttp import web

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    OAuth2TokenRequestError,
    OAuth2TokenReauthError,
)
from homeassistant.helpers.aiohttp_client import (
    async_create_clientsession,
    async_get_clientsession,
)
from homeassistant.helpers.config_entry_oauth2_flow import (
    ImplementationUnavailableError,
    OAuth2Session,
    async_get_config_entry_implementation,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONF_BRIDGE_SECRET, CONF_CLIENT_CERT, CONF_CLIENT_KEY, FLEET_API_BASE

_LOGGER = logging.getLogger(__name__)

SIGNAL_LOCATION_UPDATE = "my_location_location_update_{}"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.DEVICE_TRACKER]


def _build_client_ssl_context(cert_path: str, key_path: str) -> ssl.SSLContext:
    """Build a TLS context that presents the MY Location client certificate.

    The server certificate is still verified against the default trust store,
    so tesla.lcars.qzz.io keeps validating via its public Let's Encrypt chain.
    The custom CA is only needed by the server to verify us, never by us.
    """
    context = ssl.create_default_context()
    context.load_cert_chain(cert_path, key_path)
    return context


async def async_create_telemetry_session(
    hass: HomeAssistant, entry: ConfigEntry
) -> tuple[aiohttp.ClientSession | None, str | None]:
    """Create the client-authenticated session used to reach tesla.lcars.qzz.io.

    Returns the session, or None when client authentication is not configured
    and the shared Home Assistant session should be used instead. The second
    element is a human-readable reason when client authentication was
    requested but could not be prepared.
    """
    cert_path = (entry.options.get(CONF_CLIENT_CERT) or "").strip()
    key_path = (entry.options.get(CONF_CLIENT_KEY) or "").strip()

    if not cert_path and not key_path:
        return None, None

    if not cert_path or not key_path:
        return None, "a client certificate and a client key must both be set"

    for path in (cert_path, key_path):
        if not await hass.async_add_executor_job(os.path.isfile, path):
            return None, f"file not found: {path}"

    try:
        ssl_context = await hass.async_add_executor_job(
            _build_client_ssl_context, cert_path, key_path
        )
    except (OSError, ValueError, ssl.SSLError) as err:
        return None, f"unable to load the client certificate ({err})"

    # Passing the SSL context as the second positional argument: it becomes the
    # connector's ssl= argument. auto_cleanup closes this with Home Assistant,
    # but we still close it on unload so a reload does not leak a connector.
    return async_create_clientsession(hass, ssl_context), None


async def async_reload_config_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry so option changes take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MY Location from a config entry."""
    try:
        implementation = await async_get_config_entry_implementation(hass, entry)
    except ImplementationUnavailableError as err:
        raise ConfigEntryNotReady("OAuth implementation unavailable") from err

    oauth_session = OAuth2Session(hass, entry, implementation)

    try:
        await oauth_session.async_ensure_token_valid()
    except OAuth2TokenRequestReauthError as err:
        raise ConfigEntryAuthFailed("Tesla authentication failed") from err
    except (aiohttp.ClientError, OAuth2TokenRequestError) as err:
        raise ConfigEntryNotReady("Unable to refresh Tesla OAuth token") from err

    websession = async_get_clientsession(hass)
    headers = {
        "Authorization": f"Bearer {oauth_session.token['access_token']}",
        "Accept": "application/json",
    }

    try:
        response = await websession.get(
            f"{FLEET_API_BASE}/api/1/vehicles",
            headers=headers,
        )
        if response.status == 401:
            raise ConfigEntryAuthFailed("Tesla rejected the OAuth token")
        response.raise_for_status()
        payload = await response.json()
    except ConfigEntryAuthFailed:
        raise
    except (aiohttp.ClientError, ValueError) as err:
        raise ConfigEntryNotReady("Unable to query Tesla Fleet API") from err

    vehicles = payload.get("response", [])
    if not isinstance(vehicles, list):
        raise ConfigEntryNotReady("Unexpected response from Tesla Fleet API")

    vins = [
        vehicle["vin"]
        for vehicle in vehicles
        if isinstance(vehicle, dict) and isinstance(vehicle.get("vin"), str)
    ]

    fleet_status: dict = {}
    fleet_status_error: str | None = None
    if vins:
        try:
            await oauth_session.async_ensure_token_valid()
            status_headers = {
                "Authorization": f"Bearer {oauth_session.token['access_token']}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            response = await websession.post(
                f"{FLEET_API_BASE}/api/1/vehicles/fleet_status",
                headers=status_headers,
                json={"vins": vins},
            )
            if response.status == 401:
                raise ConfigEntryAuthFailed("Tesla rejected the OAuth token")
            if response.status >= 400:
                fleet_status_error = f"HTTP {response.status}"
            else:
                status_payload = await response.json()
                status_response = status_payload.get("response", {})
                if isinstance(status_response, dict):
                    fleet_status = status_response
                else:
                    fleet_status_error = "Unexpected response"
        except ConfigEntryAuthFailed:
            raise
        except (aiohttp.ClientError, ValueError, OAuth2TokenRequestError) as err:
            fleet_status_error = type(err).__name__

    telemetry_session, telemetry_client_auth_error = (
        await async_create_telemetry_session(hass, entry)
    )
    if telemetry_client_auth_error:
        _LOGGER.warning(
            "Fleet Telemetry client authentication is unavailable: %s",
            telemetry_client_auth_error,
        )

    entry.runtime_data = {
        "oauth_session": oauth_session,
        "vehicles": vehicles,
        "fleet_status": fleet_status,
        "fleet_status_error": fleet_status_error,
        "telemetry_session": telemetry_session,
        "telemetry_client_auth_error": telemetry_client_auth_error,
    }

    # The config entry represents the Tesla Fleet API account/connection, not a
    # particular vehicle. New entries use the stable "Tesla Fleet" title.
    if entry.title == "MY Location":
        hass.config_entries.async_update_entry(entry, title="Tesla Fleet")

    if bridge_secret := entry.options.get(CONF_BRIDGE_SECRET):
        async def handle_location_webhook(
            hass: HomeAssistant, webhook_id: str, request: web.Request
        ) -> web.Response:
            """Receive a minimal location update from the VPS bridge."""
            try:
                data: dict[str, Any] = await request.json()
                latitude = float(data["latitude"])
                longitude = float(data["longitude"])
            except (KeyError, TypeError, ValueError):
                return web.json_response(
                    {"error": "invalid location payload"},
                    status=HTTPStatus.BAD_REQUEST,
                )

            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                return web.json_response(
                    {"error": "invalid coordinates"},
                    status=HTTPStatus.BAD_REQUEST,
                )

            async_dispatcher_send(
                hass,
                SIGNAL_LOCATION_UPDATE.format(entry.entry_id),
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "vin_last_4": data.get("vin_last_4"),
                    "timestamp": data.get("timestamp"),
                },
            )
            return web.json_response({"ok": True})

        webhook.async_register(
            hass,
            "my_location",
            f"{entry.title} Fleet Telemetry",
            bridge_secret,
            handle_location_webhook,
            local_only=False,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Registered last on purpose: the title migration above also calls
    # async_update_entry, and an earlier listener would turn that one-time
    # title change into an unnecessary reload of the whole entry.
    entry.async_on_unload(entry.add_update_listener(async_reload_config_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload MY Location."""
    if bridge_secret := entry.options.get(CONF_BRIDGE_SECRET):
        webhook.async_unregister(hass, bridge_secret)
    if isinstance(entry.runtime_data, dict):
        if (session := entry.runtime_data.get("telemetry_session")) is not None:
            await session.close()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
