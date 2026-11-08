"""Button entities for the DucoBox Modbus integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DUCOBOX_NODE_TYPE_BOX
from .coordinator import DucoMbConfigEntry, DucoMbCoordinator
from .entity import DucoMbEntity
from .models import DucoMbNodeInfo


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoMbConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DucoBox Modbus buttons."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        DucoMbIdentifyButton(coordinator, node)
        for node in coordinator.box_info.nodes
        if node.node_type == DUCOBOX_NODE_TYPE_BOX
    )


class DucoMbIdentifyButton(DucoMbEntity, ButtonEntity):
    """Blink a node's identify LED over Modbus."""

    _attr_translation_key = "identify"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = ButtonDeviceClass.IDENTIFY

    def __init__(self, coordinator: DucoMbCoordinator, node: DucoMbNodeInfo) -> None:
        """Initialize the button."""
        super().__init__(coordinator, node)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{node.node_id}_identify"
        )

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.async_set_identify(self._node_id)
