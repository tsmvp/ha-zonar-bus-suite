"""The Zonar Bus Suite integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZonarApi
from .coordinator import ZonarCoordinator

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR]

type ZonarConfigEntry = ConfigEntry[ZonarCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ZonarConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = ZonarApi(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    coordinator = ZonarCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZonarConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
