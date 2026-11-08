"""Constants for the DucoBox Modbus integration."""

from homeassistant.const import Platform

DOMAIN = "ducobox_mb"

CONF_PORT = "port"
CONF_SLAVE_ID = "slave_id"
CONF_SERIAL_NUMBER = "serial_number"
CONF_NODES = "nodes"

DEFAULT_PORT = 502

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.FAN,
    Platform.SELECT,
    Platform.SENSOR,
]

DUCOBOX_NODE_TYPE_BOX = "BOX"
DUCOBOX_NODE_TYPE_BSCO2 = "BSCO2"
DUCOBOX_NODE_TYPE_BSRH = "BSRH"
DUCOBOX_NODE_TYPE_UCBAT = "UCBAT"
DUCOBOX_NODE_TYPE_UCCO2 = "UCCO2"
DUCOBOX_NODE_TYPE_UCRH = "UCRH"
DUCOBOX_NODE_TYPE_VLV = "VLV"
DUCOBOX_NODE_TYPE_VLVCO2 = "VLVCO2"
DUCOBOX_NODE_TYPE_VLVCO2RH = "VLVCO2RH"
DUCOBOX_NODE_TYPE_VLVRH = "VLVRH"
DUCOBOX_NODE_TYPE_VLVVOC = "VLVVOC"

# Node types with ventilation (fan/select) control, per the official Modbus
# sheet's HOLDING xx00 register. Sensor-only nodes (BSCO2, BSRH, UCCO2, UCRH)
# do not advertise it.
VENTILATION_NODE_TYPES = {
    DUCOBOX_NODE_TYPE_BOX,
    DUCOBOX_NODE_TYPE_VLV,
    DUCOBOX_NODE_TYPE_VLVCO2,
    DUCOBOX_NODE_TYPE_VLVCO2RH,
    DUCOBOX_NODE_TYPE_VLVRH,
    DUCOBOX_NODE_TYPE_VLVVOC,
}

CO2_NODE_TYPES = {
    DUCOBOX_NODE_TYPE_BSCO2,
    DUCOBOX_NODE_TYPE_UCCO2,
    DUCOBOX_NODE_TYPE_VLVCO2,
    DUCOBOX_NODE_TYPE_VLVCO2RH,
}

RH_NODE_TYPES = {
    DUCOBOX_NODE_TYPE_BSRH,
    DUCOBOX_NODE_TYPE_UCRH,
    DUCOBOX_NODE_TYPE_VLVCO2RH,
    DUCOBOX_NODE_TYPE_VLVRH,
}

# DUCO's Modbus mode values for register XX00. AUT1/AUT2/AUT3 have no
# documented Modbus equivalent and are therefore intentionally omitted -
# see information-sheet-Modbus-TCP-(en).pdf.
MODBUS_VENTILATION_STATE_VALUES = {
    "AUTO": 0,
    "MAN1": 4,
    "MAN2": 5,
    "MAN3": 6,
    "EMPT": 7,
    "CNT1": 8,
    "CNT2": 9,
    "CNT3": 10,
    "MAN1x2": 11,
    "MAN2x2": 12,
    "MAN3x2": 13,
    "MAN1x3": 14,
    "MAN2x3": 15,
    "MAN3x3": 16,
}

# Per-node register offsets, verified live against a real DucoBox Focus
# (see duco_modbustcp/README.md in the sysadm1/ducofocus-cb.2.0 project this
# was ported from). Register address = node_id * 100 + offset + address
# adjustment. All of these are INPUT registers (function code 4) except
# VENTILATION_STATE_OFFSET and IDENTIFY_OFFSET, which are HOLDING (function
# code 3 read / 6 write).
VENTILATION_STATE_OFFSET = 0
IDENTIFY_OFFSET = 1
TIME_STATE_REMAIN_OFFSET = 2
FLOW_LVL_TGT_OFFSET = 3
IAQ_RH_OFFSET = 4
IAQ_CO2_OFFSET = 5
VENTILATION_PROBLEM_OFFSET = 6  # box node only
RH_OFFSET = 9
CO2_OFFSET = 10

VENTILATION_PROBLEM_STATES = {0: "ok", 1: "error", 2: "inactive"}
