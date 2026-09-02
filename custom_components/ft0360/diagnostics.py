"""Diagnostics support for LANDI FT0360."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .api import FT0360ApiError
from .coordinator import FT0360Coordinator

TO_REDACT = {
    CONF_HOST,
    "gateway",
    "gw",
    "ID",
    "ip",
    "ip_address",
    "Key",
    "mac",
    "MAC",
    "Password",
    "SSID",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator: FT0360Coordinator = entry.runtime_data
    station = coordinator.data.station
    firmware = coordinator.data.firmware
    connection = coordinator.data.connection
    try:
        debug = await coordinator.client.async_get_debug_info()
    except FT0360ApiError:
        # This undocumented endpoint is deliberately optional. Diagnostics must still
        # be downloadable on firmware versions that do not expose it.
        debug = None
    diagnostics = {
        "config": {
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "station": {
            "model": station.model,
            "firmware": station.firmware,
            "mac": station.mac,
        },
        "firmware": (
            {
                "version": firmware.version,
                "build": firmware.build,
            }
            if firmware is not None
            else None
        ),
        "connection": (
            {
                "status": connection.status,
                "status_code": connection.status_code,
                "wifi_signal_level": connection.wifi_signal_level,
                "ip_address": connection.ip_address,
                "gateway": connection.gateway,
                "mac": connection.mac,
            }
            if connection is not None
            else None
        ),
        "parsed": {
            "values": dict(coordinator.data.record.values),
            "battery_low": coordinator.data.record.battery_low,
            "battery_messages": coordinator.data.record.battery_messages,
        },
        "raw_record": dict(coordinator.data.record.raw),
        "raw_firmware": dict(firmware.raw) if firmware is not None else None,
        "raw_connection": dict(connection.raw) if connection is not None else None,
        "debug": (
            {
                "model": debug.model,
                "version": debug.version,
                "upload_status": list(debug.upload_status),
                "network_state": debug.network_state,
                "device_time": debug.device_time,
                "sync_time": debug.sync_time,
                "time_info": debug.time_info,
                "feature_enabled": debug.feature_enabled,
                "options": dict(debug.options),
            }
            if debug is not None
            else {"available": False}
        ),
        "raw_debug": dict(debug.raw) if debug is not None else None,
    }
    return async_redact_data(diagnostics, TO_REDACT)
