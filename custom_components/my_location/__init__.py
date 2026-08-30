"""MY Location integration."""

from __future__ import annotations

import aiohttp

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

from .const import FLEET_API_BASE

PLATFORMS: list[Platform] = [Platform.SENSOR]


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
    try:
        response = await websession.get(
            f"{FLEET_API_BASE}/api/1/vehicles",
            headers={
                "Authorization": f"Bearer {oauth_session.token['access_token']}",
                "Accept": "application/json",
            },
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

    entry.runtime_data = {
        "oauth_session": oauth_session,
        "vehicles": vehicles,
    }

    if len(vehicles) == 1:
        display_name = vehicles[0].get("display_name") or "MY Location"
        if entry.title != display_name:
            hass.config_entries.async_update_entry(entry, title=display_name)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload MY Location."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
