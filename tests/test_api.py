"""Tests for host validation and API error mapping."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

PACKAGE_PATH = Path(__file__).parents[1] / "custom_components" / "ft0360"


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, PACKAGE_PATH / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


custom_components = types.ModuleType("custom_components")
custom_components.__path__ = []
sys.modules.setdefault("custom_components", custom_components)
package = types.ModuleType("custom_components.ft0360")
package.__path__ = [str(PACKAGE_PATH)]
sys.modules.setdefault("custom_components.ft0360", package)

_load_module("custom_components.ft0360.const", "const.py")
_load_module("custom_components.ft0360.parser", "parser.py")
api = _load_module("custom_components.ft0360.api", "api.py")


class _FakeContent:
    def __init__(self, body):
        self._body = body

    async def read(self, size):
        return self._body[:size]


class _FakeResponse:
    def __init__(self, body=b"{}", content_length=None):
        self.content = _FakeContent(body)
        self.content_length = len(body) if content_length is None else content_length

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self):
        return None


class _TimeoutResponse:
    async def __aenter__(self):
        raise asyncio.TimeoutError

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.last_request = None

    def get(self, url, **kwargs):
        self.last_request = (url, kwargs)
        return self.response


class NormalizeHostTests(unittest.TestCase):
    """Validate accepted and rejected host forms."""

    def test_normalizes_common_hosts(self):
        self.assertEqual(api.normalize_host(" 192.168.1.236 "), "192.168.1.236")
        self.assertEqual(api.normalize_host("http://station.local/"), "station.local")
        self.assertEqual(api.normalize_host("station.local:8080"), "station.local:8080")
        self.assertEqual(api.normalize_host("http://[fd00::1]:8080"), "[fd00::1]:8080")

    def test_rejects_non_host_input(self):
        for invalid in (
            "",
            "https://station.local",
            "http://user:password@station.local",
            "station.local/client",
            "station.local?command=record",
            "bad host",
            "station.local:not-a-port",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                api.normalize_host(invalid)


class ApiErrorTests(unittest.IsolatedAsyncioTestCase):
    """Check API decoding, limits and exception types."""

    async def test_invalid_json_has_specific_error(self):
        session = _FakeSession(_FakeResponse(b"not-json"))
        client = api.FT0360Client("station.local", session)

        with self.assertRaises(api.FT0360InvalidResponseError):
            await client._async_get_json("/test")

        self.assertFalse(session.last_request[1]["allow_redirects"])

    async def test_oversized_response_is_rejected_before_reading(self):
        session = _FakeSession(
            _FakeResponse(b"{}", content_length=1_048_577)
        )
        client = api.FT0360Client("station.local", session)

        with self.assertRaises(api.FT0360InvalidResponseError):
            await client._async_get_json("/test")

    async def test_timeout_is_a_connection_error(self):
        client = api.FT0360Client("station.local", _FakeSession(_TimeoutResponse()))

        with self.assertRaises(api.FT0360CannotConnectError):
            await client._async_get_json("/test")

    async def test_wrong_record_shape_is_an_invalid_response(self):
        session = _FakeSession(_FakeResponse(b'{"status":"ok"}'))
        client = api.FT0360Client("station.local", session)

        with self.assertRaises(api.FT0360InvalidResponseError):
            await client.async_get_record()

    async def test_connection_endpoint_is_parsed(self):
        body = (
            b'{"IPConfig":{"status":5,"rssi":3,"ip":"192.168.1.236",'
            b'"gw":"192.168.1.1","mac":"D4:8A:FC:3A:E1:AC"}}'
        )
        session = _FakeSession(_FakeResponse(body))
        client = api.FT0360Client("station.local", session)

        info = await client.async_get_connection_info()

        self.assertEqual(info.status, "connected")
        self.assertEqual(
            session.last_request[0],
            "http://station.local/config?command=connect_status",
        )

    async def test_firmware_endpoint_is_parsed(self):
        session = _FakeSession(
            _FakeResponse(b'{"Firmware":{"Version":"2.0.0","build":"00026"}}')
        )
        client = api.FT0360Client("station.local", session)

        info = await client.async_get_firmware_info()

        self.assertEqual(info.build, "00026")
        self.assertEqual(
            session.last_request[0],
            "http://station.local/config?command=Firmware",
        )

    async def test_debug_endpoint_is_parsed(self):
        session = _FakeSession(
            _FakeResponse(
                b'{"Model":"esp8266 router","Version":"2.0.0 build-00026",'
                b'"ostime":"2026-09-02 20:30:39","synctime":"0.17.56"}'
            )
        )
        client = api.FT0360Client("station.local", session)

        info = await client.async_get_debug_info()

        self.assertEqual(info.model, "esp8266 router")
        self.assertEqual(info.device_time, "2026-09-02 20:30:39")
        self.assertEqual(
            session.last_request[0],
            "http://station.local/config?command=debug",
        )


if __name__ == "__main__":
    unittest.main()
