"""Pure state helpers for the SpaNET cloud pump integration.

Kept independent of Home Assistant so state mapping can be unit-tested.
No pump commands are issued here.
"""

PUMP_MODES = ("off", "low", "high", "auto", "on")

def has_mode_sensor(pump):
    """Only multi-speed pumps receive a dedicated mode sensor."""
    return pump.get("speeds", 1) > 1


def has_mode_control(pump):
    """Only controllable, exactly two-speed pumps get the mode selector."""
    return bool(pump.get("hasSwitch")) and pump.get("speeds") == 2



def normalize_pump_mode(value):
    """Return a recognized cloud-reported pump mode, or None."""
    if not isinstance(value, str):
        return None
    mode = value.strip().lower()
    return mode if mode in PUMP_MODES else None


def switch_on_from_status(value):
    """Legacy switch representation of cloud state.

    Auto retains the pre-existing 'on' interpretation. It means the pump is
    enabled for automatic operation, not proof its motor is spinning.
    """
    mode = normalize_pump_mode(value)
    if mode == "off":
        return False
    if mode in ("on", "low", "high", "auto"):
        return True
    if value is None or value == "":
        return None
    try:
        return int(value) == 1
    except (TypeError, ValueError):
        return None
