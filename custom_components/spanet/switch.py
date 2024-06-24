"""SpaNet Sensors"""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
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
        for k, v in coordinator.get_state(SK_PUMPS).items():
            if v["hasSwitch"] and v["speeds"] == 1:
                entities.append(SpaSwitch(coordinator, f"Pump {k}", f"pumps.{k}"))

    async_add_entity(entities)


class SpaSwitch(SpaEntity, SwitchEntity):
    """A switch"""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator, name, state_key) -> None:
        super().__init__(coordinator, "switch", name)
        self.hass = coordinator.hass
        self._state_key = state_key

    @property
    def is_on(self):
        value = self.coordinator.get_state(self._state_key, "state")
        if not value:
            return None
        if value == "on" or value == "auto":
            return True
        if value == "off":
            return False
        return int(value) == 1

    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_pump(self.state_key, "on")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_pump(self.state_key, "off")

    def entity_default_value(self):
        """Return False as the default value for this entity type."""
        return False
