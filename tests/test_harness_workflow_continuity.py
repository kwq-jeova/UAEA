from __future__ import annotations

import json
import unittest

from harness.io_contract import turn_context_payload
from harness.semantic_authority import expand_semantic_binding, has_execution_authority
from harness.semantic_state_adapter import HarnessSemanticStateAdapter


def event(method, **params):
    return {"method": method, "params": {"threadId": "thread", "turnId": "turn1", **params}}


def output(call="call1", *, succeeded=True, eligibility="low_relevance", status="success", http=True):
    return {"ok": succeeded, "capability": "web.search", "tool": "web_search", "status": status,
            "identity": {"call_id": call}, "message": "Recorded search outcome",
            "data": {"execution_status": status, "execution_succeeded": succeeded,
                     "http_attempted": http, "actual_provider": "google" if succeeded else None,
                     "result_available": succeeded, "evidence_status": eligibility,
                     "citable_results": [{"title": "MCP reference", "url": "https://example.test/mcp"}]
                     if eligibility == "relevant" else []}}


def result_event(payload, *, raw=False):
    if raw:
        return event("rawResponseItem/completed", item={"type": "function_call_output", "id": "fco1",
                                                      "call_id": payload["identity"]["call_id"],
                                                      "output": json.dumps(payload)})
    return event("item/completed", item={"type": "dynamicToolCall", "id": payload["identity"]["call_id"],
                                        "tool": "web_search", "status": "completed", "success": payload["ok"],
                                        "contentItems": [{"type": "inputText", "text": json.dumps(payload)}]})


