"""Tests for the pure-Modbus adapter's register addressing and error handling."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pymodbus.exceptions import ModbusException

from custom_components.ducobox_mb.api import DucoModbusApi, DucoModbusApiError


class FakeResult:
    """A minimal pymodbus response object."""

    def __init__(
        self, registers: list[int] | None = None, *, error: bool = False
    ) -> None:
        self.registers = registers or []
        self._error = error

    def isError(self) -> bool:  # noqa: N802, D102 - matches pymodbus's own API
        return self._error


class FakeModbusClient:
    """Records every call and returns the configured response."""

    def __init__(self) -> None:
        self.connected = True
        self.closed = False
        self.responses: dict[tuple[str, int], FakeResult | Exception] = {}
        self.calls: list[tuple[str, int, int | None]] = []

    async def connect(self) -> bool:  # noqa: D102
        self.connected = True
        return True

    def close(self) -> None:  # noqa: D102
        self.connected = False
        self.closed = True

    async def read_input_registers(  # noqa: D102
        self,
        address: int,
        *,
        count: int = 1,  # noqa: ARG002 - part of pymodbus's call signature
        device_id: int = 1,
        **_: Any,
    ) -> FakeResult:
        self.calls.append(("read_input", address, device_id))
        response = self.responses.get(("read_input", address), FakeResult(error=True))
        if isinstance(response, Exception):
            raise response
        return response

    async def read_holding_registers(  # noqa: D102
        self,
        address: int,
        *,
        count: int = 1,  # noqa: ARG002 - part of pymodbus's call signature
        device_id: int = 1,
        **_: Any,
    ) -> FakeResult:
        self.calls.append(("read_holding", address, device_id))
        response = self.responses.get(("read_holding", address), FakeResult(error=True))
        if isinstance(response, Exception):
            raise response
        return response

    async def write_register(  # noqa: D102
        self,
        address: int,
        value: int,
        *,
        device_id: int = 1,  # noqa: ARG002 - part of pymodbus's call signature
        **_: Any,
    ) -> FakeResult:
        self.calls.append(("write", address, value))
        return self.responses.get(("write", address), FakeResult())


@pytest.fixture
def api() -> tuple[DucoModbusApi, FakeModbusClient]:
    """Return the adapter with its real pymodbus client swapped for a fake."""
    adapter = DucoModbusApi("192.0.2.1", 502, slave_id=124)
    client = FakeModbusClient()
    adapter._client = client  # noqa: SLF001 - intentional test seam
    return adapter, client


def test_address_is_node_id_times_100_plus_offset(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """Matches the live-verified scheme: no extra offset, e.g. node 2 CO2 = 210."""
    adapter, client = api
    client.responses[("read_input", 210)] = FakeResult(registers=[884])

    value = asyncio.run(adapter._async_read_input(2, 10))  # noqa: SLF001

    assert value == 884
    assert client.calls == [("read_input", 210, 124)]


def test_read_node_reads_co2_registers_for_a_co2_node(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """A VLVCO2 node reads time/flow/co2/iaq_co2, not rh registers."""
    adapter, client = api
    client.responses[("read_input", 202)] = FakeResult(registers=[0])
    client.responses[("read_input", 203)] = FakeResult(registers=[100])
    client.responses[("read_input", 205)] = FakeResult(registers=[95])
    client.responses[("read_input", 210)] = FakeResult(registers=[884])

    data = asyncio.run(adapter.async_read_node(2, "VLVCO2", is_box=False))

    assert data == {
        "time_state_remain": 0,
        "flow_lvl_tgt": 100,
        "co2": 884,
        "iaq_co2": 95,
    }


def test_read_node_reads_rh_registers_for_an_rh_node(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """A VLVRH node reads rh/iaq_rh, not co2 registers."""
    adapter, client = api
    client.responses[("read_input", 302)] = FakeResult(registers=[0])
    client.responses[("read_input", 303)] = FakeResult(registers=[50])
    client.responses[("read_input", 304)] = FakeResult(registers=[80])
    client.responses[("read_input", 309)] = FakeResult(registers=[55])

    data = asyncio.run(adapter.async_read_node(3, "VLVRH", is_box=False))

    assert data == {
        "time_state_remain": 0,
        "flow_lvl_tgt": 50,
        "rh": 55,
        "iaq_rh": 80,
    }


def test_read_node_reads_ventilation_problem_for_the_box_only(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """Only the box node reads register xx06 (ventilation status)."""
    adapter, client = api
    client.responses[("read_input", 102)] = FakeResult(registers=[0])
    client.responses[("read_input", 103)] = FakeResult(registers=[78])
    client.responses[("read_input", 106)] = FakeResult(registers=[0])

    data = asyncio.run(adapter.async_read_node(1, "BOX", is_box=True))

    assert data["ventilation_problem"] == "ok"


def test_missing_register_is_reported_as_none_not_an_exception(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """A node type's sensor that the board doesn't have reads as None."""
    adapter, client = api
    client.responses[("read_input", 304)] = ModbusException("exception response")

    value = asyncio.run(adapter._async_read_input(3, 4))  # noqa: SLF001

    assert value is None


def test_read_ventilation_state_maps_the_register_value_back_to_a_name(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """Register value 6 (MAN3) round-trips back to the state name."""
    adapter, client = api
    client.responses[("read_holding", 200)] = FakeResult(registers=[6])

    state = asyncio.run(adapter.async_read_ventilation_state(2))

    assert state == "MAN3"


def test_write_ventilation_state_sends_the_mapped_register_value(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """Writing AUTO sends register value 0 to node_id * 100 + 0."""
    adapter, client = api

    asyncio.run(adapter.async_write_ventilation_state(2, "AUTO"))

    assert client.calls == [("write", 200, 0)]


def test_write_ventilation_state_rejects_unsupported_states(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """AUT1/AUT2/AUT3 have no Modbus equivalent and must be rejected up front."""
    adapter, _client = api

    with pytest.raises(DucoModbusApiError):
        asyncio.run(adapter.async_write_ventilation_state(2, "AUT1"))


def test_write_ventilation_state_raises_on_board_error(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """A Modbus exception response on write surfaces as DucoModbusApiError."""
    adapter, client = api
    client.responses[("write", 200)] = FakeResult(error=True)

    with pytest.raises(DucoModbusApiError):
        asyncio.run(adapter.async_write_ventilation_state(2, "AUTO"))


def test_identify_writes_register_xx01(
    api: tuple[DucoModbusApi, FakeModbusClient],
) -> None:
    """Identify writes a 1 to node_id * 100 + 1."""
    adapter, client = api

    asyncio.run(adapter.async_identify(2))

    assert client.calls == [("write", 201, 1)]
