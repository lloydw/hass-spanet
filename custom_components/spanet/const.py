"""Constants for the spanet integration."""

DOMAIN = "spanet"
DEVICE_ID = "device_id"

SK_SETTEMP = "setTemperature"
SK_WATERTEMP = "currentTemperature"
SK_HEATER = "heat"
SK_SANITISE = "sanitise"
SK_SLEEPING = "sleep"
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
