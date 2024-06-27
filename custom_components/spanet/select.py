"""SpaNet Sensors"""
from __future__ import annotations
import inspect

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
    pumpOptions = ["off", "auto", "low", "high"]

    entities = []

    for coordinator in hass.data[DOMAIN]["spas"]:

        entities.append(SpaSelect(coordinator, "Operation Mode", "operationMode", OPERATION_MODES[1:], coordinator.set_operation_mode))

        for k, v in coordinator.get_state(SK_PUMPS).items():
            if v["hasSwitch"] and v["speeds"] > 1:
                entities.append(SpaSelect(coordinator, f"Pump {k}", f"pumps.{k}", pumpOptions, coordinator.set_pump))

    async_add_entity(entities)


class SpaSelect(SpaEntity, SelectEntity):
    """A selector"""

    def __init__(self, coordinator, name, state_key, options, setter, sub_key=None) -> None:
        super().__init__(coordinator, "select", name)
        self.hass = coordinator.hass
        self._state_key = state_key
        self._options = options
        self._sub_key = sub_key

        sig = inspect.signature(setter)

        self._setter = setter
        self._setter_num_parameters = len(sig.parameters)

    @property
    def current_option(self):
        return self.coordinator.get_state(self._state_key, self._sub_key)

    @property
    def options(self):
        return self._options

    async def async_select_option(self, option):
        if self._setter_num_parameters == 1:
            await self._setter(option)
        elif self._setter_num_parameters == 2:
            await self._setter(self._state_key, option)
