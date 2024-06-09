"""SpaNet Sensors"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from .const import DOMAIN
from .entity import SpaEntity
from .spanet import *


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in hass.data[DOMAIN]["spas"]:
        entities += [
            SpaTemperatureSensor(coordinator, "Water Temperature", SK_WATERTEMP),
            SpaTemperatureSensor(coordinator, "Set Temperature", SK_SETTEMP),
            SpaBinarySensor(coordinator, "Heater", SK_HEATER),
            SpaBinarySensor(coordinator, "Sanitise", SK_SANITISE),
            SpaBinarySensor(coordinator, "Sleeping", SK_SLEEPING),
        ]

    async_add_entity(entities)


class SpaSensor(SpaEntity):
    """A sensor"""

    def __init__(self, coordinator, name, status_id) -> None:
        super().__init__(coordinator, "sensor", name)
        self.hass = coordinator.hass
        self._status_id = status_id


class SpaTemperatureSensor(SpaSensor, SensorEntity):
    """A temp sensor"""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE

    @property
    def native_value(self):
        value = self.coordinator.spa.get_status(self._status_id)
        if not value:
            return None
        return int(value) / 10


class SpaBinarySensor(SpaSensor, BinarySensorEntity):
    """A binary sensor"""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self):
        value = self.coordinator.spa.get_status(self._status_id)
        if not value:
            return None
        return int(value) == 1
