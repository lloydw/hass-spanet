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
        if SK_LIGHTS in coordinator.state:
            entities.append(SpaLightSpeed(coordinator))
    async_add_entity(entities)


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
