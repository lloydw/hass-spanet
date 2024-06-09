"""SpaNet Sensors"""
from __future__ import annotations
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    HVACMode,
    HVACAction,
    ClimateEntityFeature,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import SpaEntity
from .spanet import SK_SETTEMP, SK_WATERTEMP, SK_HEATER


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in hass.data[DOMAIN]["spas"]:
        entities += [
            SpaClimate(coordinator),
        ]

    async_add_entity(entities)


class SpaClimate(SpaEntity, ClimateEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "climate", "Climate")
        self.hass = coordinator.hass

        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [HVACMode.AUTO]
        self._attr_hvac_mode = HVACMode.AUTO
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_target_temperature_step = 0.2
        self._attr_max_temp = 41.0
        self._attr_min_temp = 5
        self._attr_name = coordinator.spa_name

    @property
    def hvac_action(self) -> HVACAction | str | None:
        status = self.coordinator.get_status_numeric(SK_HEATER)
        if status is None:
            return None
        return HVACAction.HEATING if status == 1 else HVACAction.IDLE

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.get_status_numeric(SK_WATERTEMP, divisor=10)

    @property
    def target_temperature(self) -> float | None:
        return self.coordinator.get_status_numeric(SK_SETTEMP, divisor=10)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if self.coordinator.spa is not None:
            await self.coordinator.spa.set_temperature(kwargs["temperature"])
        await self.coordinator.async_request_refresh()
