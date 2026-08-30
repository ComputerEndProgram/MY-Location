"""Button platform for MY Location."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, OAuth2TokenRequestError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

_LOGGER = logging.getLogger(__name__)

TELEMETRY_HOSTNAME = "tesla.lcars.qzz.io"
TELEMETRY_PORT = 4443
TELEMETRY_CA_URL = (
    "https://tesla.lcars.qzz.io/.well-known/my-location/telemetry-ca.pem"
)
TELEMETRY_CONFIG_PROXY_URL = (
    "https://tesla.lcars.qzz.io/api/1/vehicles/fleet_telemetry_config"
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MY Location buttons."""
    vehicles = entry.runtime_data.get("vehicles", [])
    async_add_entities(
        MyLocationConfigureTelemetryButton(entry, vehicle)
        for vehicle in vehicles
        if isinstance(vehicle, dict) and isinstance(vehicle.get("vin"), str)
    )


class MyLocationConfigureTelemetryButton(ButtonEntity):
    """Configure minimal Fleet Telemetry for a vehicle."""

    _attr_has_entity_name = True
    _attr_name = "Configure telemetry"
    _attr_icon = "mdi:satellite-uplink"

    def __init__(self, entry: ConfigEntry, vehicle: dict[str, Any]) -> None:
        """Initialize the button."""
        self._entry = entry
        self._vehicle = vehicle
        self._vin = vehicle["vin"]
        identifier = (
            vehicle.get("id_s")
            or vehicle.get("vehicle_id")
            or vehicle.get("id")
            or self._vin
        )
        self._attr_unique_id = f"{identifier}_configure_telemetry"

    async def async_press(self) -> None:
        """Push the minimal Fleet Telemetry configuration through the command proxy."""
        oauth_session = self._entry.runtime_data["oauth_session"]

        try:
            await oauth_session.async_ensure_token_valid()
        except (aiohttp.ClientError, OAuth2TokenRequestError) as err:
            raise HomeAssistantError("Unable to refresh Tesla OAuth token") from err

        websession = async_get_clientsession(self.hass)

        try:
            ca_response = await websession.get(TELEMETRY_CA_URL)
            ca_response.raise_for_status()
            ca_chain = await ca_response.text()
        except aiohttp.ClientError as err:
            raise HomeAssistantError(
                "Unable to fetch the Fleet Telemetry certificate chain"
            ) from err

        if "BEGIN CERTIFICATE" not in ca_chain:
            raise HomeAssistantError("Fleet Telemetry certificate chain is invalid")

        payload = {
            "vins": [self._vin],
            "config": {
                "hostname": TELEMETRY_HOSTNAME,
                "port": TELEMETRY_PORT,
                "ca": ca_chain,
                "fields": {
                    "Location": {
                        "interval_seconds": 2,
                        "minimum_delta": 5,
                    }
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {oauth_session.token['access_token']}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            response = await websession.post(
                TELEMETRY_CONFIG_PROXY_URL,
                headers=headers,
                json=payload,
            )
            response_text = await response.text()
            if response.status >= 400:
                raise HomeAssistantError(
                    f"Tesla telemetry configuration failed: HTTP {response.status}: "
                    f"{response_text[:300]}"
                )
            result = await response.json(content_type=None)
        except HomeAssistantError:
            raise
        except (aiohttp.ClientError, ValueError) as err:
            raise HomeAssistantError(
                "Unable to send the Fleet Telemetry configuration"
            ) from err

        response_data = result.get("response", {}) if isinstance(result, dict) else {}
        updated = response_data.get("updated_vehicles")
        skipped = response_data.get("skipped_vehicles")
        _LOGGER.info(
            "Fleet Telemetry configuration result for vehicle ending %s: updated=%s skipped=%s",
            self._vin[-4:],
            updated,
            skipped,
        )

        if updated == 0:
            raise HomeAssistantError(
                f"Tesla did not update the vehicle telemetry configuration: {skipped}"
            )
