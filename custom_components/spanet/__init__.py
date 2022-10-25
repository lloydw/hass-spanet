"""The spanet integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .spanet import SpaNet
from .coordinator import Coordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CLIMATE]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Set up spanet from a config entry."""

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"spas": []}

    session = aiohttp_client.async_get_clientsession(hass)
    spanet = SpaNet(session)
    hass.data[DOMAIN][config_entry.entry_id] = spanet
    await spanet.authenticate(
        config_entry.data["username"], config_entry.data["password"]
    )
    for spa in spanet.get_available_spas():
        coordinator = Coordinator(hass, spanet, spa)
        await coordinator.async_request_refresh()

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={(dr.CONNECTION_NETWORK_MAC, spa["mac_addr"])},
            identifiers={
                (DOMAIN, spa["id"]),
            },
            name=spa["name"],
        )
        coordinator.device = device

        hass.data[DOMAIN]["spas"].append(coordinator)

    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
