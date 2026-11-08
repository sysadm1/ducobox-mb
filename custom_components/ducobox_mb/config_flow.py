"""
Config flow for the DucoBox Modbus integration.

Setup (and reconfigure) make exactly one REST call to the board, purely to
discover its node topology and Modbus addressing - see discovery.py. Once
the config entry is created, the integration never touches REST again.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

import voluptuous as vol
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_NODES,
    CONF_SERIAL_NUMBER,
    CONF_SLAVE_ID,
    DEFAULT_PORT,
    DOMAIN,
)
from .discovery import DucoMbDiscoveryError, async_discover
from .models import DucoMbBoxInfo

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


def _entry_data(host: str, port: int, box_info: DucoMbBoxInfo) -> dict[str, Any]:
    """Build config entry data from one discovery result."""
    return {
        CONF_HOST: host,
        CONF_PORT: port,
        CONF_SLAVE_ID: box_info.slave_id,
        CONF_SERIAL_NUMBER: box_info.serial_number,
        CONF_NODES: [asdict(node) for node in box_info.nodes],
    }


class DucoMbConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DucoBox Modbus."""

    VERSION = 1
    MINOR_VERSION = 1

    _zeroconf_discovered_host: str

    async def async_step_zeroconf(
        self, info: zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle the config flow initiated by Zeroconf."""
        self._zeroconf_discovered_host = info.host
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the Zeroconf-discovered board, then run REST discovery."""
        if user_input is not None:
            return await self._async_discover_and_create(
                self._zeroconf_discovered_host, DEFAULT_PORT
            )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"host": self._zeroconf_discovered_host},
        )

    async def async_step_user(
        self, info: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the config flow initiated by the user."""
        errors: dict[str, str] = {}

        if info is not None:
            try:
                return await self._async_discover_and_create(
                    info[CONF_HOST], info[CONF_PORT]
                )
            except AbortFlow:
                raise
            except DucoMbDiscoveryError:
                _LOGGER.exception(
                    "Failed to discover Duco board at %s", info[CONF_HOST]
                )
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error discovering Duco board")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-run REST discovery to pick up added/removed nodes."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            try:
                session = async_get_clientsession(self.hass)
                box_info = await async_discover(session, host)
            except DucoMbDiscoveryError:
                _LOGGER.exception("Failed to re-discover Duco board at %s", host)
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data=_entry_data(host, port, box_info)
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
                vol.Required(CONF_PORT, default=entry.data[CONF_PORT]): int,
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )

    async def _async_discover_and_create(
        self, host: str, port: int
    ) -> ConfigFlowResult:
        """Run REST discovery once and create the config entry."""
        session = async_get_clientsession(self.hass)
        box_info = await async_discover(session, host)

        await self.async_set_unique_id(box_info.serial_number)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        return self.async_create_entry(
            title=f"DucoBox Modbus ({host})",
            data=_entry_data(host, port, box_info),
        )
