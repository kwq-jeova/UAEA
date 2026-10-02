from __future__ import annotations

import io
import json
import os
import ssl
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from contextlib import closing
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from harness.codex_dynamic_tools import DynamicToolBinding, HarnessDynamicToolAdapter
from memory.sqlite_store import connect, get_web_access_event
from phase2.serpapi_backend import SerpApiFailure, google_search
from phase2.web_adapter import WebAdapter
from phase2.web_capability import WebSearchCapability, web_search_metadata
from runtime.ledger import LedgerStub
from runtime.sandbox import Sandbox
from runtime.tools import ToolRegistry


FAKE_KEY = "test-only-google-acquisition-credential"


def serp_payload():
    return {
        "search_metadata": {"status": "Success", "id": "fixture-search"},
        "search_parameters": {"engine": "google", "q": "LoRA training", "api_key": FAKE_KEY},
        "organic_results": [
            {"title": "LoRA training paper", "link": "https://arxiv.org/abs/example", "snippet": "LoRA training research"},
            {"title": "LoRA training source", "link": "https://github.com/example/lora", "snippet": "LoRA training code"},
        ],
    }


class GoogleSerpApiBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.adapter = WebAdapter(snapshot_root=self.root / "snapshots")
        self.capability = WebSearchCapability(db_path=self.root / "source.sqlite", adapter=self.adapter)
        self.key_patch = patch.dict(os.environ, {"SERPAPI_KEY": FAKE_KEY})
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)

    def call(self, payload=None, arguments=None):
        payload = serp_payload() if payload is None else payload
        with patch("phase2.serpapi_backend.urllib.request.build_opener") as opener, \
                patch.object(self.adapter, "_http_get") as legacy_request:
            opener.return_value.open.return_value = io.BytesIO(json.dumps(payload).encode())
            result = self.capability(arguments or {"query": "LoRA training", "provider": "google", "allow_fallback": False}, "probe")
            self.assertFalse(legacy_request.called)
            self.request = opener.return_value.open.call_args.args[0]
        with closing(connect(self.root / "source.sqlite")) as connection:
            self.event = get_web_access_event(connection, result.data["access_event_id"])
        return result

    def assert_no_secret(self, result):
        self.assertNotIn(FAKE_KEY, json.dumps(result.data))
        self.assertNotIn(FAKE_KEY, json.dumps(self.event))
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(FAKE_KEY.encode(), path.read_bytes(), path.name)

    def test_google_result_uses_existing_normalization_and_evidence_pipeline(self):
        result = self.call()
        self.assertTrue(result.ok)
        self.assertEqual(result.data["status"], "success")
        self.assertEqual(result.data["requested_provider"], "google")
        self.assertEqual(result.data["actual_provider"], "google")
        self.assertEqual(result.data["acquisition_backend"], "serpapi")
        self.assertEqual(result.data["search_provider"], "www.google.com")
        self.assertFalse(result.data["fallback_occurred"])
        self.assertEqual(len(result.data["citable_results"]), 2)
        self.assertEqual(result.data["evidence_status"], "relevant")
        self.assertEqual(self.event["metadata"]["acquisition_endpoint"], "https://serpapi.com/search.json")
        self.assertEqual(urllib.parse.urlsplit(self.event["url"]).hostname, "www.google.com")
        self.assertNotIn("api_key", self.event["url"])
        self.assert_no_secret(result)

    def test_request_key_is_only_in_transport_and_constraints_are_retained(self):
        result = self.call(arguments={"query": "LoRA training", "provider": "google", "allow_fallback": False,
                                      "language": "en", "region": "us", "exclude_domains": ["arxiv.org"],
                                      "preferred_domains": ["github.com"], "source_types": ["forum"], "max_results": 1})
        parameters = urllib.parse.parse_qs(urllib.parse.urlsplit(self.request.full_url).query)
        self.assertEqual(parameters["engine"], ["google"])
        self.assertEqual(parameters["api_key"], [FAKE_KEY])
        self.assertEqual(parameters["hl"], ["en"])
        self.assertEqual(parameters["lr"], ["lang_en"])
        self.assertEqual(parameters["gl"], ["us"])
        self.assertIn("-site:arxiv.org", parameters["q"][0])
        self.assertEqual(result.data["raw_search_result_count"], 2)
        self.assertEqual(result.data["search_results"][0]["url"], "https://github.com/example/lora")
        self.assertEqual(result.data["requested_constraints"]["provider"], "google")
        self.assert_no_secret(result)

    def test_missing_credential_does_not_request_or_fallback(self):
        with patch.dict(os.environ, {"SERPAPI_KEY": ""}), patch("urllib.request.build_opener") as opener, \
                patch.object(self.adapter, "_http_get") as legacy_request:
            result = self.capability({"query": "LoRA training", "provider": "google", "allow_fallback": False}, "strict")
        opener.assert_not_called()
        legacy_request.assert_not_called()
        self.assertEqual(result.data["reason"], "credential_missing")
        self.assertFalse(result.data["http_attempted"])
        self.assertIsNone(result.data["actual_provider"])
        self.assertFalse(result.data["fallback_occurred"])

    def test_strict_transport_failures_are_safe_and_skip_evidence(self):
        failures = (
            (urllib.error.HTTPError("https://serpapi.com/?api_key=" + FAKE_KEY, 401, FAKE_KEY, {}, None), "authentication_failure"),
            (urllib.error.HTTPError("https://serpapi.com", 429, FAKE_KEY, {}, None), "rate_limited"),
            (urllib.error.HTTPError("https://serpapi.com", 503, FAKE_KEY, {}, None), "http_failure"),
            (urllib.error.URLError(FAKE_KEY), "network_failure"),
            (urllib.error.URLError(TimeoutError(FAKE_KEY)), "timeout"),
        )
        for error, status in failures:
            with self.subTest(status=status), patch("urllib.request.build_opener") as opener, \
                    patch.object(self.adapter, "_http_get") as legacy_request, \
                    patch("phase2.web_adapter._assess_search_relevance") as relevance:
                opener.return_value.open.side_effect = error
                result = self.capability({"query": "LoRA training", "provider": "google", "allow_fallback": False}, "strict")
                self.assertFalse(result.ok)
                self.assertEqual(result.data["status"], status)
                self.assertIsNone(result.data["actual_provider"])
                self.assertFalse(result.data["fallback_occurred"])
                self.assertTrue(result.data["http_attempted"])
                self.assertFalse(result.data["evidence_evaluation"]["performed"])
                self.assertNotIn("low_relevance", json.dumps(result.data))
                self.assertNotIn("revise_query", json.dumps(result.data))
                legacy_request.assert_not_called()
                relevance.assert_not_called()
                self.assertNotIn(FAKE_KEY, json.dumps(result.data) + result.message)

    def test_malformed_or_wrong_engine_response_is_not_google_success(self):
        for payload in ({}, {"error": FAKE_KEY}, {"search_metadata": {"status": "Success"},
                        "search_parameters": {"engine": "bing"}}, {"search_metadata": {"status": "Processing"}}):
            with self.subTest(payload_type=list(payload)):
                result = self.call(payload)
                self.assertFalse(result.ok)
                self.assertIsNone(result.data["actual_provider"])
                self.assertFalse(result.data["evidence_evaluation"]["performed"])
                self.assert_no_secret(result)

    def test_invalid_json_and_oversize_response_fail_closed(self):
        for body in (FAKE_KEY.encode(), b"x" * (self.adapter.max_snapshot_bytes + 1)):
            with patch("urllib.request.build_opener") as opener, patch.object(self.adapter, "_http_get") as legacy_request:
                opener.return_value.open.return_value = io.BytesIO(body)
                result = self.capability({"query": "LoRA training", "provider": "google", "allow_fallback": False}, "strict")
                self.assertFalse(result.ok)
                self.assertEqual(result.data["status"], "response_error")
                self.assertNotIn(FAKE_KEY, json.dumps(result.data))
                legacy_request.assert_not_called()

    def test_empty_google_results_are_execution_success_without_evidence(self):
        payload = serp_payload()
        payload["organic_results"] = []
        result = self.call(payload)
        self.assertTrue(result.ok)
        self.assertEqual(result.data["actual_provider"], "google")
        self.assertFalse(result.data["evidence_evaluation"]["performed"])
        self.assertEqual(result.data["citable_results"], [])
        self.assertFalse(result.data["fallback_occurred"])

    def test_only_organic_http_results_are_normalized(self):
        payload = serp_payload()
        payload["ads"] = [{"title": "advertisement", "link": "https://ads.example"}]
        payload["organic_results"] += [payload["organic_results"][0], {"title": "bad", "link": "javascript:alert(1)"},
                                      {"title": "bad", "link": "https://[invalid"}, {"link": "https://example.org"}, None]
        result = self.call(payload)
        self.assertEqual(result.data["raw_search_result_count"], 2)
        self.assertEqual(len(result.data["search_results"]), 2)

    def test_success_snapshot_redacts_echoed_credentials(self):
        payload = serp_payload()
        payload["debug"] = {FAKE_KEY: {"Authorization": FAKE_KEY}, "url": "https://serpapi.com/?api_key=" + FAKE_KEY}
        payload["organic_results"][0]["snippet"] += " " + FAKE_KEY
        result = self.call(payload)
        self.assert_no_secret(result)

    def test_google_missing_fallback_policy_is_rejected_before_backend(self):
        with patch("urllib.request.build_opener") as opener:
            result = self.capability({"query": "LoRA training", "provider": "google"}, "ambiguous")
        opener.assert_not_called()
        self.assertEqual(result.data["semantic_status"], "ambiguous_provider_fallback_policy")

    def test_model_projection_and_adapter_trace_keep_provider_and_backend_distinct(self):
        registry = ToolRegistry(Sandbox(self.root, self.root / "sandbox"), LedgerStub(self.root / "traces"))
        registry.register_capability(web_search_metadata(), self.capability)
        adapter = HarnessDynamicToolAdapter(registry, [DynamicToolBinding.from_registry(
            registry, "web.search", description="Search", input_schema={"type": "object"},
        )])
        with patch("urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = io.BytesIO(json.dumps(serp_payload()).encode())
            dispatch = adapter.dispatch({"threadId": "thread", "turnId": "turn", "callId": "call", "tool": "web_search",
                                         "arguments": {"query": "LoRA training", "provider": "google", "allow_fallback": False}})
        payload = json.loads(dispatch.to_app_server_response()["contentItems"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["actual_provider"], "google")
        self.assertEqual(payload["data"]["acquisition_backend"], "serpapi")
        self.assertNotIn("network_diagnostics", payload["data"])
        self.assertIn("network_diagnostics", json.dumps(dispatch.to_trace_metadata()))
        traces = list((self.root / "traces").glob("*.jsonl"))
        self.assertTrue(traces)
        self.assertTrue(any("network_diagnostics" in path.read_text() for path in traces))
        self.assertNotIn(FAKE_KEY, json.dumps(dispatch.to_trace_metadata()))
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(FAKE_KEY.encode(), path.read_bytes(), path.name)

    def test_provider_unspecified_does_not_use_serpapi(self):
        with patch("urllib.request.build_opener") as opener, patch.object(self.adapter, "_http_get", return_value={
            "status": 200, "body": b"<html>No results</html>", "content_type": "text/html",
        }) as legacy_request:
            result = self.capability({"query": "LoRA training"}, "default")
        opener.assert_not_called()
        self.assertTrue(legacy_request.called)
        self.assertTrue(result.ok)

    def test_redirect_does_not_forward_credentials(self):
        from phase2.serpapi_backend import _NoRedirect
        handler = _NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "redirect", {}, "https://other.example"))

    def test_diagnostics_survive_capability_source_history_and_internal_observation(self):
        result = self.call()
        diagnostics = result.data["network_diagnostics"]
        self.assertEqual(diagnostics, self.event["metadata"]["network_diagnostics"])
        self.assertEqual(diagnostics["stage"], "body_read_completed")
        self.assertEqual(diagnostics["events"][0]["timeout_seconds"], 20)
        self.assertGreater(diagnostics["response_bytes"], 0)
        self.assert_no_secret(result)

    def test_strict_ssl_and_read_timeout_artifacts_identify_stage_without_retry(self):
        for stage, error, expected in [
            ("open", urllib.error.URLError(ssl.SSLError(FAKE_KEY)), "ssl_error"),
            ("body_read", TimeoutError(FAKE_KEY), "response_read_timeout"),
        ]:
            with self.subTest(stage=stage), patch("urllib.request.build_opener") as opener, \
                    patch.object(self.adapter, "_http_get") as legacy_request:
                if stage == "open":
                    opener.return_value.open.side_effect = error
                else:
                    response = opener.return_value.open.return_value.__enter__.return_value
                    response.status = 200
                    response.read.side_effect = error
                result = self.capability({"query": "LoRA training", "provider": "google", "allow_fallback": False}, "diagnostic")
                opener.return_value.open.assert_called_once()
                self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 20)
                legacy_request.assert_not_called()
                self.assertIsNone(result.data["actual_provider"])
                self.assertFalse(result.data["fallback_occurred"])
                diagnostics = result.data["network_diagnostics"]
                self.assertEqual(diagnostics["network_error_stage"], stage)
                self.assertEqual(diagnostics["error_kind"], expected)
                with closing(connect(self.root / "source.sqlite")) as connection:
                    event = get_web_access_event(connection, result.data["access_event_id"])
                self.assertEqual(event["metadata"]["network_diagnostics"], diagnostics)
                self.assertNotIn(FAKE_KEY, json.dumps(result.data) + json.dumps(event))

    def test_native_urllib_fetch_failure_preserves_network_diagnostics(self):
        from phase2.web_capability import WebFetchCapability
        capability = WebFetchCapability(db_path=self.root / "source.sqlite", adapter=self.adapter)
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError(ssl.SSLError("fixture SSL EOF"))) as request:
            result = capability({"url": "https://example.org/readme"}, "fetch diagnostic")
        request.assert_called_once()
        self.assertEqual(request.call_args.kwargs["timeout"], 20)
        self.assertEqual(result.data["network_diagnostics"]["network_error_stage"], "open")
        self.assertEqual(result.data["network_diagnostics"]["error_kind"], "ssl_error")
        with closing(connect(self.root / "source.sqlite")) as connection:
            event = get_web_access_event(connection, result.data["access_event_id"])
        self.assertEqual(event["metadata"]["network_diagnostics"], result.data["network_diagnostics"])


if __name__ == "__main__":
    unittest.main()
