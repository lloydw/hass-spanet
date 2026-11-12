"""Offline behaviour tests for optimistic PUT followed by bounded 5s GET.

Runs the real coordinator methods in isolation, never contacts Home Assistant
or the physical spa.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import importlib.util
import logging
from collections.abc import Coroutine
from pathlib import Path
from typing import Any
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "spanet"
COORDINATOR = COMPONENT / "coordinator.py"

spec = importlib.util.spec_from_file_location("spanet_readback_offline", COMPONENT / "pump_readback.py")
assert spec and spec.loader
readback = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readback)


async def fast_readback(expected, current, refresh):
    # Keep real validation/exception semantics but avoid 5+15 seconds in tests.
    async def no_wait(seconds):
        return None

    return await readback.readback_until_confirmed(
        expected, current, refresh, sleep=no_wait
    )


def isolated_coordinator():
    tree = ast.parse(COORDINATOR.read_text(encoding="utf-8"))
    coordinator = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Coordinator")
    names = ("set_pump", "set_pump_mode", "_async_set_and_verify_pump_mode", "update_pumps", "run_background")
    methods = [
        copy.deepcopy(next(
            n for n in coordinator.body
            if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == name
        )) for name in names
    ]
    holder = ast.ClassDef(
        name="IsolatedCoordinator", bases=[], keywords=[],
        body=methods, decorator_list=[]
    )
    namespace = {
        "SK_PUMPS": "pumps", "SK_BLOWER": "blower",
        "BLOWER_STATUS_OFF": "off",
        "logger": logging.getLogger("test_pump"),
        "Coroutine": Coroutine, "Any": Any, "asyncio": asyncio,
        "normalize_pump_mode": lambda value: value if value in {"off","low","high","auto","on"} else None,
        "readback_until_confirmed": fast_readback,
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=[holder], type_ignores=[])),
                 str(COORDINATOR), "exec"), namespace)
    return namespace["IsolatedCoordinator"]


class FakeSpa:
    def __init__(self):
        self.calls = []
        self.actual = "off"
        self.fail_put = False
        self.apply_put = True
        self.fail_get_count = 0
        self.omit_pump = False
        self.get_calls = 0

    async def set_pump(self, pump_id, mode, pump_variable_speed=0):
        self.calls.append((pump_id, mode, pump_variable_speed))
        if self.fail_put:
            raise RuntimeError("cloud refused command")
        if self.apply_put:
            self.actual = mode

    async def get_pumps(self):
        self.get_calls += 1
        if self.fail_get_count:
            self.fail_get_count -= 1
            raise RuntimeError("API Error 202")
        pumps = [] if self.omit_pump else [{
            "pumpNumber": 1, "id": "pump-one", "hasAuto": True,
            "pumpSpeed": 2, "canSwitchOn": True,
            "pumpVariableSpeed": 5, "pumpStatus": self.actual,
        }]
        return {"pumpAndBlower": {"pumps": pumps, "blower": None}}


class OptimisticPumpModeTests(unittest.IsolatedAsyncioTestCase):
    def make_coordinator(self, *, auto=True, enabled=True, speeds=2):
        co = isolated_coordinator()()
        co.state = {"pumps": {"1": {
            "apiId": "pump-one", "state": "off", "auto": auto, "speeds": speeds,
        }}}
        co._pump_mode_versions = {}
        co.spa = FakeSpa()
        co.operations = []
        co.notifications = 0

        def get_state(path):
            data = co.state
            for key in path.split("."):
                data = data[key]
            return data

        co.get_state = get_state
        co.is_pump_mode_control_enabled = lambda key, pump: enabled
        co.run_background = lambda coro: co.operations.append(coro)
        co.async_update_listeners = lambda: setattr(
            co, "notifications", co.notifications + 1
        )
        return co

    async def test_legacy_on_two_speed_maps_to_auto_and_verifies(self):
        co = self.make_coordinator()
        await co.set_pump("1", "on")
        self.assertEqual(co.state["pumps"]["1"]["state"], "auto")
        self.assertEqual(co.notifications, 1)
        self.assertEqual(len(co.operations), 1)
        await co.operations.pop()
        self.assertEqual(co.spa.calls, [("pump-one", "auto", 5)])
        self.assertEqual(co.spa.get_calls, 1)
        self.assertEqual(co.state["pumps"]["1"]["state"], "auto")

    async def test_legacy_off_two_speed_uses_verified_mode_path(self):
        co = self.make_coordinator()
        await co.set_pump("1", "off")
        self.assertEqual(co.state["pumps"]["1"]["state"], "off")
        await co.operations.pop()
        self.assertEqual(co.spa.calls, [("pump-one", "off", 5)])
        self.assertEqual(co.spa.get_calls, 1)

    async def test_original_single_speed_on_off_payload_unchanged(self):
        for state in ("on", "off"):
            with self.subTest(state=state):
                co = self.make_coordinator(speeds=1)
                await co.set_pump("1", state)
                self.assertEqual(co.state["pumps"]["1"]["state"], state)
                self.assertEqual(co.notifications, 1)
                self.assertEqual(len(co.operations), 1)
                await co.operations.pop()
                self.assertEqual(co.spa.calls, [("pump-one", state, 0)])
                self.assertEqual(co.spa.get_calls, 0)

    async def test_manual_single_speed_choice_retains_legacy_switch(self):
        co = self.make_coordinator(speeds=2, enabled=False)
        await co.set_pump("1", "on")
        self.assertEqual(co.state["pumps"]["1"]["state"], "on")
        await co.operations.pop()
        self.assertEqual(co.spa.calls, [("pump-one", "on", 0)])
        self.assertEqual(co.spa.get_calls, 0)

    async def test_no_auto_does_not_assume_high_on_two_speed_pump(self):
        co = self.make_coordinator(speeds=2, auto=False)
        await co.set_pump("1", "on")
        await co.operations.pop()
        self.assertEqual(co.spa.calls, [("pump-one", "on", 0)])
        self.assertEqual(co.spa.get_calls, 0)

    async def test_immediate_state_then_five_second_verification_for_all_modes(self):
        for mode in ("off", "auto", "low", "high"):
            with self.subTest(mode=mode):
                co = self.make_coordinator()
                await co.set_pump_mode("1", mode)
                self.assertEqual(co.state["pumps"]["1"]["state"], mode)
                self.assertEqual(co.notifications, 1)
                self.assertEqual(len(co.operations), 1)
                self.assertEqual(co.spa.calls, [])
                self.assertEqual(co.spa.get_calls, 0)

                await co.operations.pop()
                self.assertEqual(co.spa.calls, [("pump-one", mode, 5)])
                self.assertEqual(co.spa.get_calls, 1)
                self.assertEqual(co.state["pumps"]["1"]["state"], mode)
                self.assertEqual(co.notifications, 2)

    async def test_successful_put_but_unapplied_command_get_corrects_ui(self):
        co = self.make_coordinator()
        co.spa.apply_put = False
        await co.set_pump_mode("1", "high")
        self.assertEqual(co.state["pumps"]["1"]["state"], "high")
        await co.operations.pop()
        self.assertEqual(co.spa.calls, [("pump-one", "high", 5)])
        self.assertEqual(co.spa.get_calls, 2)
        self.assertEqual(co.state["pumps"]["1"]["state"], "off")

    async def test_transient_get_202_is_retried_with_fresh_snapshot(self):
        co = self.make_coordinator()
        co.spa.fail_get_count = 1
        await co.set_pump_mode("1", "low")
        await co.operations.pop()
        self.assertEqual(co.spa.get_calls, 2)
        self.assertEqual(co.state["pumps"]["1"]["state"], "low")

    async def test_missing_pump_in_get_cannot_confirm_cached_optimistic_mode(self):
        co = self.make_coordinator()
        co.spa.omit_pump = True
        await co.set_pump_mode("1", "low")
        await co.operations.pop()
        self.assertEqual(co.spa.get_calls, 2)
        # The request remains optimistic only because no authoritative
        # status exists; it is NOT falsely logged as confirmed.
        self.assertEqual(co.state["pumps"]["1"]["state"], "low")
        self.assertEqual(co.notifications, 1)

    async def test_newer_command_supersedes_earlier_confirmation(self):
        co = self.make_coordinator()
        await co.set_pump_mode("1", "low")
        await co.set_pump_mode("1", "high")
        self.assertEqual(co.state["pumps"]["1"]["state"], "high")
        first, second = co.operations
        await first
        self.assertEqual(co.spa.get_calls, 0)
        await second
        self.assertEqual(co.state["pumps"]["1"]["state"], "high")
        self.assertEqual(co.spa.get_calls, 1)

    async def test_failed_put_still_propagates_to_upstream_background_error_handler(self):
        co = self.make_coordinator()
        co.spa.fail_put = True
        await co.set_pump_mode("1", "high")
        with self.assertRaisesRegex(RuntimeError, "cloud refused"):
            await co.operations.pop()
        self.assertEqual(co.spa.get_calls, 0)

    async def test_rejected_background_command_forces_cloud_state_refresh(self):
        co = self.make_coordinator()
        del co.run_background
        events = []

        class ConfigEntry:
            def __init__(self):
                self.tasks = []

            def async_create_background_task(self, hass, coro, name, *, eager_start):
                events.append(("background", name, eager_start))
                self.tasks.append(coro)

        co.hass = object()
        co.config_entry = ConfigEntry()
        co.queue_refresh = lambda: events.append("queue_refresh")

        async def refresh():
            events.append("request_refresh")
            co.state["pumps"]["1"]["state"] = "off"

        co.async_request_refresh = refresh
        co.spa.fail_put = True

        await co.set_pump_mode("1", "high")
        self.assertEqual(co.state["pumps"]["1"]["state"], "high")
        self.assertEqual(co.notifications, 1)
        self.assertEqual(len(co.config_entry.tasks), 1)
        with self.assertRaisesRegex(RuntimeError, "cloud refused"):
            await co.config_entry.tasks[0]
        self.assertEqual(co.state["pumps"]["1"]["state"], "off")
        self.assertEqual(events[-2:], ["queue_refresh", "request_refresh"])

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
