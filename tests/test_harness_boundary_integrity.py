from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "phase1-runtime"))

from harness.codex_dynamic_tools import (
    _bounded_json_text, _fallback_data, _minimal_payload, _model_visible_tool_data,
)
from harness.semantic_state_adapter import HarnessSemanticStateAdapter


def search_payload():
    candidates = [{"title": f"AI agent discussion {index}",
                   "url": "https://www.reddit.com/r/AI_Agents/comments/" + str(index) + "/" + "x" * 180,
                   "snippet": "AI agent research " * 200} for index in range(5)]
    return {
        "ok": True, "capability": "web.search", "tool": "web_search", "status": "success",
        "message": "Search executed", "identity": {"thread_id": "thread", "turn_id": "turn", "call_id": "call"},
        "data": {"execution_status": "success", "execution_succeeded": True,
                 "requested_provider": "google", "actual_provider": "google",
                 "acquisition_backend": "serpapi", "fallback_occurred": False,
                 "access_event_id": "event-serp", "web_source_id": "source-serp",
                 "search_query": "AI agent research", "evidence_status": "relevant",
                 "search_contract": {"candidate_status": "relevant", "citable_result_count": 5},
                 "evidence_eligibility": {"candidate_status": "relevant", "citable_result_count": 5},
                 "evidence_reference": {"source_kind": "web_access_event", "source_id": "source-serp",
                                        "source_event_id": "event-serp", "summary": "s" * 6000},
                 "citable_results": candidates, "search_results": candidates,
                 "candidate_evidence_results": candidates, "bounded_evidence_block": "x" * 12000,
                 "network_diagnostics": {"events": ["private diagnostic" * 200]}}}


def completed_result(item, method="item/completed", turn="turn"):
    return {"message": {"method": method, "params": {
        "threadId": "thread", "turnId": turn, "item": item}}}


