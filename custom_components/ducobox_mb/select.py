"""Select entities for the DucoBox Modbus integration."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MODBUS_VENTILATION_STATE_VALUES, VENTILATION_NODE_TYPES
from .coordinator import DucoMbConfigEntry, DucoMbCoordinator
from .entity import DucoMbEntity
from .models import DucoMbNodeInfo


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoMbConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DucoBox Modbus selects."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        DucoMbSelectEntity(coordinator, node)
        for node in coordinator.box_info.nodes
        if node.node_type in VENTILATION_NODE_TYPES
    )


class DucoMbSelectEntity(DucoMbEntity, SelectEntity):
    """DucoBox Modbus ventilation state select."""

    _attr_translation_key = "ventilation_state"
    _attr_options: ClassVar[list[str]] = list(MODBUS_VENTILATION_STATE_VALUES)

    def __init__(self, coordinator: DucoMbCoordinator, node: DucoMbNodeInfo) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, node)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{node.node_id}_ventilation_state"
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently selected ventilation state."""
        return self.coordinator.data[self._node_id].state

    async def async_select_option(self, option: str) -> None:
        """Change the ventilation state."""
        await self.coordinator.async_set_ventilation_state(self._node_id, option)
