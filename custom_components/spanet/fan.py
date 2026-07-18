"""SpaNet blower exposed as a fan (on/off, variable speed 1-5, ramp preset)."""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import *
from .entity import SpaEntity

# Mode ids and status strings live in const.py (BLOWER_MODE_*, BLOWER_STATUS_*).
SPEED_RANGE = (1, 5)
PRESET_RAMP = BLOWER_STATUS_RAMP


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []
    for coordinator in hass.data[DOMAIN]["spas"]:
        blower = coordinator.state.get(SK_BLOWER)
        if blower and blower.get("hasSwitch"):
            entities.append(SpaBlowerFan(coordinator, "Blower"))
    async_add_entity(entities)


class SpaBlowerFan(SpaEntity, FanEntity):
    """The spa blower: off / variable (speed 1-5) / ramp."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = [PRESET_RAMP]
    _attr_speed_count = SPEED_RANGE[1] - SPEED_RANGE[0] + 1

    def __init__(self, coordinator, name) -> None:
        super().__init__(coordinator, "fan", name)

    def _blower(self):
        return self.coordinator.get_state(SK_BLOWER)

    @property
    def is_on(self):
        return self._blower().get("status", BLOWER_STATUS_OFF) != BLOWER_STATUS_OFF

    @property
    def preset_mode(self):
        return PRESET_RAMP if self._blower().get("status") == BLOWER_STATUS_RAMP else None

    @property
    def percentage(self):
        # Only variable mode has a meaningful speed; ramp/off report None so a
        # SET_SPEED fan card doesn't render an active ramp as a 0% (off) dial.
        blower = self._blower()
        if blower.get("status") != BLOWER_STATUS_VARIABLE:
            return None
        return ranged_value_to_percentage(SPEED_RANGE, blower.get("speed") or 1)

    async def async_set_percentage(self, percentage: int):
        if percentage == 0:
            await self.coordinator.set_blower_mode(BLOWER_MODE_OFF)
            return
        speed = max(1, round(percentage_to_ranged_value(SPEED_RANGE, percentage)))
        await self.coordinator.set_blower_mode(BLOWER_MODE_VARIABLE, speed)

    async def async_set_preset_mode(self, preset_mode: str):
        if preset_mode == PRESET_RAMP:
            await self.coordinator.set_blower_mode(BLOWER_MODE_RAMP)

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if preset_mode == PRESET_RAMP:
            await self.coordinator.set_blower_mode(BLOWER_MODE_RAMP)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            # Default "on" = variable at the last known speed (fall back to max).
            await self.coordinator.set_blower_mode(
                BLOWER_MODE_VARIABLE, self._blower().get("speed") or SPEED_RANGE[1]
            )

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_blower_mode(BLOWER_MODE_OFF)