class BoundaryIntegrityTests(unittest.TestCase):
    def test_retained_web_candidates_keep_exact_title_url_and_provenance(self):
        payload = search_payload()
        original = json.dumps(payload)
        for budget in (5000, 2000):
            with self.subTest(budget=budget):
                text = _bounded_json_text(payload, budget)
                out = json.loads(text)
                data = out["data"]
                candidates = data["citable_results"]
                self.assertGreater(len(candidates), 0)
                self.assertLessEqual(len(text), budget)
                self.assertEqual(data["citable_result_count"], len(candidates))
                self.assertEqual(data["search_contract"]["citable_result_count"], len(candidates))
                self.assertEqual(out["identity"], payload["identity"])
                self.assertEqual(data["evidence_reference"]["source_id"], "source-serp")
                self.assertEqual(data["evidence_reference"]["source_event_id"], "event-serp")
                for index, item in enumerate(candidates):
                    self.assertEqual(item["title"], payload["data"]["citable_results"][index]["title"])
                    self.assertEqual(item["url"], payload["data"]["citable_results"][index]["url"])
                self.assertNotIn("network_diagnostics", data)
        self.assertEqual(json.dumps(payload), original)

    def test_candidate_identity_too_large_is_not_truncated_or_reported_as_citable(self):
        payload = search_payload()
        for item in payload["data"]["citable_results"]:
            item["url"] = "https://example.test/" + "u" * 6000
        data = json.loads(_bounded_json_text(payload, 2000))["data"]
        self.assertEqual(data["citable_results"], [])
        self.assertEqual(data["citable_result_count"], 0)
        self.assertEqual(data["search_contract"]["citable_result_count"], 0)
        self.assertEqual(data["projection_status"], "identity_exceeds_budget")
        self.assertEqual(data["recommended_next_action"], "report_projection_limit")
        self.assertEqual(payload["data"]["citable_results"][0]["url"], "https://example.test/" + "u" * 6000)

    def test_internal_diagnostics_are_never_a_model_visible_field_even_without_truncation(self):
        for capability in ("web.search", "web.fetch"):
            data = {"execution_succeeded": True, "network_diagnostics": {"proxy": "internal"}, "url": "https://example.test/"}
            projected = _model_visible_tool_data(capability, data)
            self.assertNotIn("network_diagnostics", projected)
            self.assertIn("network_diagnostics", data)

    def test_document_path_and_evidence_ids_survive_generic_bounding(self):
        path = "documents/" + "p" * 150 + ".md"
        ref = {"source_kind": "document", "source_id": "document:" + path,
               "source_event_id": "event:" + "e" * 150, "summary": "s" * 3000}
        payload = {"ok": True, "capability": "document.read_section", "tool": "read_section",
                   "status": "success", "message": "Read section",
                   "data": {"path": path, "section_index": 1, "evidence_reference": ref, "content": "x" * 10000}}
        text = _bounded_json_text(payload, 1500)
        data = json.loads(text)["data"]
        self.assertEqual(data["path"], path)
        self.assertEqual(data["evidence_reference"]["source_id"], ref["source_id"])
        self.assertEqual(data["evidence_reference"]["source_event_id"], ref["source_event_id"])
        self.assertLessEqual(len(text), 1500)

    def test_impossible_budget_is_explicit_instead_of_truncating_identity(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            _bounded_json_text(search_payload(), 100)

    def test_minimal_and_fallback_paths_preserve_top_level_target_identity(self):
        path = "documents/" + "p" * 300 + ".md"
        ref = {"source_id": "source:" + "s" * 300, "location": path}
        payload = {"ok": True, "capability": "document.read_section", "tool": "read_section",
                   "data": {"path": path, "handle": path, "evidence_reference": ref}}
        for projected in (_minimal_payload(payload)["data"], _fallback_data(payload, 1000)):
            self.assertEqual(projected["path"], path)
            self.assertEqual(projected["handle"], path)
            self.assertEqual(projected["evidence_reference"], ref)

    def test_raw_function_output_keeps_typed_execution_truth(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "AI agent research", turn_id="turn")
        for index, ok in enumerate((True, False)):
            result = {"ok": ok, "capability": "web.search", "tool": "web_search", "message": "execution",
                      "data": {"execution_succeeded": ok, "requested_provider": "google",
                               "actual_provider": "google" if ok else None, "execution_status": "success" if ok else "network_failure"}}
            adapter.consume_raw_event(completed_result({"type": "function_call_output", "id": f"raw-{index}",
                "call_id": f"call-{index}", "output": json.dumps(result)}, "rawResponseItem/completed"),
                raw_event_reference={"fixture": "raw-function-output"})
            observation = adapter.snapshot("thread")["last_execution_observation"]
            self.assertEqual(observation["capability"], "web.search")
            self.assertEqual(observation["status"], "success" if ok else "failure")
            self.assertEqual(observation["data"]["result"], result)

    def test_completed_protocol_item_cannot_override_false_execution_success(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "AI agent research", turn_id="turn")
        adapter.consume_raw_event(completed_result({"type": "dynamicToolCall", "id": "call",
            "tool": "web_fetch", "status": "completed", "success": False,
            "contentItems": [{"type": "inputText", "text": json.dumps({"ok": False,
                "capability": "web.fetch", "tool": "web_fetch", "data": {"actual_provider": None}})}]}))
        self.assertEqual(adapter.snapshot("thread")["last_execution_observation"]["status"], "failure")

    def test_native_command_start_does_not_hide_terminal_output(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "Read README", turn_id="turn")
        adapter.consume_raw_event(completed_result({"type": "commandExecution", "id": "command",
            "command": "cat README.md", "status": "inProgress"}, "item/started"))
        self.assertIsNone(adapter.snapshot("thread")["last_execution_observation"])
        adapter.consume_raw_event(completed_result({"type": "commandExecution", "id": "command",
            "command": "cat README.md", "status": "completed", "exitCode": 1, "aggregatedOutput": "file missing"}))
        observation = adapter.snapshot("thread")["last_execution_observation"]
        self.assertEqual(observation["status"], "failure")
        self.assertIn("file missing", observation["message"])

    def test_model_proposal_cannot_grant_unknown_fallback_permission(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "Google 搜索 AI agent", turn_id="turn")
        adapter.consume_raw_event(completed_result({"type": "agentMessage", "id": "agent",
                                                   "text": "是否允许 fallback？"}))
        before = adapter.snapshot("thread")["effective_state_id"]
        rejected = adapter.validate_tool_action("thread", "web.search", {"provider": "google", "allow_fallback": True})
        self.assertFalse(rejected["valid"])
        self.assertEqual(rejected["authorization"]["state"], "unknown")
        self.assertEqual(rejected["effective_state_id"], before)
        adapter.prepare_turn("thread", "允许 fallback", turn_id="authorized")
        accepted = adapter.validate_tool_action("thread", "web.search", {"provider": "google", "allow_fallback": True})
        self.assertTrue(accepted["valid"])
        self.assertEqual(accepted["authorization"]["state"], "granted")
        self.assertEqual(accepted["authorization"]["source_items"][0]["metadata"]["provenance"]["turn_id"], "authorized")

    def test_tool_error_does_not_expire_turn_scope_before_turn_terminal(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "本轮不允许 fallback", turn_id="turn")
        adapter.consume_raw_event(completed_result({"type": "dynamicToolCall", "id": "call",
                                                   "status": "failed", "success": False}))
        self.assertIn("web.fallback=forbidden", adapter.snapshot("thread")["constraints"])
        adapter.consume_raw_event({"message": {"method": "turn/completed", "params": {
            "threadId": "thread", "turn": {"id": "turn", "status": "completed"}}}})
        self.assertNotIn("web.fallback=forbidden", adapter.snapshot("thread")["constraints"])

    def test_task_owned_observation_is_not_projected_as_evidence_for_new_task(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "AI agent research", turn_id="turn")
        adapter.consume_raw_event(completed_result({"type": "dynamicToolCall", "id": "call",
            "tool": "web_search", "status": "completed", "success": True}))
        previous = adapter.snapshot("thread")
        record = previous["semantic_observations"][0]
        self.assertEqual(record["provenance"]["task_id"], previous["task_id"])
        projection = adapter.prepare_turn("thread", "新任务：研究编译器", turn_id="turn-2")
        self.assertEqual(projection.payload["relevant_observations"], [])
        self.assertEqual(len(adapter.snapshot("thread")["semantic_observations"]), 1)

    def test_retryable_runtime_error_does_not_end_turn_policy(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "本轮不允许 fallback", turn_id="turn")
        adapter.consume_raw_event({"message": {"method": "error", "params": {
            "threadId": "thread", "turnId": "turn", "willRetry": True, "error": {"message": "retrying"}}}})
        self.assertIn("web.fallback=forbidden", adapter.snapshot("thread")["constraints"])


if __name__ == "__main__":
    unittest.main()
