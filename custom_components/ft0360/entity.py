"""Shared FT0360 entity helpers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL
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
        identifier = station.mac or entry.unique_id or entry.entry_id
        connections = (
            {(CONNECTION_NETWORK_MAC, station.mac)} if station.mac is not None else set()
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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            connections=connections,
            name=DEVICE_NAME,
            manufacturer=MANUFACTURER,
            model=station.model or MODEL,
            sw_version=sw_version,
            configuration_url=coordinator.client.base_url,
        )
