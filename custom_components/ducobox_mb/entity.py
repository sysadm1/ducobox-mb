"""Base entity for the DucoBox Modbus integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DUCOBOX_NODE_TYPE_BOX
from .coordinator import DucoMbCoordinator
from .models import DucoMbNodeInfo


class DucoMbEntity(CoordinatorEntity[DucoMbCoordinator]):
    """Base class for DucoBox Modbus entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DucoMbCoordinator, node: DucoMbNodeInfo) -> None:
        """Initialize DucoBox Modbus entity."""
        super().__init__(coordinator)
        self._node_id = node.node_id

        serial_number = coordinator.box_info.serial_number
        identifiers = {(DOMAIN, f"{serial_number}_{node.node_id}")}
        name = (
            f"{node.node_type} {node.node_id} ({node.name})"
            if node.name
            else f"{node.node_type} {node.node_id}"
        )

        self._attr_device_info = DeviceInfo(
            identifiers=identifiers,
            manufacturer="Duco",
            name=name,
            model=node.node_type,
        )

        if node.node_type != DUCOBOX_NODE_TYPE_BOX:
            via_device = (DOMAIN, f"{serial_number}_{node.parent_node_id}")
            self._attr_device_info["via_device"] = via_device
        else:
            self._attr_device_info["serial_number"] = serial_number

    @property
    def available(self) -> bool:
        """Return True if the node is still present in coordinator data."""
        return super().available and self._node_id in self.coordinator.data
