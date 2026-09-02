"""Config flow for LANDI FT0360."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .api import (
    FT0360ApiError,
    FT0360CannotConnectError,
    FT0360Client,
    FT0360InvalidResponseError,
    normalize_host,
)
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .parser import FT0360StationInfo

_LOGGER = logging.getLogger(__name__)


def _schema(host: str = "", interval: int = DEFAULT_SCAN_INTERVAL) -> vol.Schema:
    """Return the user/reconfigure schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host): str,
            vol.Required(CONF_SCAN_INTERVAL, default=interval): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
        }
    )


def _options_schema(interval: int) -> vol.Schema:
    """Return the options schema."""
    return vol.Schema(
        {
            vol.Required(CONF_SCAN_INTERVAL, default=interval): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            )
        }
    )


class FT0360ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an FT0360 config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return FT0360OptionsFlow(config_entry)

    async def _async_validate(self, host: str) -> FT0360StationInfo:
        """Connect to both endpoints and return device information."""
        client = FT0360Client(host, async_get_clientsession(self.hass))
        station, _record = await client.async_validate()
        return station

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle setup initiated by the user."""
        errors: dict[str, str] = {}
        host = ""
        interval = DEFAULT_SCAN_INTERVAL

        if user_input is not None:
            interval = int(user_input[CONF_SCAN_INTERVAL])
            try:
                host = normalize_host(str(user_input[CONF_HOST]))
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                try:
                    station = await self._async_validate(host)
                except FT0360CannotConnectError:
                    errors["base"] = "cannot_connect"
                except FT0360InvalidResponseError:
                    errors["base"] = "invalid_response"
                except FT0360ApiError:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error connecting to FT0360 at %s", host)
                    errors["base"] = "unknown"
                else:
                    unique_id = station.mac or host.casefold()
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"FT0360 ({host})",
                        data={CONF_HOST: host},
                        options={CONF_SCAN_INTERVAL: interval},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(host, interval),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the station host while preserving its identity."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        host = str(entry.data[CONF_HOST])
        interval = int(
            entry.options.get(
                CONF_SCAN_INTERVAL,
                entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )

        if user_input is not None:
            interval = int(user_input[CONF_SCAN_INTERVAL])
            try:
                host = normalize_host(str(user_input[CONF_HOST]))
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                try:
                    station = await self._async_validate(host)
                except FT0360CannotConnectError:
                    errors["base"] = "cannot_connect"
                except FT0360InvalidResponseError:
                    errors["base"] = "invalid_response"
                except FT0360ApiError:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error reconnecting to FT0360 at %s", host)
                    errors["base"] = "unknown"
                else:
                    if station.mac is not None:
                        await self.async_set_unique_id(station.mac)
                        self._abort_if_unique_id_mismatch(reason="wrong_device")
                    return self.async_update_and_abort(
                        entry,
                        title=f"FT0360 ({host})",
                        data={CONF_HOST: host},
                        options={CONF_SCAN_INTERVAL: interval},
                        reason="reconfigure_successful",
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(host, interval),
            errors=errors,
        )


class FT0360OptionsFlow(config_entries.OptionsFlow):
    """Allow changing the polling interval."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage FT0360 options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])},
            )

        interval = int(
            self._config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(interval),
        )
