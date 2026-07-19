import logging
from datetime import timedelta
import async_timeout
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import *
from .spanet import SpaNetApiError
from .scheduler import Scheduler

logger = logging.getLogger(__name__)

class Coordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, spanet, spa_config, config_entry):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            logger,
            name=spa_config["name"],
            update_interval=timedelta(seconds=60),
        )
        self.spanet = spanet
        self.spa_config = spa_config
        self.config_entry = config_entry
        self.state = {}
        self.spa = None

        self.scheduler = Scheduler()

        self.tasks = [
            self.scheduler.add_task(120, self.update_dashboard),
            self.scheduler.add_task(300, self.update_pumps),
            self.scheduler.add_task(1200, self.update_information),
            self.scheduler.add_task(1200, self.update_lights),
            self.scheduler.add_task(1200, self.update_filtration),
            self.scheduler.add_task(1200, self.update_settings)
        ]

    @property
    def spa_name(self):
        return self.spa_config["name"]

    @property
    def spa_id(self):
        return self.spa_config["id"]

    def queue_refresh(self):
        self.tasks[0].trigger(20)

    def get_state(self, key: str, sub_key=None):
        obj = self.state
        path = key.split('.')
        if sub_key is not None:
            path.append(sub_key)
        try:
            for p in path:
                obj = obj[p]
            return obj
        except (KeyError, IndexError) as exc:
            logger.error("Failed to load data for status key %s", key, exc_info=exc)
            logger.error("Status: %s", self.state)
            raise

    def get_state_numeric(self, key: str, divisor=1):
        value = self.get_state(key)
        if value is None:
            return None
        return int(value) / divisor

    async def set_temperature(self, temp: int):
        self.state[SK_SETTEMP] = temp
        await self.spa.set_temperature(temp)
        logger.debug(f"SET TEMP: {temp} -> {self.state}")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_pump(self, key: str, state: str):
        pump = self.get_state(f"{SK_PUMPS}.{key}")
        pump["state"] = state
        await self.spa.set_pump(pump["apiId"], state)
        logger.debug(f"SET PUMP {key}: {state} -> {self.state}")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_lights(self, state: str):
        lights = self.get_state(f"{SK_LIGHTS}")
        lights["state"] = state
        await self.spa.set_light_status(lights["apiId"], 1 if state == "on" else 0)
        logger.debug(f"SET LIGHTS: {state} -> {self.state}")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_light_brightness(self, level: int):
        lights = self.get_state(SK_LIGHTS)
        lights["brightness"] = level
        await self.spa.set_light_brightness(lights["apiId"], level)
        logger.debug(f"SET LIGHT BRIGHTNESS: {level} -> {self.state}")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_light_colour(self, colour: str):
        lights = self.get_state(SK_LIGHTS)
        lights["colour"] = colour
        await self.spa.set_light_colour(lights["apiId"], colour)
        logger.debug(f"SET LIGHT COLOUR: {colour} -> {self.state}")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_light_mode(self, mode: str):
        lights = self.get_state(SK_LIGHTS)
        lights["mode"] = mode
        await self.spa.set_light_mode(lights["apiId"], mode)
        logger.debug(f"SET LIGHT MODE: {mode} -> {self.state}")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_light_speed(self, speed: int):
        lights = self.get_state(SK_LIGHTS)
        lights["speed"] = speed
        await self.spa.set_light_speed(lights["apiId"], speed)
        logger.debug(f"SET LIGHT SPEED: {speed} -> {self.state}")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_operation_mode(self, mode: str):
        modeIndex = OPERATION_MODES.index(mode)
        if modeIndex < 0:
            logger.error(f"Unknown operation mode: {mode}")
            return

        await self.spa.set_operation_mode(modeIndex)
        self.state[SK_OPERATION_MODE] = mode
        logger.debug(f"SET OPERATION MODE: {mode} -> {self.state}")
        await self.async_request_refresh()

    async def set_power_save(self, mode: str):
        modeIndex = POWER_SAVE.index(mode)
        if modeIndex < 0:
            logger.error(f"Unknown power save: {mode}")
            return

        await self.spa.set_power_save(modeIndex)
        self.state[SK_POWER_SAVE] = mode
        logger.debug(f"SET POWER SAVE: {mode} -> {self.state}")
        await self.async_request_refresh()

    async def set_sleep_timer(self, key: str, value: str):
        timer = self.get_state(f"{SK_SLEEP_TIMERS}.{key}")
        timer["state"] = value
        await self.spa.set_sleep_timer(timer["apiId"], timer['number'], value == "on")
        logger.debug(f"SET SLEEP TIMER {key}: {value} -> {self.state}")
        await self.async_request_refresh()

    async def set_heat_pump(self, mode: str):
        modeIndex = HEAT_PUMP.index(mode)
        if modeIndex < 0:
            logger.error(f"Unknown heat pump: {mode}")
            return

        await self.spa.set_heat_pump(modeIndex)
        self.state[SK_HEAT_PUMP] = mode
        logger.debug(f"SET HEAT PUMP: {mode} -> {self.state}")
        await self.async_request_refresh()

    async def set_element_boost(self, value: str):
        await self.spa.set_element_boost(1 if value == "on" else 0)
        self.state[SK_ELEMENT_BOOST] = value
        logger.debug(f"SET ELEMENT BOOST: {value} -> {self.state}")
        await self.async_request_refresh()

    async def set_blower_mode(self, mode_id: int, speed: int = 0):
        # modeId: 1 = off, 2 = variable (speed 1-5), 3 = ramp.
        blower = self.get_state(SK_BLOWER)
        await self.spa.set_blower(blower["apiId"], mode_id, speed)
        blower["status"] = BLOWER_MODE_TO_STATUS.get(mode_id, blower.get("status"))
        if mode_id == BLOWER_MODE_VARIABLE and speed:
            blower["speed"] = speed
        logger.debug(f"SET BLOWER: mode={mode_id} speed={speed} -> {self.state}")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_sanitise(self, value: str):
        on = value == "on"
        await self.spa.set_sanitise(on)
        self.state[SK_SANITISE] = 1 if on else 0
        logger.debug(f"SET SANITISE: {value} -> {self.state}")
        await self.async_request_refresh()

    async def set_filtration_runtime(self, value: int):
        self.state[SK_FILT_RUNTIME] = int(value)
        await self.spa.set_filtration("totalRuntime", int(value))
        logger.debug(f"SET FILTRATION RUNTIME: {value} -> {self.state}")
        await self.async_request_refresh()

    async def set_filtration_interval(self, value: str):
        self.state[SK_FILT_INTERVAL] = str(value)
        await self.spa.set_filtration("inBetweenCycles", int(value))
        logger.debug(f"SET FILTRATION INTERVAL: {value} -> {self.state}")
        await self.async_request_refresh()

    async def set_timeout(self, value: int):
        self.state[SK_TIMEOUT] = int(value)
        await self.spa.set_timeout(int(value))
        logger.debug(f"SET TIMEOUT: {value} -> {self.state}")
        await self.async_request_refresh()

    async def set_lock(self, mode: str):
        self.state[SK_LOCK] = mode
        await self.spa.set_lock(LOCK_MODES.index(mode) + 1)
        logger.debug(f"SET LOCK: {mode} -> {self.state}")
        await self.async_request_refresh()

    async def set_sanitise_time(self, time_str: str):
        self.state[SK_SANITISE_TIME] = time_str
        await self.spa.set_sanitise_time(time_str)
        logger.debug(f"SET SANITISE TIME: {time_str} -> {self.state}")
        await self.async_request_refresh()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            if not self.spa:
                self.spa = await self.spanet.get_spa(self.spa_id)
            async with async_timeout.timeout(10):
                await self.refresh_state()

        except SpaNetApiError as exc:
            logger.error(f"API Error: {exc}")
            raise UpdateFailed("Failed updating spanet") from exc

    async def refresh_state(self):
        await self.scheduler.tick()
        logger.debug(f"Spa {self.spa_id} Status: {self.state}")

    async def update_dashboard(self):
        dashboard_data = await self.spa.get_dashboard()
        logger.debug(f"Update Dashboard {dashboard_data}")

        self.state[SK_SETTEMP] = dashboard_data["setTemperature"]
        self.state[SK_WATERTEMP] = dashboard_data["currentTemperature"]

        status_list = []
        for s in dashboard_data["statusList"]:
            status_list.append(s.split(" ")[0])

        force_refresh = self.state.get("statusList") != status_list

        self.state["statusList"] = status_list

        # Some spa models (e.g. SVM2/SVMINI2) don't report sanitise or filtration
        # in statusList, only via the sanitiseOn boolean and statusFlags.
        status_flags = dashboard_data.get("statusFlags") or {}

        self.state[SK_HEATER] = 1 if SL_HEATING in status_list else 0
        self.state[SK_SLEEPING] = 1 if SL_SLEEPING in status_list else 0
        self.state[SK_SANITISE] = 1 if (
            dashboard_data.get("sanitiseOn")
            or status_flags.get(SF_SANITISE)
            or SL_SANITISE in status_list
        ) else 0
        self.state[SK_FILTERING] = 1 if (
            status_flags.get(SF_FILTERING) or SL_FILTERING in status_list
        ) else 0

        if force_refresh:
            for task in self.tasks[1:]:
                task.trigger()

    async def update_pumps(self):
        pump_data = await self.spa.get_pumps()
        logger.debug(f"Update Pumps {pump_data}")

        pumps = self.state.get("pumps", {})
        for p in pump_data.get("pumpAndBlower", {}).get("pumps", []):
            pump_id = str(p["pumpNumber"])
            if not pump_id in pumps:
                pumps[pump_id] = {}
            pump = pumps.get(pump_id)
            pump["apiId"] = str(p["id"])
            pump["auto"] = p["hasAuto"]
            pump["speeds"] = 1 # p["pumpSpeed"] Multiple speeds not supported
            pump["hasSwitch"] = p["canSwitchOn"] and (not p["hasAuto"] or p["pumpSpeed"] > 1)
            pump["state"] = p["pumpStatus"]

        self.state[SK_PUMPS] = pumps

        blower = pump_data.get("pumpAndBlower", {}).get("blower")
        if blower and blower.get("id") is not None:
            # blowerStatus is "off", "vari" (variable speed) or "ramp";
            # coerce a missing/null status to "off" so is_on can't read a phantom on.
            self.state[SK_BLOWER] = {
                "apiId": str(blower["id"]),
                "status": blower.get("blowerStatus") or BLOWER_STATUS_OFF,
                "speed": blower.get("blowerVariableSpeed", 0),
                "hasSwitch": blower.get("canSwitchOn", False),
            }

    async def update_information(self):
        information_data = await self.spa.get_information()
        logger.debug(f"Update Information {information_data}")

        settingsSummary = information_data.get("information", {}).get("settingsSummary", {})

        operation_mode = self.fuzzyFind(OPERATION_MODES, settingsSummary.get("operationMode"))
        self.state[SK_OPERATION_MODE] = operation_mode

        power_save = int(settingsSummary.get("powersaveTimer", {}).get("mode"))
        self.state[SK_POWER_SAVE] = POWER_SAVE[power_save]

        if self.config_entry.options.get(OPT_ENABLE_HEAT_PUMP, False):
            heat_pump = int(settingsSummary.get("heatPumpMode"))
            self.state[SK_HEAT_PUMP] = HEAT_PUMP[heat_pump]

            element_boost = settingsSummary.get("hpElementBoost")
            self.state[SK_ELEMENT_BOOST] = "on" if element_boost == "1" else "off"
        else:
            self.state[SK_HEAT_PUMP] = 'Off'
            self.state[SK_ELEMENT_BOOST] = "off"

        timers = {}
        for t in settingsSummary.get("sleepTimers", []):
            timer_id = str(t["timerNumber"])
            if not timer_id in timers:
                timers[timer_id] = {}
            timer = timers.get(timer_id)
            timer['number'] = t["timerNumber"]
            timer["apiId"] = t["id"]
            if 'state' in t: # New format
                timer['state'] = t['state']
            elif 'isEnabled' in t:
                timer["state"] = 'on' if t["isEnabled"] else 'off'
        self.state[SK_SLEEP_TIMERS] = timers

    async def update_lights(self):
        light_details = await self.spa.get_light_details()
        logger.debug(f"Update Lights {light_details}")
        self.state[SK_LIGHTS] = {
            "apiId": light_details.get('lightId'),
            "state": "on" if light_details.get('lightOn') else "off",
            "mode": light_details.get('lightMode'),
            "colour": light_details.get('lightColour'),
            "brightness": light_details.get('lightBrightness'),
            "speed": light_details.get('lightSpeed'),
        }

    async def update_filtration(self):
        data = await self.spa.get_filtration()
        logger.debug(f"Update Filtration {data}")
        self.state[SK_FILT_RUNTIME] = data.get("totalRuntime")
        interval = data.get("inBetweenCycles")
        interval = str(interval) if interval is not None else None
        # keep the select's option valid (avoids HA "not a valid option" warnings)
        self.state[SK_FILT_INTERVAL] = interval if interval in FILTRATION_INTERVAL_OPTIONS else None

    async def update_settings(self):
        data = await self.spa.get_settings_details()
        logger.debug(f"Update Settings {data}")

        timeout = data.get("timeout")
        self.state[SK_TIMEOUT] = int(timeout) if str(timeout).isdigit() else None

        # API returns e.g. "OFF"/"PARTIAL"/"FULL"; normalise to the select options.
        lock = data.get("lockMode")
        lock = lock.capitalize() if isinstance(lock, str) else None
        self.state[SK_LOCK] = lock if lock in LOCK_MODES else None

        self.state[SK_SANITISE_TIME] = data.get("sanitiseTime")

    def fuzzyFind(self, modes, mode):
        for m in modes:
            if m.lower().startswith(mode.lower()):
                return m
        return None


