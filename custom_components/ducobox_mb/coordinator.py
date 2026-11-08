"""Coordinator for the DucoBox Modbus integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DucoModbusApi, DucoModbusApiError
from .const import DUCOBOX_NODE_TYPE_BOX, VENTILATION_NODE_TYPES
from .models import DucoMbBoxInfo, DucoMbNodeData

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)
# DUCO documents a minimum of 2 seconds between writes to the same board.
_MIN_WRITE_INTERVAL = 2.0


@dataclass
class DucoMbRuntimeData:
    """DucoBox Modbus runtime data."""

    coordinator: DucoMbCoordinator


type DucoMbConfigEntry = ConfigEntry[DucoMbRuntimeData]


class DucoMbCoordinator(DataUpdateCoordinator[dict[int, DucoMbNodeData]]):
    """Poll every node's Modbus registers on a fixed interval."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: DucoModbusApi,
        box_info: DucoMbBoxInfo,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name="DucoBox Modbus coordinator",
            update_interval=UPDATE_INTERVAL,
            config_entry=config_entry,
            always_update=False,
        )
        self.api = api
        self.box_info = box_info
        self._write_lock = asyncio.Lock()
        self._last_write_at = 0.0

    async def _async_wait_for_write_slot(self) -> None:
        """Respect DUCO's minimum interval between writes."""
        now = asyncio.get_running_loop().time()
        wait_time = _MIN_WRITE_INTERVAL - (now - self._last_write_at)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        self._last_write_at = asyncio.get_running_loop().time()

    async def _async_update_data(self) -> dict[int, DucoMbNodeData]:
        """Poll every known node's registers over Modbus."""
        try:
            result: dict[int, DucoMbNodeData] = {}
            for node in self.box_info.nodes:
                is_box = node.node_type == DUCOBOX_NODE_TYPE_BOX
                values = await self.api.async_read_node(
                    node.node_id, node.node_type, is_box=is_box
                )
                state = None
                if node.node_type in VENTILATION_NODE_TYPES:
                    state = await self.api.async_read_ventilation_state(node.node_id)
                result[node.node_id] = DucoMbNodeData(
                    node_id=node.node_id,
                    node_type=node.node_type,
                    state=state,
                    **values,
                )
        except DucoModbusApiError as err:
            msg = f"Failed to poll Duco board over Modbus: {err}"
            raise UpdateFailed(msg) from err
        return result

    async def async_set_ventilation_state(self, node_id: int, state: str) -> None:
        """Write a ventilation state to one node over Modbus."""
        try:
            async with self._write_lock:
                await self._async_wait_for_write_slot()
                await self.api.async_write_ventilation_state(node_id, state)
            await self.async_request_refresh()
        except DucoModbusApiError as err:
            msg = f"Failed to set ventilation state on node {node_id} to {state}: {err}"
            raise HomeAssistantError(msg) from err

    async def async_set_identify(self, node_id: int) -> None:
        """Blink a node's identify LED over Modbus."""
        try:
            async with self._write_lock:
                await self._async_wait_for_write_slot()
                await self.api.async_identify(node_id)
        except DucoModbusApiError as err:
            msg = f"Failed to identify node {node_id}: {err}"
            raise HomeAssistantError(msg) from err
