"""Offline tests for transient SpaNET authentication/discovery responses."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "spanet"
spec = importlib.util.spec_from_file_location("spanet_auth_retry_test", COMPONENT / "spanet.py")
assert spec is not None and spec.loader is not None
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class FakeClient:
    def __init__(self, *, login_status=None, devices_status=None):
        self.login_status = login_status
        self.devices_status = devices_status

    async def post(self, *args, **kwargs):
        if self.login_status is not None:
            raise api.SpaNetApiError(SimpleNamespace(status=self.login_status), "")
        return {"access_token": "fixture-token", "refresh_token": "fixture-refresh"}

    async def get(self, *args, **kwargs):
        if self.devices_status is not None:
            raise api.SpaNetApiError(SimpleNamespace(status=self.devices_status), "")
        return {"devices": []}


class AuthRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_http202_propagates_for_setup_retry(self):
        client = FakeClient(login_status=202)
        with patch.object(api, "HttpClient", return_value=client):
            with self.assertRaises(api.SpaNetApiError) as ctx:
                await api.SpaNet(object()).authenticate("fixture", "fixture", "device")
        self.assertEqual(ctx.exception.response.status, 202)

    async def test_login_http503_propagates_for_setup_retry(self):
        client = FakeClient(login_status=503)
        with patch.object(api, "HttpClient", return_value=client):
            with self.assertRaises(api.SpaNetApiError) as ctx:
                await api.SpaNet(object()).authenticate("fixture", "fixture", "device")
        self.assertEqual(ctx.exception.response.status, 503)

    async def test_http401_stays_auth_failure(self):
        client = FakeClient(login_status=401)
        with patch.object(api, "HttpClient", return_value=client):
            with self.assertRaises(api.SpaNetAuthFailed):
                await api.SpaNet(object()).authenticate("fixture", "fixture", "device")

    async def test_device_discovery_http202_propagates(self):
        client = FakeClient(devices_status=202)
        with (
            patch.object(api, "HttpClient", return_value=client),
            patch.object(api, "TokenSource", return_value=object()),
        ):
            with self.assertRaises(api.SpaNetApiError) as ctx:
                await api.SpaNet(object()).authenticate("fixture", "fixture", "device")
        self.assertEqual(ctx.exception.response.status, 202)

    def test_init_wires_transient_cloud_error_to_ha_retry(self):
        source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("except SpaNetApiError as exc:", source)
        self.assertIn("raise ConfigEntryNotReady(", source)


if __name__ == "__main__":
    unittest.main()
