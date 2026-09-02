"""Data update coordinator for LANDI FT0360."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FT0360ApiError, FT0360Client
from .const import DOMAIN
from .parser import (
    FT0360ConnectionInfo,
    FT0360FirmwareInfo,
    FT0360Record,
    FT0360StationInfo,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FT0360Data:
    """All data shared by FT0360 entities."""

    station: FT0360StationInfo
    firmware: FT0360FirmwareInfo | None
    connection: FT0360ConnectionInfo | None
    record: FT0360Record


class FT0360Coordinator(DataUpdateCoordinator[FT0360Data]):
    """Poll the record endpoint once for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: FT0360Client,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self.client = client
        self.station: FT0360StationInfo | None = None
        self.firmware: FT0360FirmwareInfo | None = None

    async def _async_setup(self) -> None:
        """Fetch static device information once during setup."""
        try:
            self.station = await self.client.async_get_about()
        except FT0360ApiError as err:
            raise UpdateFailed(f"Could not read FT0360 device information: {err}") from err

        try:
            self.firmware = await self.client.async_get_firmware_info()
        except FT0360ApiError as err:
            # The weather endpoint works on some firmware variants that do not expose
            # this optional diagnostic endpoint. Weather entities must still load.
            _LOGGER.debug("Could not read optional FT0360 firmware information: %s", err)

    async def _async_update_data(self) -> FT0360Data:
        """Fetch current readings."""
        record_result, connection_result = await asyncio.gather(
            self.client.async_get_record(),
            self.client.async_get_connection_info(),
            return_exceptions=True,
        )
        if isinstance(record_result, FT0360ApiError):
            raise UpdateFailed(
                f"Could not update FT0360 readings: {record_result}"
            ) from record_result
        if isinstance(record_result, BaseException):
            raise record_result

        connection: FT0360ConnectionInfo | None
        if isinstance(connection_result, FT0360ApiError):
            _LOGGER.debug(
                "Could not update optional FT0360 connection status: %s",
                connection_result,
            )
            connection = None
        elif isinstance(connection_result, BaseException):
            raise connection_result
        else:
            connection = connection_result

        if self.station is None:
            raise UpdateFailed("FT0360 device information is unavailable")
        return FT0360Data(
            station=self.station,
            firmware=self.firmware,
            connection=connection,
            record=record_result,
        )
