from __future__ import annotations

import io
import json
import os
import ssl
import unittest
import urllib.error
from contextvars import Context
from unittest.mock import Mock, patch

from phase2.network_observability import NetworkObservation, observe_open, observe_read


KEY = "fixture-private-network-credential"


class Response(io.BytesIO):
    status = 200


class NetworkObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"SERPAPI_KEY": KEY})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.proxy = patch("urllib.request.getproxies", return_value={
            "https": f"http://user:{KEY}@127.0.0.1:7897/private?key={KEY}",
        })
        self.proxy.start()
        self.addCleanup(self.proxy.stop)
        self.bypass = patch("urllib.request.proxy_bypass", return_value=False)
        self.bypass.start()
        self.addCleanup(self.bypass.stop)

    def test_success_preserves_call_and_read_boundaries(self):
        request = object()
        response = Response(b"example")
        open_request = Mock(return_value=response)
        observation = NetworkObservation("https://serpapi.com/search.json?api_key=" + KEY)
        with observation:
            self.assertIs(observe_open(open_request, request, timeout=20), response)
            self.assertEqual(observe_read(response, 4), b"exam")
        open_request.assert_called_once_with(request, timeout=20)
        data = observation.data
        self.assertEqual([event["stage"] for event in data["events"]],
                         ["open", "response_headers", "body_read", "body_read_completed"])
        self.assertEqual(data["http_status"], 200)
        self.assertEqual(data["response_bytes"], 4)
        self.assertTrue(data["credential_present"])
        self.assertTrue(data["proxy_present"])
        self.assertFalse(data["proxy_bypassed"])
        self.assertEqual(data["proxy_endpoint_redacted"], "http://127.0.0.1:7897")
        self.assertNotIn(KEY, json.dumps(data))
        self.assertNotIn("api_key", json.dumps(data))
        self.assertEqual(data["network_error_stage"], None)
        elapsed = [event["elapsed_ms"] for event in data["events"]]
        self.assertEqual(elapsed, sorted(elapsed))

    def test_open_failures_are_classified_without_messages_or_retry(self):
        cases = [
            (TimeoutError(KEY), "connection_open_timeout"),
            (urllib.error.URLError(TimeoutError(KEY)), "connection_open_timeout"),
            (urllib.error.URLError(ssl.SSLError(KEY)), "ssl_error"),
            (ssl.SSLError(KEY), "ssl_error"),
            (urllib.error.URLError(OSError("Tunnel connection failed: 407 " + KEY)), "proxy_error"),
            (urllib.error.HTTPError("https://serpapi.com/?api_key=" + KEY, 407, KEY, {}, None), "proxy_error"),
            (urllib.error.HTTPError("https://serpapi.com/?api_key=" + KEY, 503, KEY, {}, None), "http_error"),
            (urllib.error.URLError(KEY), "network_error"),
        ]
        for error, kind in cases:
            with self.subTest(kind=kind):
                observation = NetworkObservation("https://serpapi.com/search.json")
                opener = Mock(side_effect=error)
                with self.assertRaises(type(error)) as raised:
                    with observation:
                        observe_open(opener, object(), timeout=20)
                self.assertIs(raised.exception, error)
                self.assertEqual(opener.call_count, 1)
                self.assertEqual(observation.data["network_error_stage"], "open")
                self.assertEqual(observation.data["error_kind"], kind)
                self.assertEqual(observation.data["exception_type"], type(error).__name__)
                self.assertNotIn(KEY, json.dumps(observation.data))
                self.assertNotIn("api_key", json.dumps(observation.data))
                if isinstance(error, urllib.error.HTTPError):
                    self.assertEqual(observation.data["http_status"], error.code)

    def test_body_failure_is_not_reported_as_open_failure(self):
        for error, kind in [(TimeoutError(KEY), "response_read_timeout"), (ssl.SSLError(KEY), "ssl_error")]:
            with self.subTest(kind=kind):
                response = Mock(status=200)
                response.read.side_effect = error
                opener = Mock(return_value=response)
                observation = NetworkObservation("https://serpapi.com/search.json")
                with self.assertRaises(type(error)) as raised:
                    with observation:
                        observe_open(opener, object(), timeout=20)
                        observe_read(response, 2000001)
                self.assertIs(raised.exception, error)
                opener.assert_called_once()
                response.read.assert_called_once_with(2000001)
                self.assertEqual(observation.data["http_status"], 200)
                self.assertEqual(observation.data["network_error_stage"], "body_read")
                self.assertEqual(observation.data["error_kind"], kind)
                self.assertIsNone(observation.data["response_bytes"])
                self.assertNotIn(KEY, json.dumps(observation.data))

    def test_missing_proxy_and_credential_are_explicit(self):
        with patch.dict(os.environ, {"SERPAPI_KEY": ""}), patch("urllib.request.getproxies", return_value={}):
            observation = NetworkObservation("https://serpapi.com/search.json")
        self.assertFalse(observation.data["credential_present"])
        self.assertFalse(observation.data["proxy_present"])
        self.assertIsNone(observation.data["proxy_endpoint_redacted"])
        self.assertEqual(observation.data["stage"], "not_opened")

    def test_context_is_nested_isolated_and_reset_after_error(self):
        outer = NetworkObservation("https://serpapi.com/search.json")
        inner = NetworkObservation("https://example.org")
        with outer:
            with inner:
                observe_open(Mock(return_value=Response()), object(), timeout=20)
            Context().run(observe_open, Mock(return_value=Response()), object(), timeout=20)
            with self.assertRaises(TimeoutError):
                with NetworkObservation("https://example.org"):
                    observe_open(Mock(side_effect=TimeoutError()), object(), timeout=20)
            observe_open(Mock(return_value=Response()), object(), timeout=20)
        counts = (len(outer.data["events"]), len(inner.data["events"]))
        observe_open(Mock(return_value=Response()), object(), timeout=20)
        self.assertEqual(counts, (2, 2))
        self.assertEqual(len(outer.data["events"]), counts[0])


if __name__ == "__main__":
    unittest.main()
