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


from .const import *
from .entity import SpaEntity

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

        for k, v in coordinator.get_state(SK_PUMPS).items():
            if not v["hasSwitch"]:
                entities.append(SpaBinarySensor(coordinator, f"Pump {k}", f"pumps.{k}.status"))

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
        value = self.coordinator.get_state(self._status_id)
        if not value:
            return None
        return int(value) / 10


class SpaBinarySensor(SpaSensor, BinarySensorEntity):
    """A binary sensor"""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self):
        value = self.coordinator.get_state(self._status_id)
        if value is None:
            return None
        if value == "on":
            return True
        if value == "off":
            return False
        if value == "auto":
            return False
        return int(value) == 1
