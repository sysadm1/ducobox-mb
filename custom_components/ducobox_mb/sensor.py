"""Sensor entities for the DucoBox Modbus integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION, PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    CO2_NODE_TYPES,
    DUCOBOX_NODE_TYPE_BOX,
    RH_NODE_TYPES,
    VENTILATION_NODE_TYPES,
)
from .coordinator import DucoMbConfigEntry, DucoMbCoordinator
from .entity import DucoMbEntity
from .models import DucoMbNodeData, DucoMbNodeInfo


@dataclass(frozen=True, kw_only=True)
class DucoMbSensorEntityDescription(SensorEntityDescription):
    """Describes a DucoBox Modbus sensor entity."""

    value_fn: Callable[[DucoMbNodeData], StateType]


VENTILATION_SENSORS: list[DucoMbSensorEntityDescription] = [
    DucoMbSensorEntityDescription(
        key="state",
        translation_key="state",
        value_fn=lambda data: data.state,
    ),
    DucoMbSensorEntityDescription(
        key="time_state_remain",
        translation_key="time_state_remain",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        suggested_display_precision=0,
        value_fn=lambda data: data.time_state_remain,
    ),
    DucoMbSensorEntityDescription(
        key="flow_lvl_tgt",
        translation_key="flow_lvl_tgt",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.flow_lvl_tgt,
    ),
]

CO2_SENSORS: list[DucoMbSensorEntityDescription] = [
    DucoMbSensorEntityDescription(
        key="co2",
        translation_key="co2",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.co2,
    ),
    DucoMbSensorEntityDescription(
        key="iaq_co2",
        translation_key="iaq_co2",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.iaq_co2,
    ),
]

RH_SENSORS: list[DucoMbSensorEntityDescription] = [
    DucoMbSensorEntityDescription(
        key="rh",
        translation_key="rh",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.rh,
    ),
    DucoMbSensorEntityDescription(
        key="iaq_rh",
        translation_key="iaq_rh",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.iaq_rh,
    ),
]

VENTILATION_PROBLEM_SENSOR = DucoMbSensorEntityDescription(
    key="ventilation_problem",
    translation_key="ventilation_problem",
    device_class=SensorDeviceClass.ENUM,
    options=["ok", "error", "inactive"],
    value_fn=lambda data: data.ventilation_problem,
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoMbConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Duco Modbus sensors."""
    coordinator = entry.runtime_data.coordinator

    entities: list[SensorEntity] = []
    for node in coordinator.box_info.nodes:
        descriptions: list[DucoMbSensorEntityDescription] = []
        if node.node_type in VENTILATION_NODE_TYPES:
            descriptions.extend(VENTILATION_SENSORS)
        if node.node_type in CO2_NODE_TYPES:
            descriptions.extend(CO2_SENSORS)
        if node.node_type in RH_NODE_TYPES:
            descriptions.extend(RH_SENSORS)
        if node.node_type == DUCOBOX_NODE_TYPE_BOX:
            descriptions.append(VENTILATION_PROBLEM_SENSOR)
        entities.extend(
            DucoMbSensorEntity(coordinator, node, description)
            for description in descriptions
        )
    async_add_entities(entities)


class DucoMbSensorEntity(DucoMbEntity, SensorEntity):
    """DucoBox Modbus sensor entity."""

    entity_description: DucoMbSensorEntityDescription

    def __init__(
        self,
        coordinator: DucoMbCoordinator,
        node: DucoMbNodeInfo,
        description: DucoMbSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, node)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{node.node_id}_{description.key}"
        )
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the node."""
        data = self.coordinator.data[self._node_id]
        return self.entity_description.value_fn(data)
