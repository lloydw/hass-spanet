"""SpaNet number entities."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import *
from .entity import SpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []
    for coordinator in hass.data[DOMAIN]["spas"]:
        if SK_FILT_RUNTIME in coordinator.state:
            entities.append(SpaNumber(
                coordinator, "Filtration Runtime", SK_FILT_RUNTIME,
                FILTRATION_RUNTIME_MIN, FILTRATION_RUNTIME_MAX, "h",
                "mdi:water-sync", coordinator.set_filtration_runtime))
        if SK_TIMEOUT in coordinator.state:
            entities.append(SpaNumber(
                coordinator, "Pump Timeout", SK_TIMEOUT,
                TIMEOUT_MIN, TIMEOUT_MAX, "min",
                "mdi:timer-cog-outline", coordinator.set_timeout))
        if SK_LIGHTS in coordinator.state:
            entities.append(SpaLightSpeed(coordinator))
    async_add_entity(entities)

class SpaNumber(SpaEntity, NumberEntity):
    """A settable integer setting."""

    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, name, state_key, min_v, max_v, unit, icon, setter) -> None:
        super().__init__(coordinator, "number", name)
        self.hass = coordinator.hass
        self._state_key = state_key
        self._setter = setter
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self):
        value = self.coordinator.get_state(self._state_key)
        return None if value is None else int(value)

    async def async_set_native_value(self, value: float):
        await self._setter(int(value))


class SpaLightSpeed(SpaEntity, NumberEntity):
    """Effect speed for the spa light (fade / step / party modes)."""

    _attr_native_min_value = LIGHT_LEVEL_MIN
    _attr_native_max_value = LIGHT_LEVEL_MAX
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "number", "Light Speed")
        self.hass = coordinator.hass

    @property
    def native_value(self):
        return self.coordinator.get_state(SK_LIGHTS).get("speed")

    async def async_set_native_value(self, value: float):
        await self.coordinator.set_light_speed(int(value))
