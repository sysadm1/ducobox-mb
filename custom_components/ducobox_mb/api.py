"""
Pure Modbus TCP adapter for the Duco Connectivity Board.

Every register this module reads is taken from the live-verified map in
sysadm1/ducofocus-cb.2.0's duco_modbustcp/README.md: address = node_id * 100
+ parameter number, with no further address adjustment - confirmed by
reading register 210 (node 2, CO2) directly over pymodbus and comparing it
to the REST API's simultaneous /info/nodes value. All sensor values are
INPUT registers (function code 4).

The ventilation-state and identify HOLDING registers (xx00/xx01, function
code 3 read / 6 write) follow the same node_id * 100 + parameter addressing
per the official information-sheet-Modbus-TCP-(en).pdf, but that specific
write path has not yet been live-verified over raw pymodbus the way the
INPUT registers were - confirm it against your board (e.g. read xx00 back
after a write) before relying on it.

This module never calls the board's REST API - node topology is discovered
once over REST during config_flow and handed to this adapter as static
data.
"""

from __future__ import annotations

import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    CO2_NODE_TYPES,
    CO2_OFFSET,
    FLOW_LVL_TGT_OFFSET,
    IAQ_CO2_OFFSET,
    IAQ_RH_OFFSET,
    IDENTIFY_OFFSET,
    MODBUS_VENTILATION_STATE_VALUES,
    RH_NODE_TYPES,
    RH_OFFSET,
    TIME_STATE_REMAIN_OFFSET,
    VENTILATION_PROBLEM_OFFSET,
    VENTILATION_PROBLEM_STATES,
    VENTILATION_STATE_OFFSET,
)

_LOGGER = logging.getLogger(__name__)

_STATE_BY_VALUE = {
    value: state for state, value in MODBUS_VENTILATION_STATE_VALUES.items()
}


class DucoModbusApiError(ModbusException):
    """Raised when a Modbus call fails or returns an unexpected result."""


class DucoModbusApi:
    """Async adapter around pymodbus for one Duco Connectivity Board."""

    def __init__(self, host: str, port: int, slave_id: int) -> None:
        """
        Initialize the adapter. The client is created lazily, on first use.

        AsyncModbusTcpClient.__init__ requires a running event loop, same as
        DucoPy's sync client requires being created off Home Assistant's loop
        in sysadm1/ducobox-api's api.py. Deferring construction here avoids
        requiring every caller to already be inside an async context just to
        build the adapter.
        """
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._client: AsyncModbusTcpClient | None = None

    def _address(self, node_id: int, offset: int) -> int:
        """Convert a DUCO node/parameter pair into a Modbus register address."""
        return node_id * 100 + offset

    async def _async_ensure_connected(self) -> AsyncModbusTcpClient:
        if self._client is None:
            self._client = AsyncModbusTcpClient(self._host, port=self._port)
        if not self._client.connected:
            await self._client.connect()
            if not self._client.connected:
                msg = f"Could not connect to {self._host}:{self._port}"
                raise DucoModbusApiError(msg)
        return self._client

    async def async_close(self) -> None:
        """Close the Modbus TCP connection, if one was ever opened."""
        if self._client is not None:
            self._client.close()

    async def _async_read_input(self, node_id: int, offset: int) -> int | None:
        """Read one INPUT register, returning None on any board-side exception."""
        client = await self._async_ensure_connected()
        address = self._address(node_id, offset)
        try:
            result = await client.read_input_registers(
                address, count=1, device_id=self._slave_id
            )
        except ModbusException:
            _LOGGER.debug("Register %s not available on node %s", address, node_id)
            return None
        if result.isError():
            return None
        return result.registers[0]

    async def async_read_node(
        self, node_id: int, node_type: str, *, is_box: bool
    ) -> dict[str, Any]:
        """Read every register this node type advertises."""
        data: dict[str, Any] = {
            "time_state_remain": await self._async_read_input(
                node_id, TIME_STATE_REMAIN_OFFSET
            ),
            "flow_lvl_tgt": await self._async_read_input(node_id, FLOW_LVL_TGT_OFFSET),
        }
        if node_type in RH_NODE_TYPES:
            data["rh"] = await self._async_read_input(node_id, RH_OFFSET)
            data["iaq_rh"] = await self._async_read_input(node_id, IAQ_RH_OFFSET)
        if node_type in CO2_NODE_TYPES:
            data["co2"] = await self._async_read_input(node_id, CO2_OFFSET)
            data["iaq_co2"] = await self._async_read_input(node_id, IAQ_CO2_OFFSET)
        if is_box:
            raw = await self._async_read_input(node_id, VENTILATION_PROBLEM_OFFSET)
            data["ventilation_problem"] = VENTILATION_PROBLEM_STATES.get(raw)
        return data

    async def async_read_ventilation_state(self, node_id: int) -> str | None:
        """Read back the current ventilation mode from the HOLDING register."""
        client = await self._async_ensure_connected()
        address = self._address(node_id, VENTILATION_STATE_OFFSET)
        try:
            result = await client.read_holding_registers(
                address, count=1, device_id=self._slave_id
            )
        except ModbusException:
            return None
        if result.isError():
            return None
        return _STATE_BY_VALUE.get(result.registers[0])

    async def async_write_ventilation_state(self, node_id: int, state: str) -> None:
        """Write a DUCO ventilation mode to the HOLDING register."""
        if state not in MODBUS_VENTILATION_STATE_VALUES:
            msg = f"Unsupported ventilation state over Modbus: {state}"
            raise DucoModbusApiError(msg)
        client = await self._async_ensure_connected()
        address = self._address(node_id, VENTILATION_STATE_OFFSET)
        result = await client.write_register(
            address, MODBUS_VENTILATION_STATE_VALUES[state], device_id=self._slave_id
        )
        if result.isError():
            msg = f"Failed to write ventilation state {state} to node {node_id}"
            raise DucoModbusApiError(msg)

    async def async_identify(self, node_id: int) -> None:
        """Write the identify (blink LED) HOLDING register."""
        client = await self._async_ensure_connected()
        address = self._address(node_id, IDENTIFY_OFFSET)
        result = await client.write_register(address, 1, device_id=self._slave_id)
        if result.isError():
            msg = f"Failed to identify node {node_id}"
            raise DucoModbusApiError(msg)