class WorkflowContinuityTests(unittest.TestCase):
    def adapter(self, text="Research AI agent tools using Google; no fallback"):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", text, turn_id="turn1")
        return adapter

    def call(self, adapter, call="call1"):
        adapter.consume_raw_event(event("item/tool/call", callId=call, tool="web_search",
                                       arguments={"query": "AI agent", "provider": "google", "allow_fallback": False}))

    def finish(self, adapter, turn="turn1", status="completed"):
        adapter.consume_raw_event(event("turn/completed", turn={"id": turn, "status": status}))

    def test_relation_hint_cannot_replace_workflow_root(self):
        adapter = self.adapter("Research AI agent tools")
        first = adapter.snapshot("thread")
        self.finish(adapter)
        second = adapter.prepare_turn("thread", "Compare MCP and Agents SDK", turn_id="turn2")
        self.assertEqual(second.payload["topic"], first["topic"])
        self.assertEqual(second.payload["task_id"], first["task_id"])
        self.assertEqual(adapter.snapshot("thread")["last_user_input"], "Compare MCP and Agents SDK")
        self.finish(adapter, turn="turn2")
        third = adapter.prepare_turn("thread", "Expand the selected project", turn_id="turn3")
        self.assertEqual(third.payload["workflow_continuation"]["request_history"][-1], "Compare MCP and Agents SDK")
        new = adapter.prepare_turn("thread", "新任务：研究编译器", turn_id="turn4")
        self.assertNotEqual(new.payload["task_id"], first["task_id"])
        self.assertEqual(new.payload["workflow_execution"]["completion_established"], False)

    def test_assistant_claim_is_not_execution_and_no_action_receipt_survives(self):
        adapter = self.adapter()
        adapter.consume_raw_event(event("item/completed", item={"type": "agentMessage", "id": "a1",
                                                                 "text": "I searched and finished all research."}))
        self.finish(adapter)
        projection = adapter.prepare_turn("thread", "Expand the first project", turn_id="turn2")
        workflow = adapter.snapshot("thread")["workflow_continuity"]
        self.assertEqual(workflow["attempts"], [])
        self.assertEqual(workflow["turn_receipts"][-1]["attempts"], 0)
        self.assertEqual(workflow["status"], "active")
        self.assertFalse(projection.payload["workflow_execution"]["completion_established"])
        self.assertIn("I searched", projection.payload["workflow_continuation"]["assistant_proposal"])
        context = turn_context_payload([], semantic_projection=projection.payload)
        self.assertEqual(context["uaea.semantic_interpretations"]["kind"], "untrusted")
        self.assertNotIn("assistant_proposal", context["uaea.semantic_state_projection"]["value"])

    def test_call_and_result_representations_share_one_attempt_and_observation(self):
        adapter = self.adapter()
        self.call(adapter)
        adapter.consume_raw_event(event("item/started", item={"type": "dynamicToolCall", "id": "call1",
                                                               "tool": "web_search", "arguments": {}}))
        payload = output()
        adapter.consume_raw_event(result_event(payload), raw_event_reference={"line": 3})
        adapter.consume_raw_event(result_event(payload, raw=True), raw_event_reference={"line": 4})
        snapshot = adapter.snapshot("thread")
        self.assertEqual(len(snapshot["semantic_observations"]), 1)
        steps = snapshot["workflow_continuity"]["attempts"]
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["action"]["arguments"]["query"], "AI agent")
        sources = steps[0]["action"]["harness"]["sources"]
        self.assertIn(3, [item["raw_event_reference"].get("line") for item in sources])
        self.assertIn(4, [item["raw_event_reference"].get("line") for item in sources])

    def test_execution_success_and_evidence_insufficiency_are_independent(self):
        adapter = self.adapter()
        self.call(adapter)
        adapter.consume_raw_event(result_event(output()))
        self.finish(adapter)
        projection = adapter.prepare_turn("thread", "Continue with better evidence", turn_id="turn2")
        attempt = projection.payload["workflow_execution"]["last_attempt"]
        self.assertTrue(attempt["execution_succeeded"])
        self.assertEqual(attempt["evidence_status"], "low_relevance")
        self.assertEqual(attempt["citable_count"], 0)
        self.assertNotIn("candidate", projection.payload["workflow_execution"])
        self.assertEqual(adapter.snapshot("thread")["workflow_continuity"]["unresolved"][0]["state"], "evidence_insufficient")

    def test_rejected_then_successful_retry_updates_attempts_not_workflow_completion(self):
        adapter = self.adapter("仅使用 Google，不允许 fallback")
        self.call(adapter, "bad")
        decision = adapter.validate_tool_action("thread", "web.search", {"provider": "google", "allow_fallback": True},
                                                turn_id="turn1", call_id="bad")
        self.assertFalse(decision["valid"])
        adapter.consume_raw_event(result_event(output("bad", succeeded=False, status="validation_failed", http=False)))
        self.call(adapter, "good")
        adapter.consume_raw_event(result_event(output("good", eligibility="relevant")))
        self.finish(adapter)
        workflow = adapter.snapshot("thread")["workflow_continuity"]
        self.assertEqual([item["status"] for item in workflow["attempts"]], ["rejected", "completed"])
        self.assertFalse(workflow["attempts"][0]["action"]["outcome"]["http_attempted"])
        self.assertEqual(workflow["status"], "active")
        self.assertEqual(workflow["turn_receipts"][-1]["successful"], 1)
        projection = adapter.prepare_turn("thread", "Expand MCP reference", turn_id="turn2")
        self.assertEqual(projection.payload["workflow_execution"]["candidate"]["url"], "https://example.test/mcp")

    def test_missing_or_cancelled_result_does_not_become_execution(self):
        for terminal, expected in (("completed", "outcome_missing"), ("interrupted", "cancelled")):
            with self.subTest(terminal=terminal):
                adapter = self.adapter()
                self.call(adapter)
                self.finish(adapter, status=terminal)
                step = adapter.snapshot("thread")["workflow_continuity"]["attempts"][0]
                self.assertEqual(step["status"], expected)
                self.assertNotIn("outcome", step["action"])
                self.assertEqual(adapter.snapshot("thread")["workflow_continuity"]["turn_receipts"][-1]["successful"], 0)

    def test_dense_authority_keeps_minimal_continuation_and_actual_wire_budget(self):
        text = "仅使用 Google 搜索 AI agent，不要使用 Bing，不要使用 DuckDuckGo，禁止 fallback。"
        adapter = self.adapter(text)
        self.call(adapter, "call_abcdef1234567890")
        adapter.consume_raw_event(result_event(output("call_abcdef1234567890")))
        self.finish(adapter)
        projection = adapter.prepare_turn("thread", "选择 MCP 对象，展开工具权限与开发社区资料", turn_id="turn2")
        self.assertIn("AI agent", projection.payload["workflow_continuation"]["initial_request"])
        self.assertIn("MCP", adapter.snapshot("thread")["last_user_input"])
        self.assertEqual(projection.payload["workflow_execution"]["last_attempt"]["evidence_status"], "low_relevance")
        self.assertEqual(len(projection.payload["constraints"]), 4)
        context = turn_context_payload([], semantic_projection=projection.payload)
        self.assertLessEqual(sum(len(context[key]["value"]) for key in
                                 ("uaea.semantic_state_projection", "uaea.semantic_interpretations")), 2400)
        for binding in projection.payload["semantic_bindings"]:
            self.assertTrue(has_execution_authority(expand_semantic_binding(
                binding, projection.payload.get("semantic_binding_defaults"))))

    def test_thread_and_explicit_workflow_isolation(self):
        adapter = self.adapter()
        self.call(adapter)
        adapter.consume_raw_event(result_event(output()))
        adapter.prepare_turn("other", "Research compilers")
        self.assertEqual(adapter.snapshot("other")["workflow_continuity"]["attempts"], [])
        adapter.prepare_turn("thread", "新任务：研究编译器", turn_id="turn2")
        self.assertEqual(adapter.snapshot("thread")["workflow_continuity"]["attempts"], [])
        self.assertEqual(adapter.snapshot("thread")["phase1_runtime_snapshot"]["step_count"], 1)

    def test_real_identity_dense_constraints_retain_prior_selection_after_fetch(self):
        thread = "01a12a84-5f8a-70c0-8162-7de652c19469"
        adapter = HarnessSemanticStateAdapter()
        initial = "Research OpenAI Agents SDK and Anthropic Model Context Protocol using public sources. Only use Google. Do not use Bing. Do not use DuckDuckGo. No fallback."
        adapter.prepare_turn(thread, initial, turn_id="01a12a84-6163-7570-97ad-8967e81fc5f8")
        adapter.prepare_turn(thread, "Continue the same research. Select OpenAI Agents SDK for further investigation, focusing on tools and handoffs.",
                             turn_id="01a12a84-9d0e-7dc1-8781-3a4f420e0e5e")
        payload = output("call_8866e1f83fa0de17")
        payload.update({"capability": "web.fetch", "tool": "web_fetch"})
        payload["data"] = {"execution_succeeded": True, "execution_status": "success",
                           "http_attempted": True, "url": "https://example.test/agents-sdk"}
        raw = result_event(payload)
        raw["params"].update({"threadId": thread, "turnId": "01a12a84-9d0e-7dc1-8781-3a4f420e0e5e"})
        adapter.consume_raw_event(raw)
        adapter.consume_raw_event({"method": "turn/completed", "params": {
            "threadId": thread, "turn": {"id": raw["params"]["turnId"], "status": "completed"}}})
        projection = adapter.prepare_turn(thread, "Expand that selected project and summarize evidence and unfinished work")
        self.assertLessEqual(len(projection.to_context_value()), 2400)
        self.assertIn("Model Context Protocol", projection.payload["workflow_continuation"]["initial_request"])
        self.assertIn("Select OpenAI Agents SDK", projection.payload["workflow_continuation"]["request_history"][-1])
        self.assertNotIn("citable_count", projection.payload["workflow_execution"]["last_attempt"])
        self.assertEqual(adapter.snapshot(thread)["workflow_continuity"]["attempts"][0]["action"]["outcome"]["source_url"],
                         "https://example.test/agents-sdk")

    def test_three_turn_search_continuation_with_native_ids_and_four_policies(self):
        thread = "01a12a88-c8fd-79f1-aeba-8b9ce154b345"
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn(thread, "Research OpenAI Agents SDK and Anthropic Model Context Protocol using public sources. Only use Google. Do not use Bing. Do not use DuckDuckGo. No fallback.")
        for index in range(2):
            if index:
                adapter.prepare_turn(thread, "Continue the same research. Select OpenAI Agents SDK for further investigation, focusing on tools and handoffs. Use official documentation.")
            turn = f"01a12a88-abcd-79f1-aeba-8b9ce154b34{index}"
            payload = output(f"call_98372440b039fce{index}", eligibility="relevant")
            raw = result_event(payload)
            raw["params"].update({"threadId": thread, "turnId": turn})
            adapter.consume_raw_event(raw)
            adapter.consume_raw_event({"method": "turn/completed", "params": {
                "threadId": thread, "turn": {"id": turn, "status": "completed"}}})
        projection = adapter.prepare_turn(thread, "Expand that selected project and distinguish obtained evidence from unfinished work.")
        context = turn_context_payload([], semantic_projection=projection.payload)
        self.assertLessEqual(sum(len(context[key]["value"]) for key in
                                 ("uaea.semantic_state_projection", "uaea.semantic_interpretations")), 2400)
        self.assertEqual(projection.payload["workflow_execution"]["last_attempt"]["evidence_status"], "relevant")
        self.assertIn("Select OpenAI Agents SDK", projection.payload["workflow_continuation"]["request_history"][-1])
        self.assertEqual(len(projection.payload["constraints"]), 4)


if __name__ == "__main__":
    unittest.main()
