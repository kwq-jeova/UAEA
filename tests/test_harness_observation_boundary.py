from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.codex_dynamic_tools import DynamicToolBinding, HarnessDynamicToolAdapter, _bounded_json_text
from harness.observation_boundary import factual_web_message, observation_boundary
from harness.provider_history import project_provider_history
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from phase2.web_adapter import WebAdapter
from phase2.web_capability import WebSearchCapability, _search_success_message, web_search_metadata
from runtime.capability import ToolResult
from runtime.ledger import LedgerStub
from runtime.sandbox import Sandbox
from runtime.tools import ToolRegistry


class ObservationBoundaryTests(unittest.TestCase):
    def test_successful_google_all_evidence_states_have_no_contradictory_message(self):
        for status in ("low_relevance", "uncertain", "constraints_partially_satisfied", "relevant"):
            with self.subTest(status=status):
                data = {"actual_provider": "google", "search_provider": "www.google.com",
                        "execution_succeeded": True, "search_contract": {"candidate_status": status},
                        "citable_results": []}
                message = _search_success_message("AI research", data)
                self.assertIn("www.google.com", message)
                self.assertNotIn("do not call this Google", message)
                safe = factual_web_message("web.search", data, "do not call this Google")
                self.assertIn("successfully using google", safe)
                self.assertNotIn("do not call this Google", safe)
                self.assertIn("not network/permission restrictions", safe)

    def test_unspecified_execution_is_not_invented(self):
        self.assertEqual(factual_web_message("web.search", {"requested_provider": "google"}, "unknown"), "unknown")
        self.assertEqual(factual_web_message("web.search", {"execution_succeeded": True}, "unknown"),
                         "Search executed successfully.")

    def test_open_ended_failure_reason_survives_history_without_taxonomy(self):
        reason = "Unexpected upstream event: boundary reset (vendor code 17)"
        raw = {"input": [
            {"type": "function_call", "call_id": "call", "name": "web_search", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "call", "output": json.dumps({
                "ok": False, "message": "generic wrapper text", "data": {
                    "execution_succeeded": False, "reason": reason, "error": reason,
                    "requested_provider": "google", "actual_provider": None, "http_attempted": True,
                }})},
        ]}
        original = copy.deepcopy(raw)
        projected = project_provider_history(raw)
        fact = json.loads(projected.request["input"][1]["content"][0]["text"].split("\n", 1)[1])
        self.assertEqual(fact["reason"], reason)
        self.assertEqual(fact["observation"]["error"], reason)
        self.assertIsNone(fact["observation"]["actual_provider"])
        self.assertEqual(fact["observation"]["observation_boundary"], observation_boundary())
        self.assertEqual(raw, original)

    def test_schema_rejection_reports_argument_cause_and_policy_pass_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            web = WebAdapter(snapshot_root=root / "snapshots")
            registry.register_capability(web_search_metadata(), WebSearchCapability(db_path=root / "source.sqlite", adapter=web))
            adapter = HarnessDynamicToolAdapter(registry, [DynamicToolBinding.from_registry(
                registry, "web.search", description="Search", input_schema={"type": "object"})])
            semantic = HarnessSemanticStateAdapter()
            semantic.prepare_turn("thread", "仅使用 Google，不允许 fallback，查 AI research", turn_id="policy")
            adapter.bind_semantic_state_adapter(semantic)
            with patch.object(web, "search") as http:
                dispatch = adapter.dispatch({"threadId": "thread", "turnId": "turn", "callId": "call",
                    "tool": "web_search", "arguments": {"query": "AI research", "provider": "google",
                    "allow_fallback": False, "source_types": ["blog"]}})
            http.assert_not_called()
            raw = copy.deepcopy(dispatch.tool_result.data)
            payload = json.loads(dispatch.to_app_server_response()["contentItems"][0]["text"])
            data = payload["data"]
            self.assertFalse(data["http_attempted"])
            self.assertTrue(data["policy_validation_passed"])
            self.assertEqual(data["validation_source"], "capability_input")
            self.assertEqual(data["requested_provider"], "google")
            self.assertIsNone(data["actual_provider"])
            self.assertIn("unsupported source_types value: blog", data["error"])
            self.assertIn("unsupported source_types value: blog", payload["message"])
            recovery = data["recovery"]
            self.assertEqual(recovery["legal_next_steps"], [{"action": "repair_arguments",
                "use_current_tool_schema": True, "preserve_active_constraints": True,
                "requires_current_policy_validation": True}])
            self.assertIn("web.provider=google", recovery["active_constraints"])
            self.assertEqual(recovery["authorization"]["state"], "denied")
            self.assertEqual(recovery["authorization"]["scope"], "web.provider_fallback")
            self.assertEqual(dispatch.tool_result.data, raw)

    def test_boundary_and_raw_cause_survive_recovery_budget(self):
        from harness.recovery_observation import recovery_observation
        cause = "Unsupported optional argument from the current tool schema"
        data = {"capability": "web.search", "execution_status": "validation_failed",
                "execution_succeeded": False, "http_attempted": False, "error": cause,
                "validation_source": "capability_input", "retryable": True,
                "active_constraints": ["web.provider=google", "web.fallback=forbidden"],
                "authorization": {"state": "denied"}, "observation_boundary": observation_boundary(),
                "diagnostic_padding": "x" * 12000}
        data["recovery"] = recovery_observation(data)
        result = json.loads(_bounded_json_text({"ok": False, "capability": "web.search", "data": data}, 2000))
        self.assertEqual(result["data"]["error"], cause)
        self.assertEqual(result["data"]["observation_boundary"], observation_boundary())
        self.assertEqual(result["data"]["recovery"], data["recovery"])

    def test_insufficient_evidence_projection_preserves_execution_and_hides_raw_links(self):
        for status in ("low_relevance", "uncertain", "no_candidates"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                raw = {"execution_status": "success", "execution_succeeded": True,
                       "requested_provider": "google", "actual_provider": "google", "http_attempted": True,
                       "search_contract": {"candidate_status": status}, "citable_results": [],
                       "raw_search_results": [{"url": "https://noise.example/", "snippet": "x" * 12000}]}
                registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
                registry.register_capability(web_search_metadata(), lambda args, objective: ToolResult(True, "do not call this Google", raw))
                adapter = HarnessDynamicToolAdapter(registry, [DynamicToolBinding.from_registry(
                    registry, "web.search", description="Search", input_schema={"type": "object"})], max_output_chars=2000)
                dispatch = adapter.dispatch({"threadId": "thread", "turnId": "turn", "callId": "call",
                    "tool": "web_search", "arguments": {"query": "AI research"}})
                text = dispatch.to_app_server_response()["contentItems"][0]["text"]
                data = json.loads(text)["data"]
                self.assertTrue(data["execution_succeeded"])
                self.assertEqual(data["actual_provider"], "google")
                self.assertEqual(data["citable_results"], [])
                self.assertEqual(data["observation_boundary"], observation_boundary())
                self.assertNotIn("https://noise.example/", text)
                self.assertNotIn("do not call this Google", text)
                self.assertEqual(dispatch.tool_result.data, raw)

    def test_success_message_counts_retained_candidates_not_internal_candidates(self):
        from tests.test_harness_boundary_integrity import search_payload
        payload = search_payload()
        payload["data"]["observation_boundary"] = observation_boundary()
        visible = json.loads(_bounded_json_text(payload, 2200))
        count = len(visible["data"]["citable_results"])
        self.assertGreater(count, 0)
        self.assertLess(count, len(payload["data"]["citable_results"]))
        self.assertIn(f"citable candidates: {count}", visible["message"])


if __name__ == "__main__":
    unittest.main()
