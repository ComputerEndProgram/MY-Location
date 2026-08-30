"""Sensor platform for MY Location."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MY Location diagnostic sensors."""
    vehicles = entry.runtime_data.get("vehicles", [])
    async_add_entities(MyLocationVehicleSensor(entry, vehicle) for vehicle in vehicles)


class MyLocationVehicleSensor(SensorEntity):
    """Diagnostic sensor proving Fleet API vehicle access."""

    _attr_has_entity_name = True
    _attr_name = "Fleet API vehicle"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:car-connected"

    def __init__(self, entry: ConfigEntry, vehicle: dict[str, Any]) -> None:
        """Initialize the vehicle sensor."""
        self._vehicle = vehicle
        identifier = (
            vehicle.get("id_s")
            or vehicle.get("vehicle_id")
            or vehicle.get("id")
            or vehicle.get("vin")
            or entry.entry_id
        )
        self._attr_unique_id = f"{identifier}_fleet_api_vehicle"

    @property
    def native_value(self) -> str:
        """Return the vehicle's display name."""
        return self._vehicle.get("display_name") or "Vehicle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return non-sensitive diagnostic attributes."""
        vin = self._vehicle.get("vin")
        attributes: dict[str, Any] = {}
        if state := self._vehicle.get("state"):
            attributes["fleet_state"] = state
        if isinstance(vin, str) and len(vin) >= 4:
            attributes["vin_last_4"] = vin[-4:]
        return attributes
