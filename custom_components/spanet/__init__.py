"""The spanet integration."""
from __future__ import annotations

import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import Platform
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, DEVICE_ID
from .spanet import SpaNet, SpaNetApiError
from .coordinator import Coordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CLIMATE, Platform.SWITCH, Platform.SELECT, Platform.FAN, Platform.LIGHT, Platform.NUMBER, Platform.TIME]

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
    if "email" not in config_entry.data or "password" not in config_entry.data:
        hass.data[DOMAIN][config_entry.entry_id] = spanet
        return True

    try:
        await spanet.authenticate(
            config_entry.data["email"],
            config_entry.data["password"],
            hass.data[DOMAIN][DEVICE_ID]
        )
    except SpaNetApiError as exc:
        # Authentication/device-list HTTP 202 is a temporary service failure.
        # Let Home Assistant retry rather than treating it as bad credentials.
        if exc.response.status == 202 or exc.response.status >= 500:
            raise ConfigEntryNotReady(
                f"SpaNET cloud unavailable (HTTP {exc.response.status})"
            ) from exc
        raise
    # Build an entire ready snapshot before publishing any coordinator.
    # When an API endpoint returns transient 202, first_refresh raises
    # ConfigEntryNotReady and HA retries setup automatically. Keeping the
    # list local prevents a failed multi-spa attempt from leaking partial
    # coordinators into the global registry.
    ready_spas = []
    for spa in spanet.get_available_spas():
        coordinator = Coordinator(hass, spanet, spa, config_entry)
        await coordinator.async_config_entry_first_refresh()
        ready_spas.append((spa, coordinator))

    device_registry = dr.async_get(hass)
    for spa, coordinator in ready_spas:
        device = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={(dr.CONNECTION_NETWORK_MAC, spa["macAddress"])},
            identifiers={
                (DOMAIN, spa["id"]),
            },
            name=spa["name"],
        )
        coordinator.device = device

    hass.data[DOMAIN][config_entry.entry_id] = spanet
    hass.data[DOMAIN]["spas"].extend(
        coordinator for _, coordinator in ready_spas
    )

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
