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
from .pump_modes import normalize_pump_mode, has_mode_sensor

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
            SpaBinarySensor(coordinator, "Filtering", SK_FILTERING),
        ]

        for k, v in coordinator.get_state(SK_PUMPS).items():
            if has_mode_sensor(v) or coordinator.is_pump_mode_control_enabled(k, v):
                entities.append(SpaPumpModeSensor(coordinator, k))
            if not v["hasSwitch"]:
                entities.append(SpaBinarySensor(coordinator, f"Pump {k}", f"pumps.{k}.state"))

    async_add_entity(entities)


class SpaSensor(SpaEntity):
    """A sensor"""

    def __init__(self, coordinator, name, status_id) -> None:
        super().__init__(coordinator, "sensor", name)
        self.hass = coordinator.hass
        self._status_id = status_id


class SpaPumpModeSensor(SpaSensor, SensorEntity):
    """Read-only reported mode for a multi-speed pump."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["off", "low", "high", "auto", "on"]

    def __init__(self, coordinator, pump_number) -> None:
        self._pump_number = str(pump_number)
        super().__init__(coordinator, f"Pump {pump_number} Mode", f"{SK_PUMPS}.{pump_number}.state")

    @property
    def native_value(self):
        return normalize_pump_mode(self.coordinator.get_state(self._status_id))

    @property
    def extra_state_attributes(self):
        pump = self.coordinator.get_state(f"{SK_PUMPS}.{self._pump_number}")
        return {
            "reported_speed_count": pump.get("speeds"),
            "supports_auto": pump.get("auto"),
        }


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
