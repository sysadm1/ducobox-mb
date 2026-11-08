"""
One-time REST discovery of node topology and Modbus addressing.

This is the only place in the integration that speaks REST. It runs once
during config_flow (and again if the user explicitly reconfigures), purely
to answer two questions Modbus itself cannot: which node IDs exist and what
type each one is (`/info/nodes`), and which slave ID the board expects
(`/config`, `General.Modbus.Addr` - this lives under `/config`, not `/info`;
`/info`'s own `General.Modbus` block only reports a write-budget counter).
Every ongoing poll and every write goes through api.py over Modbus only.
"""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession

from .models import DucoMbBoxInfo, DucoMbNodeInfo


class DucoMbDiscoveryError(ClientError):
    """Raised when the one-time REST discovery call fails or is malformed."""


def _get(data: Any, *keys: str) -> Any:
    """Traverse nested dict keys, returning None if any key is missing."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return None
    return data


async def async_discover(session: ClientSession, host: str) -> DucoMbBoxInfo:
    """Fetch serial number, Modbus addressing and node topology, once."""
    try:
        async with session.get(f"http://{host}/info") as response:
            response.raise_for_status()
            info = await response.json()
        async with session.get(f"http://{host}/config") as response:
            response.raise_for_status()
            config = await response.json()
        async with session.get(f"http://{host}/info/nodes") as response:
            response.raise_for_status()
            nodes_response = await response.json()
    except ClientError as err:
        msg = f"Failed to discover Duco board at {host}: {err}"
        raise DucoMbDiscoveryError(msg) from err

    serial_number = _get(info, "General", "Board", "SerialDucoBox", "Val")
    slave_id = _get(config, "General", "Modbus", "Addr", "Val")
    if serial_number is None or slave_id is None:
        msg = f"Board at {host} did not report Modbus addressing"
        raise DucoMbDiscoveryError(msg)

    nodes = []
    for node in nodes_response.get("Nodes", []):
        node_id = node.get("Node")
        node_type = _get(node, "General", "Type", "Val")
        parent_node_id = _get(node, "General", "Parent", "Val")
        if node_id is None or node_type is None or parent_node_id is None:
            continue
        nodes.append(
            DucoMbNodeInfo(
                node_id=node_id,
                node_type=node_type,
                parent_node_id=parent_node_id,
                name=_get(node, "General", "Name", "Val"),
            )
        )
    if not nodes:
        msg = f"Board at {host} did not report any nodes in /info/nodes"
        raise DucoMbDiscoveryError(msg)

    return DucoMbBoxInfo(
        serial_number=serial_number,
        slave_id=slave_id,
        nodes=tuple(nodes),
    )
