"""Offline guardrails for reconciling SpaNET upstream changes.

These checks do not contact a spa or require the Home Assistant runtime.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "spanet"


def method_source(filename: str, class_name: str, method_name: str) -> str:
    source = (COMPONENT / filename).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for cls in tree.body:
        if isinstance(cls, ast.ClassDef) and cls.name == class_name:
            for func in cls.body:
                if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)) and func.name == method_name:
                    return ast.get_source_segment(source, func) or ""
    raise AssertionError(f"Missing {class_name}.{method_name}")


class UpstreamMergeCompatibilityTests(unittest.TestCase):
    def test_existing_pump_switch_uses_upstream_background_submission(self):
        source = method_source("coordinator.py", "Coordinator", "set_pump")
        self.assertIn('self.run_background(self.spa.set_pump(pump["apiId"], state))', source)
        self.assertIn('self.async_update_listeners()', source)

    def test_two_speed_mode_write_still_awaits_api_before_readback(self):
        source = method_source("coordinator.py", "Coordinator", "set_pump_mode")
        self.assertIn('await self.spa.set_pump(pump["apiId"], mode, 5)', source)
        self.assertIn('self._async_confirm_pump_mode(key, mode)', source)
        self.assertNotIn('pump["state"] = mode', source)

    def test_readback_uses_existing_pump_scheduler_task(self):
        source = method_source("coordinator.py", "Coordinator", "_async_confirm_pump_mode")
        self.assertIn('self.pumps_task.trigger()', source)
        self.assertIn('await self.async_request_refresh()', source)

    def test_background_scheduler_has_valid_annotations_and_name(self):
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("from collections.abc import Coroutine", source)
        self.assertIn("from typing import Any", source)
        self.assertNotIn("Coroutine[Any, Any, _R]", source)
        method = method_source("coordinator.py", "Coordinator", "run_background")
        self.assertIn('getattr(target, "cr_code", None)', method)
        self.assertIn("self.config_entry.async_create_background_task(", method)

    def test_upstream_sleep_timer_payload_retained(self):
        source = method_source("spanet.py", "SpaPool", "set_sleep_timer")
        self.assertIn('"isEnabled": enabled == 1', source)
        self.assertIn('"daysHex": "7F" if enabled else "80"', source)
        self.assertNotIn('"timerNumber"', source)


if __name__ == "__main__":
    unittest.main()
