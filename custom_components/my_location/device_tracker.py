"""Device tracker platform for MY Location."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityStateAttribute
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import SIGNAL_LOCATION_UPDATE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MY Location device trackers."""
    vehicles = entry.runtime_data.get("vehicles", [])
    async_add_entities(
        MyLocationDeviceTracker(entry, vehicle)
        for vehicle in vehicles
        if isinstance(vehicle, dict) and isinstance(vehicle.get("vin"), str)
    )


class MyLocationDeviceTracker(TrackerEntity, RestoreEntity):
    """Represent the vehicle's Fleet Telemetry location."""

    _attr_has_entity_name = True
    _attr_name = "Location"
    _attr_icon = "mdi:car-marker"

    def __init__(self, entry: ConfigEntry, vehicle: dict[str, Any]) -> None:
        """Initialize the tracker."""
        self._entry = entry
        self._vehicle = vehicle
        self._vin = vehicle["vin"]
        self._attr_unique_id = f"{self._vin}_location"
        self._attr_latitude = None
        self._attr_longitude = None
        self._last_update = None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return minimal diagnostic attributes."""
        attrs: dict[str, Any] = {"vin_last_4": self._vin[-4:]}
        if self._last_update is not None:
            attrs["telemetry_timestamp"] = self._last_update
        return attrs

    async def async_added_to_hass(self) -> None:
        """Restore the last location and subscribe to webhook updates."""
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            self._attr_latitude = state.attributes.get(EntityStateAttribute.LATITUDE)
            self._attr_longitude = state.attributes.get(EntityStateAttribute.LONGITUDE)
            self._last_update = state.attributes.get("telemetry_timestamp")

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_LOCATION_UPDATE.format(self._entry.entry_id),
                self._handle_location,
            )
        )

    @callback
    def _handle_location(self, data: dict[str, Any]) -> None:
        """Apply a Fleet Telemetry location update."""
        vin_last_4 = data.get("vin_last_4")
        if vin_last_4 and vin_last_4 != self._vin[-4:]:
            return

        self._attr_latitude = data["latitude"]
        self._attr_longitude = data["longitude"]
        self._last_update = data.get("timestamp")
        self.async_write_ha_state()
