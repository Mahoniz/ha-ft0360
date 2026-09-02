"""Parse the local LANDI FT0360 JSON format.

The console exposes human-facing labels and units rather than stable machine keys.
Parsing therefore uses normalized section/item labels first and the known positions as
a fallback. Unit strings are deliberately ignored because some firmware/browser
combinations expose them as mojibake (for example ``Â°C`` or ``w/mÂ²``).
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping


class FT0360ParseError(ValueError):
    """Raised when a response is not an FT0360 record payload."""


@dataclass(frozen=True)
class FT0360StationInfo:
    """Static information returned by the about endpoint."""

    model: str | None
    firmware: str | None
    mac: str | None


@dataclass(frozen=True)
class FT0360FirmwareInfo:
    """Firmware information returned by the config endpoint."""

    version: str | None
    build: str | None
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class FT0360ConnectionInfo:
    """Network state returned by the config endpoint."""

    status_code: int | None
    status: str
    wifi_signal_level: int | None
    ip_address: str | None
    gateway: str | None
    mac: str | None
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class FT0360DebugInfo:
    """Optional metadata returned by the hidden debug endpoint."""

    model: str | None
    version: str | None
    upload_status: tuple[Mapping[str, Any], ...]
    network_state: int | None
    device_time: str | None
    sync_time: str | None
    time_info: str | None
    feature_enabled: bool | None
    options: Mapping[str, str | None]
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class FT0360Record:
    """Normalized readings from one record response."""

    values: Mapping[str, float]
    battery_low: bool | None
    battery_messages: tuple[str, ...]
    raw: Mapping[str, Any]


_NUMBER_PATTERN = re.compile(r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][-+]?\d+)?")

_SECTION_ALIASES = {
    "indoor": "indoor",
    "innen": "indoor",
    "outdoor": "outdoor",
    "aussen": "outdoor",
    "pressure": "pressure",
    "luftdruck": "pressure",
    "windspeed": "wind",
    "wind": "wind",
    "rainfall": "rain",
    "rain": "rain",
    "regen": "rain",
    "solar": "solar",
}

_POSITIONAL_SECTIONS = ("indoor", "outdoor", "pressure", "wind", "rain", "solar")

_POSITIONAL_ITEMS: dict[str, tuple[str, ...]] = {
    "indoor": ("indoor_temperature", "indoor_humidity"),
    "outdoor": ("outdoor_temperature", "outdoor_humidity"),
    "pressure": ("pressure_absolute", "pressure_relative"),
    "wind": (
        "max_daily_gust",
        "wind_speed",
        "wind_gust",
        "wind_direction",
        "wind_average_2_minute",
        "wind_direction_average_2_minute",
        "wind_average_10_minute",
        "wind_direction_average_10_minute",
    ),
    "rain": (
        "rain_rate",
        "rain_hour",
        "rain_day",
        "rain_week",
        "rain_month",
        "rain_year",
        "rain_total",
    ),
    "solar": ("solar_radiation", "uv_index"),
}

_ITEM_ALIASES: dict[tuple[str, str], str] = {
    ("indoor", "temperature"): "indoor_temperature",
    ("indoor", "temperatur"): "indoor_temperature",
    ("indoor", "humidity"): "indoor_humidity",
    ("indoor", "feuchtigkeit"): "indoor_humidity",
    ("outdoor", "temperature"): "outdoor_temperature",
    ("outdoor", "temperatur"): "outdoor_temperature",
    ("outdoor", "humidity"): "outdoor_humidity",
    ("outdoor", "feuchtigkeit"): "outdoor_humidity",
    ("pressure", "absolute"): "pressure_absolute",
    ("pressure", "absolut"): "pressure_absolute",
    ("pressure", "relative"): "pressure_relative",
    ("pressure", "relativ"): "pressure_relative",
    ("wind", "maxdailygust"): "max_daily_gust",
    ("wind", "maximaletagesboe"): "max_daily_gust",
    ("wind", "wind"): "wind_speed",
    ("wind", "windspeed"): "wind_speed",
    ("wind", "windgeschwindigkeit"): "wind_speed",
    ("wind", "gust"): "wind_gust",
    ("wind", "boe"): "wind_gust",
    ("wind", "windboe"): "wind_gust",
    ("wind", "direction"): "wind_direction",
    ("wind", "richtung"): "wind_direction",
    ("wind", "windaverage2minute"): "wind_average_2_minute",
    ("wind", "winddurchschnitt2minuten"): "wind_average_2_minute",
    ("wind", "directionaverage2minute"): "wind_direction_average_2_minute",
    ("wind", "richtungsdurchschnitt2minuten"): "wind_direction_average_2_minute",
    ("wind", "windaverage10minute"): "wind_average_10_minute",
    ("wind", "winddurchschnitt10minuten"): "wind_average_10_minute",
    ("wind", "directionaverage10minute"): "wind_direction_average_10_minute",
    ("wind", "richtungsdurchschnitt10minuten"): "wind_direction_average_10_minute",
    ("rain", "rate"): "rain_rate",
    ("rain", "regenrate"): "rain_rate",
    ("rain", "hour"): "rain_hour",
    ("rain", "stunde"): "rain_hour",
    ("rain", "day"): "rain_day",
    ("rain", "tag"): "rain_day",
    ("rain", "week"): "rain_week",
    ("rain", "woche"): "rain_week",
    ("rain", "month"): "rain_month",
    ("rain", "monat"): "rain_month",
    ("rain", "year"): "rain_year",
    ("rain", "jahr"): "rain_year",
    ("rain", "total"): "rain_total",
    ("rain", "gesamt"): "rain_total",
    ("solar", "light"): "solar_radiation",
    ("solar", "solarstrahlung"): "solar_radiation",
    ("solar", "uvi"): "uv_index",
    ("solar", "uvindex"): "uv_index",
}

_DIRECTION_KEYS = {
    "wind_direction",
    "wind_direction_average_2_minute",
    "wind_direction_average_10_minute",
}

CARDINAL_DIRECTIONS: tuple[str, ...] = (
    "n",
    "ne",
    "e",
    "se",
    "s",
    "sw",
    "w",
    "nw",
)

CONNECTION_STATUS_OPTIONS: tuple[str, ...] = (
    "idle",
    "connecting",
    "wrong_password",
    "router_not_found",
    "connection_failed",
    "connected",
    "unknown",
)

_CONNECTION_STATUS = {
    0: "idle",
    1: "connecting",
    2: "wrong_password",
    3: "router_not_found",
    4: "connection_failed",
    5: "connected",
}


def _normalize_label(value: Any) -> str:
    """Normalize labels without depending on correctly decoded unit glyphs."""
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    text = "".join(character for character in text if not unicodedata.combining(character))
    return "".join(character for character in text if character.isalnum())


def _as_float(value: Any) -> float | None:
    """Extract a finite number from a console value."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None

    match = _NUMBER_PATTERN.search(str(value).strip())
    if match is None:
        return None
    try:
        number = float(match.group(0).replace(",", "."))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _as_int(value: Any) -> int | None:
    """Return an integer for an integral console value."""
    number = _as_float(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _as_optional_text(value: Any) -> str | None:
    """Return a stripped text value when present."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_nullable_text(value: Any) -> str | None:
    """Treat the console's literal NULL placeholders as missing values."""
    text = _as_optional_text(value)
    if text is None or text.casefold() in {"null", "none"}:
        return None
    return text


def _battery_state(messages: tuple[str, ...]) -> bool | None:
    """Return True for a battery problem, False for explicitly healthy."""
    if not messages:
        return None

    text = " ".join(_normalize_label(message) for message in messages)
    problem_tokens = (
        "low",
        "weak",
        "bad",
        "empty",
        "replace",
        "schwach",
        "leer",
        "niedrig",
        "wechseln",
    )
    if any(token in text for token in problem_tokens):
        return True

    healthy_tokens = ("allbatteryareok", "batteryok", "batteriesok", "batterieok")
    if any(token in text for token in healthy_tokens):
        return False
    return None


def _find_battery_messages(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Find battery messages even if the top-level key changes in case."""
    battery: Any = None
    for key, value in payload.items():
        if _normalize_label(key) == "battery":
            battery = value
            break

    if isinstance(battery, Mapping):
        battery = battery.get("list")
    if not isinstance(battery, (list, tuple)):
        return ()
    return tuple(str(message).strip() for message in battery if str(message).strip())


def parse_record(payload: Mapping[str, Any]) -> FT0360Record:
    """Parse and validate a ``command=record`` response."""
    if not isinstance(payload, Mapping):
        raise FT0360ParseError("The record response is not a JSON object")

    sections: Any = None
    for key, value in payload.items():
        if _normalize_label(key) == "sensor":
            sections = value
            break
    if not isinstance(sections, list) or not sections:
        raise FT0360ParseError("The record response has no Sensor list")

    values: dict[str, float] = {}
    recognized: set[str] = set()

    for section_index, section in enumerate(sections):
        if not isinstance(section, Mapping):
            continue

        section_name = _SECTION_ALIASES.get(_normalize_label(section.get("title", "")))
        if section_name is None and section_index < len(_POSITIONAL_SECTIONS):
            section_name = _POSITIONAL_SECTIONS[section_index]
        if section_name is None:
            continue

        items = section.get("list")
        if not isinstance(items, list):
            continue

        positional_keys = _POSITIONAL_ITEMS.get(section_name, ())
        for item_index, item in enumerate(items):
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue

            reading_key = _ITEM_ALIASES.get((section_name, _normalize_label(item[0])))
            if reading_key is None and item_index < len(positional_keys):
                reading_key = positional_keys[item_index]
            if reading_key is None:
                continue

            recognized.add(reading_key)
            number = _as_float(item[1])
            if number is None:
                continue
            if reading_key in _DIRECTION_KEYS:
                number %= 360
            values[reading_key] = number

    if not recognized:
        raise FT0360ParseError("The Sensor list contains no recognized FT0360 readings")

    battery_messages = _find_battery_messages(payload)
    return FT0360Record(
        values=values,
        battery_low=_battery_state(battery_messages),
        battery_messages=battery_messages,
        raw=dict(payload),
    )


def parse_station_info(payload: Mapping[str, Any]) -> FT0360StationInfo:
    """Parse the ``command=about`` response."""
    if not isinstance(payload, Mapping):
        raise FT0360ParseError("The about response is not a JSON object")

    normalized = {_normalize_label(key): value for key, value in payload.items()}
    model = str(normalized.get("model") or "").strip() or None
    firmware = str(normalized.get("version") or "").strip() or None
    mac = normalize_mac(normalized.get("mac"))
    return FT0360StationInfo(model=model, firmware=firmware, mac=mac)


def parse_firmware_info(payload: Mapping[str, Any]) -> FT0360FirmwareInfo:
    """Parse the read-only ``command=Firmware`` response."""
    if not isinstance(payload, Mapping):
        raise FT0360ParseError("The firmware response is not a JSON object")

    firmware: Any = None
    for key, value in payload.items():
        if _normalize_label(key) == "firmware":
            firmware = value
            break
    if not isinstance(firmware, Mapping):
        raise FT0360ParseError("The firmware response has no Firmware object")

    normalized = {_normalize_label(key): value for key, value in firmware.items()}
    version = _as_optional_text(normalized.get("version"))
    build = _as_optional_text(normalized.get("build"))
    if version is None and build is None:
        raise FT0360ParseError("The Firmware object contains no version or build")
    return FT0360FirmwareInfo(version=version, build=build, raw=dict(payload))


def parse_connection_info(payload: Mapping[str, Any]) -> FT0360ConnectionInfo:
    """Parse the read-only ``command=connect_status`` response."""
    if not isinstance(payload, Mapping):
        raise FT0360ParseError("The connection response is not a JSON object")

    ip_config: Any = None
    for key, value in payload.items():
        if _normalize_label(key) == "ipconfig":
            ip_config = value
            break
    if not isinstance(ip_config, Mapping):
        raise FT0360ParseError("The connection response has no IPConfig object")

    normalized = {_normalize_label(key): value for key, value in ip_config.items()}
    status_code = _as_int(normalized.get("status"))
    signal_level = _as_int(normalized.get("rssi"))
    return FT0360ConnectionInfo(
        status_code=status_code,
        status=_CONNECTION_STATUS.get(status_code, "unknown"),
        wifi_signal_level=signal_level,
        ip_address=_as_optional_text(normalized.get("ip")),
        gateway=_as_optional_text(normalized.get("gw")),
        mac=normalize_mac(normalized.get("mac")),
        raw=dict(payload),
    )


def parse_debug_info(payload: Mapping[str, Any]) -> FT0360DebugInfo:
    """Parse the optional read-only ``command=debug`` response."""
    if not isinstance(payload, Mapping):
        raise FT0360ParseError("The debug response is not a JSON object")

    normalized = {_normalize_label(key): value for key, value in payload.items()}
    known_keys = {
        "model",
        "version",
        "uploadstatus",
        "net",
        "ostime",
        "synctime",
        "timeinfo",
        "feature",
        "option",
    }
    if not known_keys.intersection(normalized):
        raise FT0360ParseError("The debug response contains no recognized fields")

    upload_status: list[Mapping[str, Any]] = []
    raw_upload_status = normalized.get("uploadstatus")
    if isinstance(raw_upload_status, list):
        for item in raw_upload_status:
            if not isinstance(item, Mapping):
                continue
            normalized_item = {
                _normalize_label(key): value for key, value in item.items()
            }
            upload_status.append(
                {
                    "serial": _as_int(normalized_item.get("serial")),
                    "code": _as_int(normalized_item.get("code")),
                    "message": _as_optional_text(normalized_item.get("message")),
                    "website": _as_optional_text(normalized_item.get("website")),
                    "time": _as_optional_text(normalized_item.get("time")),
                }
            )

    options: dict[str, str | None] = {}
    raw_options = normalized.get("option")
    if isinstance(raw_options, Mapping):
        normalized_options = {
            _normalize_label(key): value for key, value in raw_options.items()
        }
        for key in ("nation", "transmitter", "position", "pairing"):
            options[key] = _as_nullable_text(normalized_options.get(key))

    feature = normalized.get("feature")
    return FT0360DebugInfo(
        model=_as_optional_text(normalized.get("model")),
        version=_as_optional_text(normalized.get("version")),
        upload_status=tuple(upload_status),
        network_state=_as_int(normalized.get("net")),
        device_time=_as_optional_text(normalized.get("ostime")),
        sync_time=_as_optional_text(normalized.get("synctime")),
        time_info=_as_optional_text(normalized.get("timeinfo")),
        feature_enabled=feature if isinstance(feature, bool) else None,
        options=options,
        raw=dict(payload),
    )


def normalize_mac(value: Any) -> str | None:
    """Return a lower-case colon-separated MAC address when valid."""
    if value is None:
        return None
    compact = re.sub(r"[^0-9a-fA-F]", "", str(value))
    if len(compact) != 12:
        return None
    return ":".join(compact[index : index + 2] for index in range(0, 12, 2)).lower()


def degrees_to_cardinal(value: float | None) -> str | None:
    """Convert degrees to the station's specified 8-point compass direction."""
    if value is None or not math.isfinite(value):
        return None
    index = int(((value % 360) + 22.5) // 45) % 8
    return CARDINAL_DIRECTIONS[index]
