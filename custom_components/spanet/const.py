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
