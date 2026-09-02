"""Sensor platform for LANDI FT0360."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    EntityCategory,
    PERCENTAGE,
    UnitOfIrradiance,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FT0360Coordinator, FT0360Data
from .entity import FT0360Entity
from .parser import CARDINAL_DIRECTIONS, CONNECTION_STATUS_OPTIONS, degrees_to_cardinal


@dataclass(frozen=True, kw_only=True)
class FT0360SensorEntityDescription(SensorEntityDescription):
    """Describe an FT0360 numeric sensor."""


@dataclass(frozen=True, kw_only=True)
class FT0360DiagnosticSensorEntityDescription(SensorEntityDescription):
    """Describe an FT0360 diagnostic sensor."""

    value_fn: Callable[[FT0360Data], str | int | None]


SENSOR_DESCRIPTIONS: tuple[FT0360SensorEntityDescription, ...] = (
    FT0360SensorEntityDescription(
        key="indoor_temperature",
        translation_key="indoor_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="indoor_humidity",
        translation_key="indoor_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    FT0360SensorEntityDescription(
        key="outdoor_temperature",
        translation_key="outdoor_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="outdoor_humidity",
        translation_key="outdoor_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    FT0360SensorEntityDescription(
        key="pressure_absolute",
        translation_key="pressure_absolute",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="pressure_relative",
        translation_key="pressure_relative",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="max_daily_gust",
        translation_key="max_daily_gust",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="wind_speed",
        translation_key="wind_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="wind_gust",
        translation_key="wind_gust",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="wind_direction",
        translation_key="wind_direction",
        native_unit_of_measurement=DEGREE,
        device_class=SensorDeviceClass.WIND_DIRECTION,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        suggested_display_precision=0,
    ),
    FT0360SensorEntityDescription(
        key="wind_average_2_minute",
        translation_key="wind_average_2_minute",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="wind_direction_average_2_minute",
        translation_key="wind_direction_average_2_minute",
        native_unit_of_measurement=DEGREE,
        device_class=SensorDeviceClass.WIND_DIRECTION,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        suggested_display_precision=0,
    ),
    FT0360SensorEntityDescription(
        key="wind_average_10_minute",
        translation_key="wind_average_10_minute",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="wind_direction_average_10_minute",
        translation_key="wind_direction_average_10_minute",
        native_unit_of_measurement=DEGREE,
        device_class=SensorDeviceClass.WIND_DIRECTION,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        suggested_display_precision=0,
    ),
    FT0360SensorEntityDescription(
        key="rain_rate",
        translation_key="rain_rate",
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="rain_hour",
        translation_key="rain_hour",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="rain_day",
        translation_key="rain_day",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="rain_week",
        translation_key="rain_week",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="rain_month",
        translation_key="rain_month",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="rain_year",
        translation_key="rain_year",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="rain_total",
        translation_key="rain_total",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="solar_radiation",
        translation_key="solar_radiation",
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    FT0360SensorEntityDescription(
        key="uv_index",
        translation_key="uv_index",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
)

CARDINAL_DESCRIPTION = SensorEntityDescription(
    key="wind_direction_cardinal",
    translation_key="wind_direction_cardinal",
)

DIAGNOSTIC_SENSOR_DESCRIPTIONS: tuple[
    FT0360DiagnosticSensorEntityDescription, ...
] = (
    FT0360DiagnosticSensorEntityDescription(
        key="connection_status",
        translation_key="connection_status",
        device_class=SensorDeviceClass.ENUM,
        options=list(CONNECTION_STATUS_OPTIONS),
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.connection.status if data.connection is not None else None
        ),
    ),
    FT0360DiagnosticSensorEntityDescription(
        key="wifi_signal_level",
        translation_key="wifi_signal_level",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.connection.wifi_signal_level if data.connection is not None else None
        ),
    ),
    FT0360DiagnosticSensorEntityDescription(
        key="ip_address",
        translation_key="ip_address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.connection.ip_address if data.connection is not None else None
        ),
    ),
    FT0360DiagnosticSensorEntityDescription(
        key="gateway",
        translation_key="gateway",
        icon="mdi:router-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.connection.gateway if data.connection is not None else None
        ),
    ),
    FT0360DiagnosticSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.firmware.version
            if data.firmware is not None and data.firmware.version is not None
            else data.station.firmware
        ),
    ),
    FT0360DiagnosticSensorEntityDescription(
        key="firmware_build",
        translation_key="firmware_build",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.firmware.build if data.firmware is not None else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FT0360 sensors."""
    coordinator: FT0360Coordinator = entry.runtime_data
    async_add_entities(
        [FT0360Sensor(coordinator, entry, description) for description in SENSOR_DESCRIPTIONS]
        + [FT0360CardinalDirectionSensor(coordinator, entry)]
        + [
            FT0360DiagnosticSensor(coordinator, entry, description)
            for description in DIAGNOSTIC_SENSOR_DESCRIPTIONS
        ]
    )


class FT0360Sensor(FT0360Entity, SensorEntity):
    """One numeric reading from the station."""

    entity_description: FT0360SensorEntityDescription

    def __init__(
        self,
        coordinator: FT0360Coordinator,
        entry: ConfigEntry,
        description: FT0360SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        device_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Return whether this individual reading is present."""
        return (
            super().available
            and self.entity_description.key in self.coordinator.data.record.values
        )

    @property
    def native_value(self) -> float | None:
        """Return the normalized numeric value."""
        return self.coordinator.data.record.values.get(self.entity_description.key)


class FT0360CardinalDirectionSensor(FT0360Entity, SensorEntity):
    """Wind direction as the station's 8-point compass value."""

    entity_description = CARDINAL_DESCRIPTION
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(CARDINAL_DIRECTIONS)

    def __init__(self, coordinator: FT0360Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        device_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{device_id}_wind_direction_cardinal"

    @property
    def available(self) -> bool:
        """Return whether wind direction is present."""
        return super().available and "wind_direction" in self.coordinator.data.record.values

    @property
    def native_value(self) -> str | None:
        """Return a compass direction translation key."""
        return degrees_to_cardinal(self.coordinator.data.record.values.get("wind_direction"))


class FT0360DiagnosticSensor(FT0360Entity, SensorEntity):
    """Expose read-only station metadata and network diagnostics."""

    entity_description: FT0360DiagnosticSensorEntityDescription

    def __init__(
        self,
        coordinator: FT0360Coordinator,
        entry: ConfigEntry,
        description: FT0360DiagnosticSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        device_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Return whether this diagnostic value is present."""
        return super().available and self.native_value is not None

    @property
    def native_value(self) -> str | int | None:
        """Return the current diagnostic value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the numeric console status code for troubleshooting."""
        if self.entity_description.key != "connection_status":
            return None
        connection = self.coordinator.data.connection
        if connection is None:
            return None
        return {"status_code": connection.status_code}
