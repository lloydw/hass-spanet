"""SpaNet Sensors"""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from .const import *
from .entity import SpaEntity

import logging
logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []
    for coordinator in hass.data[DOMAIN]["spas"]:
        for k, v in coordinator.get_state(SK_PUMPS).items():
            options = ["off", "auto", "low", "high", "0", "1", "2", "3", "-1"]
            if v["hasSwitch"] and v["speeds"] > 1:
                entities.append(SpaSelect(coordinator, f"Pump {k}", f"pumps.{k}", options, coordinator.set_pump))

    async_add_entity(entities)


class SpaSelect(SpaEntity, SelectEntity):
    """A selector"""

    def __init__(self, coordinator, name, state_key, options, setter) -> None:
        super().__init__(coordinator, "select", name)
        self.hass = coordinator.hass
        self._state_key = state_key
        self._options = options
        self._setter = setter

    @property
    def current_option(self):
        return self.coordinator.get_state(self._state_key, "state")

    @property
    def options(self):
        return self._options

    async def async_select_option(self, option):
        await self._setter(self._state_key, option)
