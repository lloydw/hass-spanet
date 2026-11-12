"""Validate the minimum SpaNET cloud snapshot before entity platform setup.

Pure Python so offline tests can cover different pump and spa hardware.
A missing startup snapshot must fail the initial coordinator refresh;
Home Assistant will then retry the config entry automatically.
"""
from __future__ import annotations

from collections.abc import Mapping

# These values are consumed unconditionally by existing SpaNET platforms.
# Optional filtration/settings and optional blower data are deliberately
# excluded, so hardware without those capabilities can still initialise.
REQUIRED_KEYS = (
    "currentTemperature",
    "setTemperature",
    "heat",
    "sanitise",
    "sleep",
    "filtering",
    "pumps",
    "lights",
    "sleepTimers",
    "operationMode",
    "powerSave",
)
REQUIRED_HEAT_PUMP_KEYS = ("heatPump", "elementBoost")
REQUIRED_MAPPINGS = ("pumps", "lights", "sleepTimers")


def missing_startup_keys(
    state: Mapping[str, object],
    *,
    heat_pump_enabled: bool = False,
) -> tuple[str, ...]:
    """Return absent/invalid core keys, without requiring any pump speed."""
    required = REQUIRED_KEYS + (
        REQUIRED_HEAT_PUMP_KEYS if heat_pump_enabled else ()
    )
    missing = []
    for key in required:
        if key not in state or state[key] is None:
            missing.append(key)
        elif key in REQUIRED_MAPPINGS and not isinstance(state[key], dict):
            missing.append(key)
    return tuple(missing)
