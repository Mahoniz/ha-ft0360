"""Binary sensor platform for LANDI FT0360."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ATTR_BATTERY_MESSAGES
from .coordinator import FT0360Coordinator
from .entity import FT0360Entity

BATTERY_DESCRIPTION = BinarySensorEntityDescription(
    key="battery_low",
    translation_key="battery_low",
    device_class=BinarySensorDeviceClass.BATTERY,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the FT0360 battery status."""
    coordinator: FT0360Coordinator = entry.runtime_data
    async_add_entities([FT0360BatteryLowBinarySensor(coordinator, entry)])


class FT0360BatteryLowBinarySensor(FT0360Entity, BinarySensorEntity):
    """Report whether any station battery is low."""

    entity_description = BATTERY_DESCRIPTION

    def __init__(self, coordinator: FT0360Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        device_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{device_id}_battery_low"

    @property
    def available(self) -> bool:
        """Return whether the payload contains a recognized battery state."""
        return super().available and self.coordinator.data.record.battery_low is not None

    @property
    def is_on(self) -> bool | None:
        """Return True when the console reports a battery problem."""
        return self.coordinator.data.record.battery_low

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the original console battery messages for troubleshooting."""
        return {
            ATTR_BATTERY_MESSAGES: list(self.coordinator.data.record.battery_messages),
        }
