"""Constants for the LANDI FT0360 integration."""

from typing import Final

DOMAIN: Final = "ft0360"

CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL: Final = 10
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

DEFAULT_REQUEST_TIMEOUT: Final = 5
MAX_RESPONSE_SIZE: Final = 1_048_576

ENDPOINT_RECORD: Final = "/client?command=record"
ENDPOINT_ABOUT: Final = "/client?command=about"
ENDPOINT_CONNECT_STATUS: Final = "/config?command=connect_status"
ENDPOINT_DEBUG: Final = "/config?command=debug"
ENDPOINT_FIRMWARE: Final = "/config?command=Firmware"

MANUFACTURER: Final = "LANDI"
MODEL: Final = "FT0360"
DEVICE_NAME: Final = "FT0360"

ATTR_BATTERY_MESSAGES: Final = "messages"
