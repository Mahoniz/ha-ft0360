"""Shared FT0360 entity helpers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_SENSOR_SCOPE,
    DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SCOPE_ALL,
    SCOPE_INDOOR,
    SCOPE_OUTDOOR,
)
from .coordinator import FT0360Coordinator


class FT0360Entity(CoordinatorEntity[FT0360Coordinator]):
    """Base class for entities belonging to one FT0360 console."""

    _attr_has_entity_name = True

    @property
    def suggested_object_id(self) -> str:
        """Return a stable, readable default entity object ID."""
        return f"{DOMAIN}_{self.entity_description.key}"

    def __init__(self, coordinator: FT0360Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        station = coordinator.data.station
        identifier = entry.unique_id or station.mac or entry.entry_id
        scope = entry.data.get(CONF_SENSOR_SCOPE, SCOPE_ALL)
        connections = (
            {(CONNECTION_NETWORK_MAC, station.mac)}
            if station.mac is not None and scope == SCOPE_ALL
            else set()
        )
        firmware = coordinator.data.firmware
        sw_version = firmware.version if firmware is not None else None
        sw_version = sw_version or station.firmware
        if firmware is not None and firmware.build is not None:
            sw_version = (
                f"{sw_version} (build {firmware.build})"
                if sw_version is not None
                else f"build {firmware.build}"
            )
        device_name = {
            SCOPE_INDOOR: "FT0360 Innenstation",
            SCOPE_OUTDOOR: "FT0360 Aussenstation",
        }.get(scope, DEVICE_NAME)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            connections=connections,
            name=device_name,
            manufacturer=MANUFACTURER,
            model=station.model or MODEL,
            sw_version=sw_version,
            configuration_url=coordinator.client.base_url,
        )
