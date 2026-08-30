"""MY Location integration."""

from __future__ import annotations

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
    OAuth2TokenRequestReauthError,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import (
    ImplementationUnavailableError,
    OAuth2Session,
    async_get_config_entry_implementation,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import FLEET_API_BASE

CONF_BRIDGE_SECRET = "bridge_secret"
SIGNAL_LOCATION_UPDATE = "my_location_location_update_{}"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.DEVICE_TRACKER]


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

    entry.runtime_data = {
        "oauth_session": oauth_session,
        "vehicles": vehicles,
        "fleet_status": fleet_status,
        "fleet_status_error": fleet_status_error,
    }

    if len(vehicles) == 1:
        display_name = vehicles[0].get("display_name") or "MY Location"
        if entry.title != display_name:
            hass.config_entries.async_update_entry(entry, title=display_name)

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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload MY Location."""
    if bridge_secret := entry.options.get(CONF_BRIDGE_SECRET):
        webhook.async_unregister(hass, bridge_secret)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
