"""Per-pump, backward-compatible GUI preferences for SpaNET.

Preferences are stored per physical spa ID and pump number. Missing options
always mean automatic detection so upgrading an existing integration requires
no migration and preserves all pre-existing switch entity IDs.
"""

OPT_PUMP_CONTROL_MODES = "pump_control_modes"
OPT_PUMP_UNVERIFIED_CONFIRMATIONS = "pump_unverified_two_speed_confirmations"

PUMP_CONTROL_AUTO = "automatic"
PUMP_CONTROL_SINGLE = "single_speed"
PUMP_CONTROL_TWO_SPEED = "two_speed"
PUMP_CONTROL_CHOICES = (
    PUMP_CONTROL_AUTO,
    PUMP_CONTROL_SINGLE,
    PUMP_CONTROL_TWO_SPEED,
)


def pump_config_key(spa_id: str, pump_number: str) -> str:
    """Scope a per-pump preference to a spa, not just pump number."""
    return f"{spa_id}:{pump_number}"


def configured_mode(options, spa_id: str, pump_number: str) -> str:
    """Return the saved choice, falling back to auto on old installs."""
    saved = (options or {}).get(OPT_PUMP_CONTROL_MODES) or {}
    value = saved.get(pump_config_key(spa_id, pump_number))
    return value if value in PUMP_CONTROL_CHOICES else PUMP_CONTROL_AUTO


def user_confirmed_unverified_two_speed(options, spa_id: str, pump_number: str) -> bool:
    """Did this user explicitly confirm manual two-speed on unverified hardware?"""
    confirmed = (options or {}).get(OPT_PUMP_UNVERIFIED_CONFIRMATIONS) or {}
    return confirmed.get(pump_config_key(spa_id, pump_number)) is True


def allows_two_speed_control(pump, choice=PUMP_CONTROL_AUTO, confirmed=False) -> bool:
    """Whether this pump may expose two-speed control (not the legacy switch).

    Auto: only API-verified exactly two-speed pumps.
    Single: hide the new selector; legacy switch remains untouched.
    Two: API-verified exactly two-speed pumps, OR an API-reported one-speed
    pump with a real controllable output and explicit per-pump consent.
    Three-plus-speed pumps are never mistaken for two-speed controllers.
    """
    try:
        speeds = max(1, int(pump.get("speeds", 1)))
    except (TypeError, ValueError):
        speeds = 1
    if choice == PUMP_CONTROL_SINGLE:
        return False
    if choice not in PUMP_CONTROL_CHOICES:
        return False
    if speeds == 2:
        return bool(pump.get("hasSwitch"))
    if choice == PUMP_CONTROL_TWO_SPEED and speeds == 1 and confirmed:
        return bool(pump.get("canSwitchOn", False))
    return False
