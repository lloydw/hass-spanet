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

        entities.append(SpaSelect(coordinator, "Operation Mode", SK_OPERATION_MODE, OPERATION_MODES[1:], coordinator.set_operation_mode))
        entities.append(SpaSelect(coordinator, "Power Save", SK_POWER_SAVE, POWER_SAVE[1:], coordinator.set_power_save))

        if config_entry.options.get(OPT_ENABLE_HEAT_PUMP, False):
            entities.append(SpaSelect(coordinator, "Heat Pump", SK_HEAT_PUMP, HEAT_PUMP, coordinator.set_heat_pump))

        # Each pump uses its saved preference or automatic detection.
        # No hardcoded flag or global change to existing switch entities.
        for k, v in coordinator.get_state(SK_PUMPS).items():
            if coordinator.is_pump_mode_control_enabled(k, v):
                entities.append(SpaPumpModeSelect(coordinator, k, v["auto"]))

        if SK_FILT_INTERVAL in coordinator.state:
            entities.append(SpaSelect(coordinator, "Filtration Interval", SK_FILT_INTERVAL,
                                      FILTRATION_INTERVAL_OPTIONS, coordinator.set_filtration_interval))
        if SK_LOCK in coordinator.state:
            entities.append(SpaSelect(coordinator, "Keypad Lock", SK_LOCK, LOCK_MODES, coordinator.set_lock))

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


class SpaPumpModeSelect(SpaEntity, SelectEntity):
    """Explicitly opted-in mode control for a confirmed two-speed pump."""

    def __init__(self, coordinator, pump_number: str, has_auto: bool) -> None:
        super().__init__(coordinator, "select", f"Pump {pump_number} Mode")
        self._pump_number = str(pump_number)
        self._attr_options = ["off"] + (["auto"] if has_auto else []) + ["low", "high"]

    @property
    def current_option(self):
        state = self.coordinator.get_state(f"{SK_PUMPS}.{self._pump_number}.state")
        return state if state in self.options else None

    async def async_select_option(self, option):
        if option not in self.options:
            raise ValueError(f"Unsupported pump option: {option!r}")
        await self.coordinator.set_pump_mode(self._pump_number, option)
