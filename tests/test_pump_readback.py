"""Offline tests for bounded SpaNET post-command readback.

These tests never load Home Assistant or contact the spa.
"""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "spanet"
spec = importlib.util.spec_from_file_location(
    "spanet_pump_readback_test", COMPONENT / "pump_readback.py"
)
assert spec is not None and spec.loader is not None
readback = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readback)


class PumpReadbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_confirmed_first_attempt(self):
        state = "off"
        calls = []
        sleeps = []

        async def sleep(seconds):
            sleeps.append(seconds)

        async def refresh():
            nonlocal state
            calls.append("GET")
            state = "low"

        self.assertTrue(await readback.readback_until_confirmed(
            "low", lambda: state, refresh, sleep=sleep
        ))
        self.assertEqual(calls, ["GET"])
        self.assertEqual(sleeps, [7])

    async def test_eventual_consistency_uses_only_one_retry(self):
        state = "off"
        calls = []
        sleeps = []

        async def sleep(seconds):
            sleeps.append(seconds)

        async def refresh():
            nonlocal state
            calls.append("GET")
            if len(calls) == 2:
                state = "high"

        self.assertTrue(await readback.readback_until_confirmed(
            "high", lambda: state, refresh, sleep=sleep
        ))
        self.assertEqual(calls, ["GET", "GET"])
        self.assertEqual(sleeps, [7, 15])

    async def test_stale_api_never_fakes_new_mode(self):
        calls = []

        async def sleep(seconds):
            pass

        async def refresh():
            calls.append("GET")

        self.assertFalse(await readback.readback_until_confirmed(
            "low", lambda: "off", refresh, sleep=sleep
        ))
        self.assertEqual(len(calls), 2)

    async def test_transient_api_error_uses_bounded_retry(self):
        calls = []

        async def sleep(seconds):
            pass

        async def refresh():
            calls.append("GET")
            if len(calls) == 1:
                raise RuntimeError("transient API error")

        self.assertTrue(await readback.readback_until_confirmed(
            "auto", lambda: "auto", refresh, sleep=sleep
        ))
        self.assertEqual(len(calls), 2)

    async def test_two_api_errors_stop_after_two_attempts(self):
        calls = []

        async def sleep(seconds):
            pass

        async def refresh():
            calls.append("GET")
            raise RuntimeError("API Error 202")

        self.assertFalse(await readback.readback_until_confirmed(
            "auto", lambda: "off", refresh, sleep=sleep
        ))
        self.assertEqual(len(calls), 2)

    async def test_cancellation_propagates_without_polling(self):
        sleeping = asyncio.Event()
        calls = []

        async def sleep(seconds):
            sleeping.set()
            await asyncio.Event().wait()

        async def refresh():
            calls.append("GET")

        task = asyncio.create_task(readback.readback_until_confirmed(
            "low", lambda: "off", refresh, sleep=sleep
        ))
        await sleeping.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(calls, [])

    def test_legacy_readback_helper_is_dormant_during_hardware_trials(self):
        # Keep the offline-tested helper on this trial branch as a rollback
        # reference; do not schedule it from the new optimistic command path.
        coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn("self.pumps_task = self.scheduler.add_task(300, self.update_pumps)", coordinator)
        self.assertIn('self.run_background(self.spa.set_pump(pump["apiId"], mode, 5))', coordinator)
        self.assertNotIn("readback_until_confirmed", coordinator)
        self.assertNotIn("_async_confirm_pump_mode", coordinator)



if __name__ == "__main__":
    unittest.main()
