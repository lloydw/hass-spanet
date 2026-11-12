"""Offline regression tests for SpaNET two-speed pump support.

No Home Assistant configuration, network access, or SpaNET credentials are used.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "spanet"


def load_file(module_name: str, filename: str):
    """Load isolated source files without initialising the HA integration."""
    spec = importlib.util.spec_from_file_location(module_name, COMPONENT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modes = load_file("spanet_pump_modes_test", "pump_modes.py")
api = load_file("spanet_api_test", "spanet.py")


class PumpStateTests(unittest.TestCase):
    def test_known_modes_are_normalised(self):
        for raw, expected in (
            ("off", "off"),
            (" LOW ", "low"),
            ("High", "high"),
            ("AUTO", "auto"),
            ("on", "on"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(modes.normalize_pump_mode(raw), expected)

    def test_unknown_modes_remain_unknown(self):
        for raw in (None, "", "variable", "sleep", 2, {}, "unknown"):
            with self.subTest(raw=raw):
                self.assertIsNone(modes.normalize_pump_mode(raw))

    def test_switch_handles_two_speed_states(self):
        for raw in ("on", "low", "high", "auto", "1", 1):
            with self.subTest(raw=raw):
                self.assertIs(modes.switch_on_from_status(raw), True)
        for raw in ("off", "0", 0, 2):
            with self.subTest(raw=raw):
                self.assertIs(modes.switch_on_from_status(raw), False)

    def test_switch_gracefully_handles_unrecognised_states(self):
        for raw in ("???", None, ""):
            with self.subTest(raw=raw):
                self.assertIsNone(modes.switch_on_from_status(raw))

    def test_selector_is_configured_per_pump_not_hardcoded(self):
        source = (COMPONENT / "select.py").read_text(encoding="utf-8")
        self.assertNotIn("ENABLE_EXPERIMENTAL_V2_PUMP_SELECT", source)
        self.assertIn("coordinator.is_pump_mode_control_enabled(k, v)", source)
        self.assertIn("SpaPumpModeSelect(", source)


class FakeClient:
    def __init__(self):
        self.requests = []

    async def put(self, path, payload):
        self.requests.append((path, payload))
        return {"success": True}


class PumpApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = FakeClient()
        self.spa = api.SpaPool({"id": "dummy-spa", "name": "Fixture"}, self.client)

    async def test_four_modes_send_expected_payload(self):
        for mode, mode_id in (("off", 2), ("low", 5),
                              ("high", 6), ("auto", 3)):
            with self.subTest(mode=mode):
                await self.spa.set_pump("dummy-pump", mode, 5)
                self.assertEqual(
                    self.client.requests[-1],
                    (
                        "/PumpsAndBlower/SetPump/dummy-pump",
                        {"deviceId": "dummy-spa", "modeId": mode_id,
                         "pumpVariableSpeed": 5},
                    ),
                )

    async def test_legacy_switch_keeps_zero_variable_speed(self):
        for mode, mode_id in (("on", 1), ("off", 2)):
            with self.subTest(mode=mode):
                await self.spa.set_pump("dummy-pump", mode)
                self.assertEqual(
                    self.client.requests[-1][1],
                    {"deviceId": "dummy-spa", "modeId": mode_id,
                     "pumpVariableSpeed": 0},
                )

    async def test_invalid_mode_or_speed_never_sends_request(self):
        for mode, speed in (("turbo", 5), ("high", -1),
                            ("low", 1.5), ("auto", True)):
            with self.subTest(mode=mode, speed=speed):
                with self.assertRaises(ValueError):
                    await self.spa.set_pump("dummy-pump", mode, speed)
        self.assertEqual(self.client.requests, [])


if __name__ == "__main__":
    unittest.main()
