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
    entities: list[SensorEntity] = []

    for vehicle in vehicles:
        entities.append(MyLocationVehicleSensor(entry, vehicle))
        entities.append(MyLocationVirtualKeySensor(entry, vehicle))

    async_add_entities(entities)


class MyLocationVehicleSensor(SensorEntity):
    """Diagnostic sensor proving Fleet API vehicle access."""

    _attr_has_entity_name = True
    _attr_name = "Fleet API vehicle"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:car-connected"

    def __init__(self, entry: ConfigEntry, vehicle: dict[str, Any]) -> None:
        """Initialize the vehicle sensor."""
        self._vehicle = vehicle
        self._attr_unique_id = f"{_vehicle_identifier(entry, vehicle)}_fleet_api_vehicle"

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


class MyLocationVirtualKeySensor(SensorEntity):
    """Diagnostic sensor for Tesla virtual-key pairing state."""

    _attr_has_entity_name = True
    _attr_name = "Virtual key"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:key-wireless"

    def __init__(self, entry: ConfigEntry, vehicle: dict[str, Any]) -> None:
        """Initialize the virtual-key sensor."""
        self._entry = entry
        self._vehicle = vehicle
        self._attr_unique_id = f"{_vehicle_identifier(entry, vehicle)}_virtual_key"

    @property
    def native_value(self) -> str:
        """Return paired, unpaired, or unknown."""
        vin = self._vehicle.get("vin")
        status = self._entry.runtime_data.get("fleet_status", {})

        if isinstance(vin, str):
            paired = status.get("key_paired_vins", [])
            unpaired = status.get("unpaired_vins", [])
            if vin in paired:
                return "paired"
            if vin in unpaired:
                return "unpaired"

        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Fleet Telemetry compatibility diagnostics."""
        vin = self._vehicle.get("vin")
        status = self._entry.runtime_data.get("fleet_status", {})
        attributes: dict[str, Any] = {}

        if isinstance(vin, str):
            info = status.get("vehicle_info", {}).get(vin, {})
            if isinstance(info, dict):
                for key in (
                    "firmware_version",
                    "fleet_telemetry_version",
                    "vehicle_command_protocol_required",
                    "total_number_of_keys",
                    "discounted_device_data",
                ):
                    if key in info and info[key] is not None:
                        attributes[key] = info[key]

            if len(vin) >= 4:
                attributes["vin_last_4"] = vin[-4:]

        if error := self._entry.runtime_data.get("fleet_status_error"):
            attributes["fleet_status_error"] = error

        return attributes


def _vehicle_identifier(entry: ConfigEntry, vehicle: dict[str, Any]) -> str:
    """Return a stable identifier for a vehicle entity."""
    return str(
        vehicle.get("id_s")
        or vehicle.get("vehicle_id")
        or vehicle.get("id")
        or vehicle.get("vin")
        or entry.entry_id
    )
