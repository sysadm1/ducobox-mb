# DucoBox Modbus

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/sysadm1/ducobox-mb.svg)](https://github.com/sysadm1/ducobox-mb/releases)
[![License](https://img.shields.io/github/license/sysadm1/ducobox-mb.svg)](LICENSE)

A Home Assistant integration for DucoBox ventilation systems that talks exclusively over **Modbus TCP**. For the REST-only variant with no Modbus dependency, see [ducobox-api](https://github.com/sysadm1/ducobox-api).

## Modbus-only, with one REST call at setup

Modbus has no equivalent of REST's `/info/nodes`, so there is no way to ask the board "which nodes exist and what type is each one" over Modbus alone. To avoid making you type that in by hand, this integration's config flow makes exactly **one REST call** when you add (or reconfigure) it, purely to discover node IDs, node types and the board's Modbus slave ID. That data is stored once in the config entry.

After setup, the integration never calls REST again. Every sensor poll and every write (ventilation state, identify) goes over Modbus TCP only. If you want zero REST dependency at any point, including setup, use [ducobox-mb's companion project's YAML-based alternative](https://github.com/sysadm1/ducofocus-cb.2.0/tree/main/duco_modbustcp) and type the node map in by hand instead.

## Verified against a real board

The register map this integration reads is the one verified live against a DucoBox Focus with Connectivity Board 2.0 (see `sysadm1/ducofocus-cb.2.0`'s `duco_modbustcp/README.md` for how): `address = node_id * 100 + parameter_number`, no further offset, INPUT registers (function code 4) for every sensor value. This integration's own read path (sensors and the ventilation-state read-back) has additionally been cross-checked directly: every value it reads over Modbus was confirmed to match the REST API's `/info/nodes` response for the same node at the same moment.

**Not yet live-verified**: writing the ventilation-state HOLDING register (`xx00`) and the identify register (`xx01`) over raw Modbus. These follow the same addressing scheme per the official `information-sheet-Modbus-TCP-(en).pdf`, but unlike the reads, nobody has confirmed a write-then-read-back round trip against real hardware yet. Test this carefully (e.g. set a mode, then confirm it stuck by reading `xx00` back, or by checking Home Assistant's existing `select.*_ventilation_state` entity from `ducobox-api` against the same node) before relying on it for anything automated.

## Features

| Entity | Type | BOX | sensor-only nodes (BSCO2/BSRH/UCCO2/UCRH) | VLV/VLVCO2/VLVRH/VLVCO2RH/VLVVOC |
|---:|:---|:---:|:---:|:---:|
| Ventilation | Fan | ✓ | | ✓ |
| Ventilation State | Select | ✓ | | ✓ |
| Ventilation State | Sensor | ✓ | | ✓ |
| Ventilation State Remaining Time | Sensor | ✓ | | ✓ |
| Target Flow Level | Sensor | ✓ | | ✓ |
| CO2 / CO2 Air Quality Index | Sensor | | ✓ (CO2 types only) | ✓ (CO2 types only) |
| Relative Humidity / RH Air Quality Index | Sensor | | ✓ (RH types only) | ✓ (RH types only) |
| Ventilation Status (OK/Error/Inactive) | Sensor | ✓ | | |
| Identify | Button | ✓ | | |

Compared to [ducobox-api](https://github.com/sysadm1/ducobox-api), this integration does **not** expose: `time_state_end`, ventilation `Mode` (AUTO/MANU), VOC, heat-recovery temperatures, filter time remaining, board diagnostics (Wi-Fi signal, write budgets), cloud status, or any `number` configuration entities. None of those are available as Modbus registers on the DucoBox Focus - see `duco_modbustcp/README.md` in `ducofocus-cb.2.0` for the full register map this was built from.

The ventilation select/fan only offer `AUTO`, `MAN1`-`MAN3`, `EMPT`, `CNT1`-`CNT3` and `MAN1x2`-`MAN3x3`. `AUT1`-`AUT3` (available over REST) have no documented Modbus register value.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner and select "Custom repositories"
3. Add repository `https://github.com/sysadm1/ducobox-mb` with category "Integration"
4. Search for "DucoBox Modbus", select the integration, and download it
5. Restart Home Assistant

### Manual

1. Download the latest release from [Releases](https://github.com/sysadm1/ducobox-mb/releases)
2. Extract the `custom_components/ducobox_mb` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to "Settings" → "Devices & Services" → "Add Integration"
2. Search for "DucoBox Modbus"
3. Enter the board's IP address and Modbus TCP port (502 by default)
4. The integration fetches the board's node list and Modbus slave ID once over REST, then switches to Modbus TCP only

If you later add or remove a node (e.g. a new valve), use the integration's "Reconfigure" option to re-run this one-time discovery step.

## Contribution

If you find a node type or entity this integration doesn't support, or confirm the write path against real hardware, feel free to [open an issue](https://github.com/sysadm1/ducobox-mb/issues) or [create a pull request](https://github.com/sysadm1/ducobox-mb/pulls).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
