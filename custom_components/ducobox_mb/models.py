"""Data models for the DucoBox Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DucoMbNodeInfo:
    """Static node topology, discovered once over REST at setup time."""

    node_id: int
    node_type: str
    parent_node_id: int
    name: str | None = None


@dataclass(frozen=True)
class DucoMbBoxInfo:
    """Static box identity and Modbus addressing, discovered once at setup."""

    serial_number: str
    slave_id: int
    nodes: tuple[DucoMbNodeInfo, ...] = field(default_factory=tuple)


@dataclass
class DucoMbNodeData:
    """Live, polled Modbus register values for one node."""

    node_id: int
    node_type: str

    state: str | None = None
    time_state_remain: int | None = None
    flow_lvl_tgt: int | None = None

    rh: int | None = None
    iaq_rh: int | None = None

    co2: int | None = None
    iaq_co2: int | None = None

    ventilation_problem: str | None = None
