"""SpaNet light (brightness + colour + mode)."""
from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
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
    entities = []
    for coordinator in hass.data[DOMAIN]["spas"]:
        if SK_LIGHTS in coordinator.state:
            entities.append(SpaLight(coordinator))
    async_add_entity(entities)


def nearest_colour(rgb):
    """Snap an arbitrary RGB to the nearest name in the SpaNet palette."""
    r, g, b = rgb
    return min(
        LIGHT_COLOURS,
        key=lambda name: (r - LIGHT_COLOURS[name][0]) ** 2
        + (g - LIGHT_COLOURS[name][1]) ** 2
        + (b - LIGHT_COLOURS[name][2]) ** 2,
    )


def level_to_ha(level):
    """SpaNet brightness 1-5 -> HA 0-255."""
    if not level:
        return None
    return max(1, min(255, round(int(level) / LIGHT_LEVEL_MAX * 255)))


def ha_to_level(brightness):
    """HA brightness 0-255 -> SpaNet 1-5."""
    level = round(int(brightness) / 255 * LIGHT_LEVEL_MAX)
    return max(LIGHT_LEVEL_MIN, min(LIGHT_LEVEL_MAX, level))


class SpaLight(SpaEntity, LightEntity):
    """The spa's RGB light."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = LIGHT_MODES

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "light", "Lights")
        self.hass = coordinator.hass

    def _lights(self):
        return self.coordinator.get_state(SK_LIGHTS)

    @property
    def is_on(self):
        return self._lights().get("state") == "on"

    @property
    def brightness(self):
        return level_to_ha(self._lights().get("brightness"))

    @property
    def rgb_color(self):
        # Fall back to white for a colour name we don't have mapped, so the
        # RGB color mode always has a valid value (spa models may differ).
        return LIGHT_COLOURS.get(self._lights().get("colour"), (255, 255, 255))

    @property
    def effect(self):
        mode = self._lights().get("mode")
        return mode if mode in LIGHT_MODES else None

    async def async_turn_on(self, **kwargs):
        lights = self._lights()

        # A colour pick also forces the controller back into solid-colour mode.
        if ATTR_RGB_COLOR in kwargs:
            await self.coordinator.set_light_colour(nearest_colour(kwargs[ATTR_RGB_COLOR]))
            if lights.get("mode") != "colour":
                await self.coordinator.set_light_mode("colour")

        if ATTR_EFFECT in kwargs:
            await self.coordinator.set_light_mode(kwargs[ATTR_EFFECT])

        if ATTR_BRIGHTNESS in kwargs:
            await self.coordinator.set_light_brightness(ha_to_level(kwargs[ATTR_BRIGHTNESS]))

        if not self.is_on:
            await self.coordinator.set_lights("on")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_lights("off")
