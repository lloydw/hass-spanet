"""The spanet integration."""
from __future__ import annotations

import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, DEVICE_ID
from .spanet import SpaNet
from .coordinator import Coordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CLIMATE, Platform.SWITCH, Platform.SELECT, Platform.FAN, Platform.NUMBER, Platform.TIME]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Set up spanet from a config entry."""

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"spas": []}
    if DEVICE_ID not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DEVICE_ID] = str(uuid.uuid4())

    session = aiohttp_client.async_get_clientsession(hass)
    spanet = SpaNet(session)
    hass.data[DOMAIN][config_entry.entry_id] = spanet
    if "email" not in config_entry.data or "password" not in config_entry.data:
        return True

    await spanet.authenticate(
        config_entry.data["email"],
        config_entry.data["password"],
        hass.data[DOMAIN][DEVICE_ID]
    )
    for spa in spanet.get_available_spas():
        coordinator = Coordinator(hass, spanet, spa, config_entry)
        # Await the first refresh to completion so coordinator.state (pumps,
        # blower, etc.) is fully populated before the platforms set up their
        # entities - otherwise entity creation can race the initial fetch and
        # leave switches (e.g. the blower) orphaned/unavailable.
        await coordinator.async_config_entry_first_refresh()

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={(dr.CONNECTION_NETWORK_MAC, spa["macAddress"])},
            identifiers={
                (DOMAIN, spa["id"]),
            },
            name=spa["name"],
        )
        coordinator.device = device

        hass.data[DOMAIN]["spas"].append(coordinator)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry, cleaning up its platforms and coordinators.

    Previously this was a no-op, so the entry's platforms were never unloaded
    and its coordinators were left in the shared ``spas`` list. Every reload
    therefore stacked another set of coordinators that kept polling the SpaNet
    cloud. Unload the platforms and drop this entry's coordinators/client.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN]["spas"] = [
            coordinator
            for coordinator in hass.data[DOMAIN]["spas"]
            if coordinator.config_entry.entry_id != entry.entry_id
        ]
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
