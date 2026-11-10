"""Offline boundary tests: real Registry/Source store, fixture transport, no model."""
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import memory.sqlite_store  # Resolve the shared Source package before Phase-1 path setup.
from tests.test_contract_convergence import setup_host
from harness.codex_dynamic_tools import DynamicToolBinding, HarnessDynamicToolAdapter
from harness.io_contract import turn_context_payload
from harness.provider_history import project_provider_history
from harness.recovery_observation import recovery_observation
from harness.responses_bridge import ProviderHistoryBridge
from harness.request_audit import redact
from phase2.evidence_boundary import temporal_facts
from phase2.web_adapter import WebAdapter
from phase2.web_capability import WebFetchCapability, web_fetch_metadata


class ProviderTimeErrorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.adapter, self.semantic, self.seen = setup_host(self.root)
        self.web = WebAdapter(snapshot_root=self.root / "snapshots")
        self.fetch = WebFetchCapability(db_path=self.root / "source.sqlite", adapter=self.web)
        self.adapter.registry.register_capability(web_fetch_metadata(), self.fetch)
        bindings = list(self.adapter.bindings) + [DynamicToolBinding.from_registry(
            self.adapter.registry, "web.fetch", description="fetch", input_schema={"type": "object"})]
        self.adapter = HarnessDynamicToolAdapter(
            self.adapter.registry, bindings, execution_boundary=self.adapter.execution_boundary)
        self.adapter.bind_semantic_state_adapter(self.semantic)
        self.semantic.prepare_turn("thread", "只用 Google，不允许降级；按指定历史日期核查", turn_id="t1")

    def dispatch(self, tool, args, call="a"):
        return self.adapter.dispatch({"threadId": "thread", "turnId": "t1",
                                      "callId": call, "tool": tool, "arguments": args})

    def wire(self, dispatch):
        return json.loads(dispatch.to_app_server_response()["contentItems"][0]["text"])

    def test_fallback_denial_is_local_with_known_provider_and_legal_new_attempt(self):
        proposal = {"query": "topic B", "provider": "google", "allow_fallback": True}
        rejected = self.dispatch("web_search", proposal, "denied")
        self.assertEqual(rejected.execution_decision["reason"], "authorization_unknown")
        self.assertEqual(rejected.action_request.parameters, proposal)
        data = self.wire(rejected)["data"]
        recovery = data["recovery"]
        self.assertTrue(recovery["constraints_known"])
        self.assertIn("web.provider=google", recovery["active_constraints"])
        self.assertEqual(recovery["authorization"]["state"], "unknown")
        self.assertEqual(recovery["failure_scope"], "web.provider_fallback")
        self.assertIn("Only the provider-fallback", self.wire(rejected)["message"])
        retry = recovery["legal_next_steps"][0]
        self.assertEqual(retry["argument_updates"], {"provider": "google", "allow_fallback": False})
        self.assertTrue(retry["requires_current_policy_validation"])
        self.assertEqual(self.seen, [])
        accepted = self.dispatch("web_search", {**proposal, **retry["argument_updates"]}, "retry")
        self.assertTrue(accepted.ok)
        self.assertEqual(len(self.seen), 1)
        self.assertEqual(rejected.execution_decision["authorization"]["provider_switch"]["state"], "unknown")
        self.adapter.dispatch({"threadId": "thread", "turnId": "t1", "callId": "retry",
                               "tool": "web_search", "arguments": accepted.action_request.parameters})
        self.assertEqual(len(self.seen), 1)
        self.assertFalse(self.semantic.snapshot("thread")["workflow_continuity"]["completion_established"])

    def test_legal_search_does_not_remove_provider_constraint_on_next_object(self):
        for n, query in enumerate(("object A", "object B")):
            self.assertTrue(self.dispatch("web_search", {
                "query": query, "provider": "google", "allow_fallback": False}, str(n)).ok)
        denied = self.dispatch("web_search", {
            "query": "object B", "provider": "bing", "allow_fallback": False}, "conflict")
        self.assertFalse(denied.ok)
        self.assertEqual(len(self.seen), 2)

    def test_bad_fetch_is_known_input_failure_not_network_or_unknown_execution(self):
        with patch.object(self.web, "_http_get") as http:
            for i, args in enumerate(({"max_chars": 5000}, {"max_chars": True}, {"start_char": -1},
                                      {"start_char": 1})):
                out = self.dispatch("web_fetch", {"url": "https://example.test", **args}, str(i))
                data = self.wire(out)["data"]
                self.assertEqual(data["execution_status"], "validation_failed")
                self.assertEqual(data["error_kind"], "argument_validation")
                self.assertFalse(data["http_attempted"])
                self.assertEqual(data["recovery"]["legal_next_steps"][0]["action"], "repair_arguments")
                self.assertIn("this_action", data["recovery"]["failure_scope"])
                self.assertIsNotNone(out.observation.observation_id)
            http.assert_not_called()

    def test_legacy_fetch_has_same_input_error_semantics(self):
        self.adapter.execution_boundary = None
        with patch.object(self.web, "_http_get") as http:
            data = self.wire(self.dispatch("web_fetch", {"url": "https://example.test",
                                                        "max_chars": 5000}))["data"]
        self.assertEqual(data["reason"], "invalid_arguments")
        self.assertEqual(data["recovery"]["legal_next_steps"][0]["action"], "repair_arguments")
        http.assert_not_called()

    def test_generic_value_error_after_handler_remains_unknown_not_safe_retry(self):
        with patch.object(self.adapter.registry, "execute_capability", side_effect=ValueError("internal")):
            out = self.dispatch("web_fetch", {"url": "https://example.test"})
        self.assertEqual(out.tool_result.data["execution_status"], "execution_unknown")
        self.assertIsNone(out.tool_result.data["execution_succeeded"])
        self.assertNotIn("recovery", out.tool_result.data)

    def test_http_forbidden_and_tls_are_distinct_without_security_bypass(self):
        for i, exc in enumerate((
            urllib.error.HTTPError("https://example.test", 403, "Forbidden", {}, None),
            urllib.error.URLError("TLS EOF"),
        )):
            with self.subTest(exc=type(exc).__name__), patch.object(self.web, "_http_get", side_effect=exc):
                out = self.dispatch("web_fetch", {"url": "https://example.test"}, "error" + str(i))
                data = self.wire(out)["data"]
                self.assertEqual(data["execution_status"], "http_failure" if i == 0 else "network_failure")
                self.assertEqual(data["http_status"], 403 if i == 0 else None)
                self.assertFalse(data["execution_succeeded"])
                self.assertEqual(data["recovery"]["global_web_availability"],
                                 "not_determined_by_this_failure")
                self.assertFalse(any(x.get("automatic") for x in data["recovery"]["legal_next_steps"]))

    def test_local_missing_file_stays_local_and_preserves_original_error(self):
        (self.root / "README.md").unlink()
        for mode in ("shared", "legacy"):
            if mode == "legacy":
                self.adapter.execution_boundary = None
            out = self.dispatch("read_section", {"path": "README.md", "section": "Facts"}, mode)
            wire = self.wire(out)
            self.assertFalse(wire["ok"])
            self.assertIn("No such file", wire["data"]["error"])
            self.assertEqual(wire["data"]["failure_scope"], "local_filesystem_request")
            self.assertFalse(wire["data"]["http_attempted"])
            self.assertEqual(wire["data"]["recovery"]["failure_scope"], "local_filesystem_request")

    def test_challenge_response_remains_actual_source_not_article_verification(self):
        body = b"<html><title>Verify you are human</title><p>Complete the challenge</p></html>"
        with patch.object(self.web, "_http_get", return_value={
            "body": body, "content_type": "text/html", "status": 200}):
            out = self.dispatch("web_fetch", {"url": "https://example.test"})
        wire = self.wire(out)
        self.assertTrue(wire["ok"])  # HTTP fetch succeeded, not semantic page acquisition.
        self.assertIn("challenge", wire["data"]["source_excerpt"]["text"])
        self.assertEqual(wire["data"]["temporal_facts"]["content_period"]["status"], "unknown")
        self.assertNotIn("content_supported", wire["data"])
        # Explicit upstream challenge diagnostics also remain local; no text classifier.
        rec = recovery_observation({"execution_succeeded": False, "error_kind": "content_challenge"})
        self.assertEqual(rec["failure_scope"], "this_action_only")

    def test_clock_is_resampled_and_never_becomes_requested_date_or_market_fact(self):
        for stamp in ("2026-11-05T23:59:59+00:00", "2026-11-06T00:00:01+00:00"):
            with patch("harness.io_contract.datetime") as clock:
                clock.now.return_value = datetime.fromisoformat(stamp)
                context = turn_context_payload([])
            fact = json.loads(context["uaea.runtime_facts.time"]["value"])
            self.assertEqual(fact["observed_at_utc"], stamp)
            self.assertEqual(fact["market_calendar_validation"], "not_provided")
            self.assertNotIn("price", fact)
            self.assertNotIn("requested_date", fact)
            self.assertIn("not_requested_as_of", fact["scope"])

    def test_published_date_and_access_time_cannot_create_historical_price(self):
        html = self.root / "page.html"
        html.write_text('<meta property="article:published_time" content="2025-10-31T12:00:00Z">'
                        '<p>Q3 2025; no historical closing price in excerpt.</p>')
        facts = temporal_facts({"access_event_id": "source", "accessed_at": "2026-11-05T00:00:00Z",
            "access_status": "fetched", "source_type": "web_page", "content_ref": str(html)})
        self.assertTrue(facts["published_at"].startswith("2025-10-31"))
        self.assertEqual(facts["content_period"]["status"], "unknown")
        self.assertNotIn("historical_price", facts)

    def test_error_scope_survives_provider_history_wrapping(self):
        out = self.dispatch("web_search", {"query": "x", "provider": "google", "allow_fallback": True})
        wire = self.wire(out)
        request = {"input": [{"type": "function_call_output", "call_id": "a", "output": json.dumps(wire)}]}
        projected = project_provider_history(request).request
        text = json.dumps(projected)
        self.assertIn("web.provider_fallback", text)
        self.assertIn("web.provider=google", text)
        self.assertIn("allow_fallback", text)
        self.assertEqual(wire["data"]["recovery"]["authorization"]["state"], "unknown")

    def test_actual_outbound_audit_preserves_time_original_date_and_local_denial(self):
        received = []
        class Receiver(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b'data: {"type":"response.completed"}\n\n')
        server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            refusal = self.wire(self.dispatch("web_search", {
                "query": "topic", "provider": "google", "allow_fallback": True}))
            context = turn_context_payload(self.adapter.dynamic_tools(),
                semantic_projection=self.semantic.current_projection("thread").payload)
            audit = self.root / "http-audit.jsonl"
            with ProviderHistoryBridge(f"http://127.0.0.1:{server.server_port}",
                    journal_path=self.root / "history.jsonl", audit_path=audit) as bridge:
                bridge.set_runtime_context(context, thread_id="thread",
                    input_id=self.semantic.snapshot("thread")["current_input_id"])
                body = {"input": [
                    {"role": "user", "content": [{"type": "input_text", "text":
                        "Use the actual 2026-11-04 close; no simulated price has been acquired."}]},
                    {"type": "function_call_output", "call_id": "a", "output": json.dumps(refusal)}]}
                conn = http.client.HTTPConnection("127.0.0.1", int(bridge.base_url.rsplit(":", 1)[1]))
                conn.request("POST", "/v1/responses", json.dumps(body))
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                response.read()
                conn.close()
            self.assertEqual(len(received), 1)
            sent = next(row for row in map(json.loads, audit.read_text().splitlines())
                        if row.get("request") is not None)
            self.assertEqual(sent["request"], redact(received[0]))
            text = json.dumps(received[0])
            self.assertIn("2026-11-04", text)
            self.assertIn("observed_at_utc", text)
            self.assertIn("web.provider_fallback", text)
            self.assertIn("web.provider=google", text)
            self.assertIn("not_requested_as_of_or_source_coverage", text)
            self.assertNotIn("market_calendar_verified", text)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
