"""Fan entities for the DucoBox Modbus integration."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import percentage_to_ordered_list_item

from .const import MODBUS_VENTILATION_STATE_VALUES, VENTILATION_NODE_TYPES
from .coordinator import DucoMbConfigEntry, DucoMbCoordinator
from .entity import DucoMbEntity
from .models import DucoMbNodeInfo

# Mirrors sysadm1/ducobox-api's fan.py: the board exposes three continuous
# ventilation levels. Home Assistant percentages select the nearest one
# instead of sending an arbitrary 0-100 override.
ORDERED_FAN_SPEEDS = ["CNT1", "CNT2", "CNT3"]
SPEED_LEVEL_PERCENTAGES = [
    (index + 1) * 100 // len(ORDERED_FAN_SPEEDS)
    for index, _ in enumerate(ORDERED_FAN_SPEEDS)
]
STATE_TO_PERCENTAGE = {
    state: SPEED_LEVEL_PERCENTAGES[index]
    for index, speed in enumerate(ORDERED_FAN_SPEEDS)
    for state in (speed, f"MAN{index + 1}", f"MAN{index + 1}x2", f"MAN{index + 1}x3")
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoMbConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DucoBox Modbus fans."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        DucoMbFanEntity(coordinator, node)
        for node in coordinator.box_info.nodes
        if node.node_type in VENTILATION_NODE_TYPES
    )


class DucoMbFanEntity(DucoMbEntity, FanEntity):
    """DucoBox Modbus fan entity."""

    _attr_translation_key = "ventilation"
    _attr_supported_features = FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED
    _attr_speed_count = len(ORDERED_FAN_SPEEDS)
    _attr_preset_modes: ClassVar[list[str]] = list(MODBUS_VENTILATION_STATE_VALUES)

    def __init__(self, coordinator: DucoMbCoordinator, node: DucoMbNodeInfo) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator, node)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{node.node_id}_ventilation"
        )

    @property
    def is_on(self) -> bool:
        """Return true; the board always has some ventilation mode active."""
        return True

    @property
    def preset_mode(self) -> str | None:
        """Return the current ventilation mode."""
        return self.coordinator.data[self._node_id].state

    @property
    def percentage(self) -> int | None:
        """Return the discrete speed level, or None for automatic/other modes."""
        state = self.coordinator.data[self._node_id].state
        return STATE_TO_PERCENTAGE.get(state or "")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the ventilation mode."""
        await self.coordinator.async_set_ventilation_state(self._node_id, preset_mode)

    async def async_set_percentage(self, percentage: int) -> None:
        """Map Home Assistant's fan slider to one of the supported speeds."""
        if percentage == 0:
            state = "AUTO"
        else:
            state = percentage_to_ordered_list_item(ORDERED_FAN_SPEEDS, percentage)

        if state not in MODBUS_VENTILATION_STATE_VALUES:
            msg = f"Ventilation state {state} is not available over Modbus"
            raise HomeAssistantError(msg)

        await self.coordinator.async_set_ventilation_state(self._node_id, state)
