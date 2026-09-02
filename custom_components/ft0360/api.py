"""Async client for the local LANDI FT0360 HTTP API."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .const import (
    DEFAULT_REQUEST_TIMEOUT,
    ENDPOINT_ABOUT,
    ENDPOINT_CONNECT_STATUS,
    ENDPOINT_DEBUG,
    ENDPOINT_FIRMWARE,
    ENDPOINT_RECORD,
    MAX_RESPONSE_SIZE,
)
from .parser import (
    FT0360ConnectionInfo,
    FT0360DebugInfo,
    FT0360FirmwareInfo,
    FT0360ParseError,
    FT0360Record,
    FT0360StationInfo,
    parse_connection_info,
    parse_debug_info,
    parse_firmware_info,
    parse_record,
    parse_station_info,
)


class FT0360ApiError(Exception):
    """Base exception for communication with the FT0360."""


class FT0360CannotConnectError(FT0360ApiError):
    """Raised when the station cannot be reached."""


class FT0360InvalidResponseError(FT0360ApiError):
    """Raised when the station returns invalid or unexpected data."""


def normalize_host(value: str) -> str:
    """Normalize an IPv4/IPv6 address or hostname, optionally with a port."""
    raw = value.strip()
    if not raw:
        raise ValueError("Host must not be empty")

    candidate = raw if "://" in raw else f"http://{raw}"
    parsed = urlsplit(candidate)
    if parsed.scheme.casefold() != "http":
        raise ValueError("Only local HTTP addresses are supported")
    if parsed.username or parsed.password:
        raise ValueError("Credentials are not supported")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Enter only the IP address or hostname")
    if not parsed.hostname or any(character.isspace() for character in parsed.hostname):
        raise ValueError("Invalid IP address or hostname")

    try:
        port = parsed.port
    except ValueError as err:
        raise ValueError("Invalid port") from err

    hostname = parsed.hostname
    if ":" in hostname:
        hostname = f"[{hostname}]"
    return f"{hostname}:{port}" if port is not None else hostname


class FT0360Client:
    """Small async client for the station's read-only local endpoints."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        self.host = normalize_host(host)
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=request_timeout)

    @property
    def base_url(self) -> str:
        """Return the station base URL."""
        return f"http://{self.host}"

    async def _async_get_json(self, endpoint: str) -> dict[str, Any]:
        """Fetch and decode one JSON object."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with self._session.get(
                url, timeout=self._timeout, allow_redirects=False
            ) as response:
                response.raise_for_status()
                if (
                    response.content_length is not None
                    and response.content_length > MAX_RESPONSE_SIZE
                ):
                    raise FT0360InvalidResponseError(
                        f"Response from {self.host} is too large"
                    )
                body = await response.content.read(MAX_RESPONSE_SIZE + 1)
        except asyncio.TimeoutError as err:
            raise FT0360CannotConnectError(
                f"Timeout while connecting to {self.host}"
            ) from err
        except aiohttp.ClientResponseError as err:
            raise FT0360CannotConnectError(
                f"HTTP {err.status} returned by {self.host}"
            ) from err
        except aiohttp.ClientError as err:
            raise FT0360CannotConnectError(
                f"Unable to connect to {self.host}: {err}"
            ) from err

        if len(body) > MAX_RESPONSE_SIZE:
            raise FT0360InvalidResponseError(f"Response from {self.host} is too large")

        try:
            # The station emits UTF-8 but does not always declare a useful content type.
            # Latin-1 is a last-resort fallback; unit labels are ignored by the parser.
            try:
                text = body.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = body.decode("latin-1")
            data = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            raise FT0360InvalidResponseError(
                f"Invalid JSON returned by {self.host}"
            ) from err

        if not isinstance(data, dict):
            raise FT0360InvalidResponseError(
                f"Expected a JSON object from {self.host}, got {type(data).__name__}"
            )
        return data

    async def async_get_record(self) -> FT0360Record:
        """Fetch and parse the current weather readings."""
        payload = await self._async_get_json(ENDPOINT_RECORD)
        try:
            return parse_record(payload)
        except FT0360ParseError as err:
            raise FT0360InvalidResponseError(str(err)) from err

    async def async_get_about(self) -> FT0360StationInfo:
        """Fetch and parse static station information."""
        payload = await self._async_get_json(ENDPOINT_ABOUT)
        try:
            return parse_station_info(payload)
        except FT0360ParseError as err:
            raise FT0360InvalidResponseError(str(err)) from err

    async def async_get_connection_info(self) -> FT0360ConnectionInfo:
        """Fetch and parse the current console network state."""
        payload = await self._async_get_json(ENDPOINT_CONNECT_STATUS)
        try:
            return parse_connection_info(payload)
        except FT0360ParseError as err:
            raise FT0360InvalidResponseError(str(err)) from err

    async def async_get_firmware_info(self) -> FT0360FirmwareInfo:
        """Fetch and parse the console firmware metadata."""
        payload = await self._async_get_json(ENDPOINT_FIRMWARE)
        try:
            return parse_firmware_info(payload)
        except FT0360ParseError as err:
            raise FT0360InvalidResponseError(str(err)) from err

    async def async_get_debug_info(self) -> FT0360DebugInfo:
        """Fetch and parse optional metadata for a diagnostics download."""
        payload = await self._async_get_json(ENDPOINT_DEBUG)
        try:
            return parse_debug_info(payload)
        except FT0360ParseError as err:
            raise FT0360InvalidResponseError(str(err)) from err

    async def async_validate(self) -> tuple[FT0360StationInfo, FT0360Record]:
        """Validate both endpoints during the config flow."""
        about, record = await asyncio.gather(
            self.async_get_about(),
            self.async_get_record(),
        )
        return about, record
