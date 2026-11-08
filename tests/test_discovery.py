"""Tests for the one-time REST discovery call."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Self

import pytest

from custom_components.ducobox_mb.discovery import DucoMbDiscoveryError, async_discover
from custom_components.ducobox_mb.models import DucoMbNodeInfo

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


class FakeResponse:
    """A minimal aiohttp response usable as an async context manager."""

    def __init__(self, payload: Any, *, status: int = 200) -> None:
        self._payload = payload
        self._status = status

    async def __aenter__(self) -> Self:  # noqa: D105
        return self

    async def __aexit__(self, *exc_info: object) -> None:  # noqa: D105
        return None

    def raise_for_status(self) -> None:  # noqa: D102
        if self._status >= 400:
            msg = f"HTTP {self._status}"
            raise RuntimeError(msg)

    async def json(self) -> Any:  # noqa: D102
        return self._payload


class FakeSession:
    """Serves the three fixture endpoints discovery.py calls, in order."""

    def __init__(self, responses: dict[str, Any]) -> None:
        self._responses = responses
        self.requested: list[str] = []

    def get(self, url: str) -> FakeResponse:  # noqa: D102
        self.requested.append(url)
        for suffix, payload in self._responses.items():
            if url.endswith(suffix):
                return FakeResponse(payload)
        return FakeResponse({}, status=404)


def _real_session() -> FakeSession:
    return FakeSession(
        {
            "/info": _load("info.json"),
            "/config": _load("config.json"),
            "/info/nodes": _load("info_nodes.json"),
        }
    )


def test_discover_reads_serial_number_from_info() -> None:
    """The serial number comes from /info, not /config."""
    box_info = asyncio.run(async_discover(_real_session(), "192.0.2.1"))

    assert box_info.serial_number == "REDACTED"


def test_discover_reads_slave_id_from_config_not_info() -> None:
    """General.Modbus.Addr lives under /config - /info only has a write counter."""
    box_info = asyncio.run(async_discover(_real_session(), "192.0.2.1"))

    assert box_info.slave_id == 124


def test_discover_builds_node_topology_with_types_and_parents() -> None:
    """Every node from /info/nodes becomes a DucoMbNodeInfo with its type."""
    box_info = asyncio.run(async_discover(_real_session(), "192.0.2.1"))

    assert len(box_info.nodes) == 7
    box = next(n for n in box_info.nodes if n.node_id == 1)
    kitchen = next(n for n in box_info.nodes if n.node_id == 2)
    assert box.node_type == "BOX"
    assert box.parent_node_id == 0
    assert kitchen == DucoMbNodeInfo(
        node_id=2, node_type="VLVCO2", parent_node_id=1, name="Keuken"
    )


def test_discover_raises_when_modbus_addressing_is_missing() -> None:
    """A board that never reports General.Modbus.Addr is a discovery failure."""
    session = FakeSession(
        {
            "/info": _load("info.json"),
            "/config": {"General": {}},
            "/info/nodes": _load("info_nodes.json"),
        }
    )

    with pytest.raises(DucoMbDiscoveryError):
        asyncio.run(async_discover(session, "192.0.2.1"))


def test_discover_raises_when_no_nodes_reported() -> None:
    """A board reporting zero nodes is also a discovery failure."""
    session = FakeSession(
        {
            "/info": _load("info.json"),
            "/config": _load("config.json"),
            "/info/nodes": {"Nodes": []},
        }
    )

    with pytest.raises(DucoMbDiscoveryError):
        asyncio.run(async_discover(session, "192.0.2.1"))
