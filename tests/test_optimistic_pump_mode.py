"""Offline behavioural tests of the actual two-speed coordinator setter.

Extract the method AST and execute it against a small fake coordinator so
no Home Assistant installation, cloud access, or physical spa is required.
"""
from __future__ import annotations

import ast
import copy
import logging
from pathlib import Path
import unittest

COORDINATOR = (Path(__file__).resolve().parents[1] /
               "custom_components/spanet/coordinator.py")


def isolated_pump_method():
    tree = ast.parse(COORDINATOR.read_text(encoding="utf-8"))
    coordinator = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Coordinator"
    )
    method = next(
        n for n in coordinator.body
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "set_pump_mode"
    )
    holder = ast.ClassDef(
        name="IsolatedCoordinator", bases=[], keywords=[],
        body=[copy.deepcopy(method)], decorator_list=[]
    )
    namespace = {"SK_PUMPS": "pumps", "logger": logging.getLogger("test_pump")}
    module = ast.fix_missing_locations(ast.Module(body=[holder], type_ignores=[]))
    exec(compile(module, str(COORDINATOR), "exec"), namespace)
    return namespace["IsolatedCoordinator"]


class FakeSpa:
    def __init__(self):
        self.calls = []

    async def set_pump(self, pump_id, state, pump_variable_speed=0):
        self.calls.append((pump_id, state, pump_variable_speed))


class OptimisticPumpModeTests(unittest.IsolatedAsyncioTestCase):
    def make_coordinator(self, *, auto=True, enabled=True):
        coordinator = isolated_pump_method()()
        coordinator.state = {"pumps": {"1": {
            "apiId": "pump-one", "state": "off", "auto": auto,
        }}}
        coordinator.spa = FakeSpa()
        coordinator.operations = []
        coordinator.notifications = 0
        coordinator.get_state = lambda key: coordinator.state["pumps"]["1"]
        coordinator.is_pump_mode_control_enabled = lambda key, pump: enabled
        coordinator.run_background = lambda coro: coordinator.operations.append(coro)
        coordinator.async_update_listeners = lambda: setattr(
            coordinator, "notifications", coordinator.notifications + 1
        )
        return coordinator

    async def test_immediate_visual_feedback_and_background_api_request(self):
        for mode in ("off", "auto", "low", "high"):
            with self.subTest(mode=mode):
                co = self.make_coordinator()
                await co.set_pump_mode("1", mode)
                self.assertEqual(co.state["pumps"]["1"]["state"], mode)
                self.assertEqual(co.notifications, 1)
                self.assertEqual(len(co.operations), 1)
                self.assertEqual(co.spa.calls, [])
                # Run the captured background coroutine, proving the
                # device-specific SetPump parameter is still 5, never 0.
                await co.operations.pop()
                self.assertEqual(co.spa.calls, [("pump-one", mode, 5)])

    async def test_unverified_pump_rejected_without_any_state_mutation(self):
        co = self.make_coordinator(enabled=False)
        with self.assertRaisesRegex(ValueError, "not enabled"):
            await co.set_pump_mode("1", "high")
        self.assertEqual(co.state["pumps"]["1"]["state"], "off")
        self.assertEqual(co.notifications, 0)
        self.assertEqual(co.operations, [])

    async def test_invalid_mode_rejected_before_background_submit(self):
        co = self.make_coordinator()
        with self.assertRaisesRegex(ValueError, "Unsupported SpaNET pump mode"):
            await co.set_pump_mode("1", "turbo")
        self.assertEqual(co.operations, [])
        self.assertEqual(co.notifications, 0)

    async def test_auto_rejected_if_hardware_does_not_support_it(self):
        co = self.make_coordinator(auto=False)
        with self.assertRaisesRegex(ValueError, "automatic mode"):
            await co.set_pump_mode("1", "auto")
        self.assertEqual(co.operations, [])
        self.assertEqual(co.notifications, 0)


if __name__ == "__main__":
    unittest.main()
