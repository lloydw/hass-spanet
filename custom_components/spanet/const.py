"""Constants for the spanet integration."""

DOMAIN = "spanet"
DEVICE_ID = "device_id"

SK_SETTEMP = "setTemperature"
SK_WATERTEMP = "currentTemperature"
SK_HEATER = "heat"
SK_SANITISE = "sanitise"
SK_SLEEPING = "sleep"
SK_FILTERING = "filtering"
SK_PUMPS = "pumps"
SK_OPERATION_MODE = "operationMode"
SK_POWER_SAVE = "powerSave"
SK_HEAT_PUMP = "heatPump"
SK_ELEMENT_BOOST = "elementBoost"
SK_SLEEP_TIMERS = "sleepTimers"
SK_LIGHTS = "lights"
SK_BLOWER = "blower"

SL_HEATING = "Heating"
SL_SLEEPING = "Sleeping"
SL_SANITISE = "Sanitise"
SL_FILTERING = "Filtering"

# Keys within the dashboard "statusFlags" object
SF_SANITISE = "SanitiseOn"
SF_FILTERING = "Filtering"

OPERATION_MODES = ["Unknown", "Normal", "Economy", "Away", "Weekend"]
POWER_SAVE = ["Unknown", "Off", "Low", "High"]
HEAT_PUMP = ["Auto", "Heat", "Cool", "Off"]

OPT_ENABLE_HEAT_PUMP = "enable_heat_pump"

# Blower vocabulary: modeId (write) <-> blowerStatus (read).
BLOWER_MODE_OFF = 1
BLOWER_MODE_VARIABLE = 2
BLOWER_MODE_RAMP = 3
BLOWER_STATUS_OFF = "off"
BLOWER_STATUS_VARIABLE = "vari"
BLOWER_STATUS_RAMP = "ramp"
BLOWER_MODE_TO_STATUS = {
    BLOWER_MODE_OFF: BLOWER_STATUS_OFF,
    BLOWER_MODE_VARIABLE: BLOWER_STATUS_VARIABLE,
    BLOWER_MODE_RAMP: BLOWER_STATUS_RAMP,
}

# --- settings controls (endpoints verified against the SpaNET app) ---
SK_FILT_RUNTIME = "filtrationRuntime"
SK_FILT_INTERVAL = "filtrationInterval"
SK_TIMEOUT = "timeout"
SK_LOCK = "lock"
SK_SANITISE_TIME = "sanitiseTime"

# Filtration total runtime is 1-24 h; "hours between cycles" only accepts
# divisors of 24, so it's a select rather than a free slider.
FILTRATION_RUNTIME_MIN = 1
FILTRATION_RUNTIME_MAX = 24
FILTRATION_INTERVALS = [1, 2, 3, 4, 6, 8, 12, 24]
FILTRATION_INTERVAL_OPTIONS = [str(x) for x in FILTRATION_INTERVALS]

# Keypad lock: list index + 1 == the API lockMode value (1=Off, 2=Partial, 3=Full).
LOCK_MODES = ["Off", "Partial", "Full"]

# Pump/operation auto-off timeout, in minutes.
TIMEOUT_MIN = 10
TIMEOUT_MAX = 60
# SpaNet light control (endpoints verified against the SpaNET app).
# The hardware exposes a fixed named-colour palette; each name is mapped to an
# RGB point by its position on the colour wheel so HA can snap to the nearest.
LIGHT_COLOURS = {
    "white":  (255, 255, 255),
    "red":    (255, 0, 0),
    "orange": (255, 128, 0),
    "lime":   (191, 255, 0),
    "green":  (0, 255, 0),
    "teal":   (0, 200, 200),
    "blue":   (0, 40, 255),
    "pink":   (255, 0, 200),
}
LIGHT_MODES = ["colour", "fade", "step", "party"]
LIGHT_LEVEL_MIN = 1
LIGHT_LEVEL_MAX = 5
