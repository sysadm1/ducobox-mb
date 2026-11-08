"""The DucoBox Modbus integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import DucoModbusApi
from .const import CONF_NODES, CONF_SERIAL_NUMBER, CONF_SLAVE_ID, PLATFORMS
from .coordinator import DucoMbConfigEntry, DucoMbCoordinator, DucoMbRuntimeData
from .models import DucoMbBoxInfo, DucoMbNodeInfo


async def async_setup_entry(hass: HomeAssistant, entry: DucoMbConfigEntry) -> bool:
    """Set up DucoBox Modbus from a config entry."""
    box_info = DucoMbBoxInfo(
        serial_number=entry.data[CONF_SERIAL_NUMBER],
        slave_id=entry.data[CONF_SLAVE_ID],
        nodes=tuple(DucoMbNodeInfo(**node) for node in entry.data[CONF_NODES]),
    )
    api = DucoModbusApi(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        box_info.slave_id,
    )
    try:
        coordinator = DucoMbCoordinator(hass, entry, api, box_info)
        await coordinator.async_config_entry_first_refresh()

        entry.runtime_data = DucoMbRuntimeData(coordinator=coordinator)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except UpdateFailed as err:
        await api.async_close()
        raise ConfigEntryNotReady(err) from err
    except Exception:
        await api.async_close()
        raise

    return True


async def async_unload_entry(hass: HomeAssistant, entry: DucoMbConfigEntry) -> bool:
    """Unload a config entry and close its Modbus connection."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.coordinator.api.async_close()
    return unload_ok
