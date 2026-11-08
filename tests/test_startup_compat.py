"""Offline regression checks for startup retries and single-speed models.

No cloud credentials, network, or live Home Assistant instance needed.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "spanet"


def load(module, file):
    spec = importlib.util.spec_from_file_location(module, COMPONENT / file)
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


startup = load("spanet_startup_test", "startup.py")
modes = load("spanet_modes_startup_test", "pump_modes.py")


def ready_state(speeds=1, has_switch=True):
    return {
        "currentTemperature": 367,
        "setTemperature": 368,
        "heat": 0,
        "sanitise": 0,
        "sleep": 0,
        "filtering": 1,
        "pumps": {"1": {"speeds": speeds, "hasSwitch": has_switch,
                        "state": "off", "auto": False}},
        "lights": {"state": "off"},
        "sleepTimers": {},
        "operationMode": "Normal",
        "powerSave": "Off",
    }


class StartupReadinessTests(unittest.TestCase):
    def test_valid_single_speed_snapshot_is_ready(self):
        self.assertEqual(startup.missing_startup_keys(ready_state()), ())

    def test_valid_two_speed_snapshot_is_ready(self):
        self.assertEqual(startup.missing_startup_keys(ready_state(2)), ())

    def test_all_api_202_errors_cannot_publish_empty_state(self):
        missing = startup.missing_startup_keys({})
        self.assertIn("pumps", missing)
        self.assertIn("currentTemperature", missing)
        self.assertIn("sleepTimers", missing)

    def test_failed_pump_endpoint_prevents_partial_setup(self):
        state = ready_state()
        del state["pumps"]
        self.assertEqual(startup.missing_startup_keys(state), ("pumps",))

    def test_failed_dashboard_endpoint_prevents_partial_setup(self):
        state = ready_state()
        for key in ("currentTemperature", "setTemperature", "heat",
                    "sanitise", "sleep", "filtering"):
            del state[key]
        self.assertIn("currentTemperature", startup.missing_startup_keys(state))

    def test_failed_lights_endpoint_prevents_partial_setup(self):
        state = ready_state()
        state["lights"] = None
        self.assertEqual(startup.missing_startup_keys(state), ("lights",))

    def test_wrong_types_for_core_mappings_are_rejected(self):
        for key, value in (("pumps", []), ("sleepTimers", "oops"),
                           ("lights", [])):
            with self.subTest(key=key):
                state = ready_state()
                state[key] = value
                self.assertEqual(startup.missing_startup_keys(state), (key,))

    def test_optional_settings_and_blower_not_required(self):
        self.assertEqual(startup.missing_startup_keys(ready_state()), ())

    def test_heat_pump_fields_only_required_when_enabled(self):
        state = ready_state()
        self.assertEqual(startup.missing_startup_keys(state), ())
        self.assertEqual(
            startup.missing_startup_keys(state, heat_pump_enabled=True),
            ("heatPump", "elementBoost"),
        )
        state.update({"heatPump": "Auto", "elementBoost": "off"})
        self.assertEqual(
            startup.missing_startup_keys(state, heat_pump_enabled=True), ()
        )

    def test_coordinator_uses_first_refresh_failure_for_ha_auto_retry(self):
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        section = source.split("    async def refresh_state(self):", 1)[1].split(
            "    async def update_dashboard(self):", 1
        )[0]
        self.assertIn("missing_startup_keys(", section)
        self.assertIn("raise UpdateFailed(", section)
        self.assertIn("self._initial_state_ready = True", section)

    def test_setup_never_publishes_spas_before_initial_refresh(self):
        source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        first = source.index("await coordinator.async_config_entry_first_refresh()")
        publish = source.index('hass.data[DOMAIN]["spas"].extend(')
        self.assertLess(first, publish)


class SingleSpeedCompatibilityTests(unittest.TestCase):
    def test_controllable_single_speed_has_no_new_mode_entities(self):
        p = {"speeds": 1, "hasSwitch": True, "auto": False}
        self.assertFalse(modes.has_mode_sensor(p))
        self.assertFalse(modes.has_mode_control(p))

    def test_noncontrollable_single_speed_has_no_new_mode_entities(self):
        p = {"speeds": 1, "hasSwitch": False, "auto": True}
        self.assertFalse(modes.has_mode_sensor(p))
        self.assertFalse(modes.has_mode_control(p))

    def test_two_speed_controllable_gets_both(self):
        p = {"speeds": 2, "hasSwitch": True, "auto": True}
        self.assertTrue(modes.has_mode_sensor(p))
        self.assertTrue(modes.has_mode_control(p))

    def test_two_speed_without_controls_gets_sensor_only(self):
        p = {"speeds": 2, "hasSwitch": False}
        self.assertTrue(modes.has_mode_sensor(p))
        self.assertFalse(modes.has_mode_control(p))

    def test_three_speed_never_gets_two_speed_selector(self):
        p = {"speeds": 3, "hasSwitch": True}
        self.assertTrue(modes.has_mode_sensor(p))
        self.assertFalse(modes.has_mode_control(p))

    def test_missing_speed_metadata_falls_back_to_one_speed(self):
        p = {"hasSwitch": True}
        self.assertFalse(modes.has_mode_sensor(p))
        self.assertFalse(modes.has_mode_control(p))

    def test_legacy_switch_keeps_same_gate_and_path(self):
        source = (COMPONENT / "switch.py").read_text(encoding="utf-8")
        self.assertIn('if v["hasSwitch"] or coordinator.is_forced_single_speed_switch(k, v):', source)
        coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('await self.spa.set_pump(pump["apiId"], state)', coordinator)


if __name__ == "__main__":
    unittest.main()
