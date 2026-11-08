"""Offline regression tests for per-pump GUI options and upgrade compatibility."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "spanet"

spec = importlib.util.spec_from_file_location(
    "spanet_pump_options_test", COMPONENT / "pump_options.py"
)
assert spec is not None and spec.loader is not None
options = importlib.util.module_from_spec(spec)
spec.loader.exec_module(options)


def pump(speed=1, controllable=True, has_auto=False):
    return {
        "speeds": speed,
        "canSwitchOn": controllable,
        "hasSwitch": controllable and (not has_auto or speed > 1),
        "auto": has_auto,
    }


class UpgradeCompatibilityTests(unittest.TestCase):
    def test_older_install_without_options_defaults_to_auto(self):
        self.assertEqual(options.configured_mode({}, "spa-a", "1"),
                         options.PUMP_CONTROL_AUTO)
        self.assertFalse(options.user_confirmed_unverified_two_speed(
            {}, "spa-a", "1"))
        self.assertFalse(options.allows_two_speed_control(pump(1)))
        self.assertTrue(options.allows_two_speed_control(pump(2)))

    def test_existing_heat_pump_option_does_not_affect_pump_defaults(self):
        self.assertEqual(
            options.configured_mode({"enable_heat_pump": True}, "spa-a", "1"),
            options.PUMP_CONTROL_AUTO
        )

    def test_bad_saved_option_falls_back_safely(self):
        stored = {options.OPT_PUMP_CONTROL_MODES: {"spa-a:1": "turbo"}}
        self.assertEqual(options.configured_mode(stored, "spa-a", "1"),
                         options.PUMP_CONTROL_AUTO)

    def test_existing_one_speed_switch_does_not_gain_speed_control(self):
        self.assertFalse(options.allows_two_speed_control(pump(1, True)))
        self.assertFalse(options.allows_two_speed_control(pump(1, False)))
        self.assertFalse(options.allows_two_speed_control(pump(1, True, True)))

    def test_two_speed_adds_selector_while_preserving_switch(self):
        p = pump(2)
        self.assertTrue(p["hasSwitch"])
        self.assertTrue(options.allows_two_speed_control(p))


class MultiPumpIsolationTests(unittest.TestCase):
    def test_two_pumps_same_spa_have_distinct_preferences(self):
        k1 = options.pump_config_key("spa-a", "1")
        k2 = options.pump_config_key("spa-a", "2")
        self.assertNotEqual(k1, k2)
        stored = {options.OPT_PUMP_CONTROL_MODES: {
            k1: options.PUMP_CONTROL_SINGLE,
            k2: options.PUMP_CONTROL_TWO_SPEED,
        }}
        self.assertEqual(options.configured_mode(stored, "spa-a", "1"),
                         options.PUMP_CONTROL_SINGLE)
        self.assertEqual(options.configured_mode(stored, "spa-a", "2"),
                         options.PUMP_CONTROL_TWO_SPEED)

    def test_same_pump_number_two_spas_is_isolated(self):
        key_a = options.pump_config_key("spa-a", "1")
        key_b = options.pump_config_key("spa-b", "1")
        self.assertNotEqual(key_a, key_b)
        stored = {options.OPT_PUMP_CONTROL_MODES: {
            key_a: options.PUMP_CONTROL_SINGLE
        }}
        self.assertEqual(options.configured_mode(stored, "spa-b", "1"),
                         options.PUMP_CONTROL_AUTO)

    def test_undetected_two_speed_override_cannot_leak_to_another_pump(self):
        saved = {options.OPT_PUMP_UNVERIFIED_CONFIRMATIONS: {
            options.pump_config_key("spa-a", "1"): True,
        }}
        self.assertTrue(options.user_confirmed_unverified_two_speed(
            saved, "spa-a", "1"))
        self.assertFalse(options.user_confirmed_unverified_two_speed(
            saved, "spa-a", "2"))
        self.assertFalse(options.user_confirmed_unverified_two_speed(
            saved, "spa-b", "1"))


class OverrideSafetyTests(unittest.TestCase):
    def test_manual_single_hides_two_speed_selector(self):
        self.assertFalse(options.allows_two_speed_control(
            pump(2), options.PUMP_CONTROL_SINGLE))

    def test_manual_two_on_api_verified_two_does_not_need_ack(self):
        self.assertTrue(options.allows_two_speed_control(
            pump(2), options.PUMP_CONTROL_TWO_SPEED, confirmed=False))

    def test_manual_two_on_reported_single_needs_ack(self):
        p = pump(1, True)
        self.assertFalse(options.allows_two_speed_control(
            p, options.PUMP_CONTROL_TWO_SPEED, confirmed=False))
        self.assertTrue(options.allows_two_speed_control(
            p, options.PUMP_CONTROL_TWO_SPEED, confirmed=True))

    def test_manual_two_cannot_control_pump_api_marks_uncontrollable(self):
        self.assertFalse(options.allows_two_speed_control(
            pump(1, False), options.PUMP_CONTROL_TWO_SPEED, confirmed=True))

    def test_three_speed_never_misidentified_as_two(self):
        for choice in options.PUMP_CONTROL_CHOICES:
            self.assertFalse(options.allows_two_speed_control(
                pump(3), choice, confirmed=True))

    def test_invalid_choice_never_enables_controls(self):
        self.assertFalse(options.allows_two_speed_control(
            pump(2), "quad_speed", confirmed=True))

    def test_missing_speed_metadata_is_safe(self):
        p = {"hasSwitch": True, "canSwitchOn": True}
        self.assertFalse(options.allows_two_speed_control(p))
        self.assertFalse(options.allows_two_speed_control(
            p, options.PUMP_CONTROL_TWO_SPEED, confirmed=False))


class SourceIntegrationTests(unittest.TestCase):
    def test_options_flow_is_gui_driven_and_reloads_only_integration(self):
        src = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        self.assertIn("class OptionsFlowHandler(OptionsFlowWithReload):", src)
        self.assertIn("OPT_ENABLE_HEAT_PUMP", src)
        self.assertIn("OPT_PUMP_CONTROL_MODES", src)
        self.assertIn("async_step_confirm_two_speed(", src)
        self.assertIn("self.config_entry.entry_id", src)

    def test_legacy_switch_entity_names_and_send_path_unchanged(self):
        sw = (COMPONENT / "switch.py").read_text(encoding="utf-8")
        co = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('if v["hasSwitch"] or coordinator.is_forced_single_speed_switch(k, v):', sw)
        self.assertIn('f"Pump {k}"', sw)
        self.assertIn('await self.spa.set_pump(pump["apiId"], state)', co)

    def test_sensor_reports_real_hardware_speed_count(self):
        co = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        se = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
        self.assertIn('pump["speeds"] = max(1, int(p.get("pumpSpeed", 1)))', co)
        self.assertIn('"reported_speed_count": pump.get("speeds")', se)

    def test_config_flow_does_not_log_plaintext_credentials(self):
        src = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        self.assertNotIn('Validate - {data[', src)
        self.assertIn('_LOGGER.debug("Validating SpaNET credentials")', src)

    def test_no_pump_command_on_options_save(self):
        cf = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        self.assertNotIn(".set_pump(", cf)
        self.assertNotIn(".set_pump_mode(", cf)


if __name__ == "__main__":
    unittest.main()
