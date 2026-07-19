"""SpaNet time entity (daily sanitise time)."""
from __future__ import annotations

from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
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
        if SK_SANITISE_TIME in coordinator.state:
            entities.append(SpaSanitiseTime(coordinator))
    async_add_entity(entities)


class SpaSanitiseTime(SpaEntity, TimeEntity):
    """The daily automatic sanitise time."""

    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "time", "Sanitise Time")
        self.hass = coordinator.hass

    @property
    def native_value(self):
        raw = self.coordinator.get_state(SK_SANITISE_TIME)
        if not raw or ":" not in str(raw):
            return None
        hh, mm = str(raw).split(":")[:2]
        return dt_time(int(hh), int(mm))

    async def async_set_value(self, value: dt_time):
        await self.coordinator.set_sanitise_time(value.strftime("%H:%M"))
