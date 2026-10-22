from __future__ import annotations

import unittest

from harness.io_contract import turn_context_payload
from harness.request_continuity import parse_request_operation
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from tests.test_harness_workflow_continuity import event, output, result_event


class RequestContinuityTests(unittest.TestCase):
    def setUp(self):
        self.adapter = HarnessSemanticStateAdapter()

    def start(self, text, turn, operation="retain"):
        return self.adapter.prepare_turn("thread", text, turn_id=turn, request_operation=operation)

    def finish(self, turn, status="completed"):
        self.adapter.consume_raw_event(event("turn/completed", turnId=turn,
            turn={"id": turn, "status": status}))

    def workflow(self):
        return self.adapter.snapshot("thread")["workflow_continuity"]

    def test_request_survives_without_steps_or_model_execution(self):
        self.start("Research local runtimes. Only use Google. No fallback.", "t1")
        self.finish("t1")
        request = "Open the discovered reference and compare its lifecycle interfaces for our runtime."
        self.start(request, "t2")
        self.adapter.consume_raw_event(event("item/completed", turnId="t2", item={
            "type": "agentMessage", "id": "claim", "text": 'I read it. {"name":"web_fetch"}'}))
        self.finish("t2")
        for n in range(3, 11):
            projection = self.start("Continue", f"t{n}")
            self.finish(f"t{n}")
        continuation = projection.payload["workflow_continuation"]
        self.assertIn(request, continuation["request_history"])
        workflow = self.workflow()
        self.assertEqual(workflow["attempts"], [])
        self.assertEqual(workflow["action_request_origin"], {})
        self.assertEqual(workflow["source_coverage"]["fetched"], 0)
        self.assertEqual(workflow["request_continuity"]["fulfillment"], "not_established")
        self.assertFalse(workflow["completion_established"])
        self.assertTrue(all(x["attempts"] == 0 for x in workflow["turn_receipts"]))
        context = turn_context_payload([], semantic_projection=projection.payload)
        self.assertIn(request, context["uaea.semantic_interpretations"]["value"])
        self.assertNotIn(request, context["uaea.semantic_state_projection"]["value"])
        self.assertEqual(context["uaea.semantic_interpretations"]["kind"], "untrusted")
        self.assertEqual(projection.payload["constraints"], ["web.provider=google", "web.fallback=forbidden"])

    def test_later_action_and_outcome_link_to_preexisting_user_inputs(self):
        self.start("Research local runtimes", "t1")
        self.finish("t1")
        self.start("Read the reference first", "t2")
        original = self.adapter.snapshot("thread")["current_input_id"]
        self.finish("t2")
        self.start("Continue", "t3")
        self.adapter.consume_raw_event(event("item/tool/call", turnId="t3", callId="fetch",
            tool="web_fetch", arguments={"url": "https://example.test/reference"}))
        payload = output("fetch")
        payload.update(capability="web.fetch", tool="web_fetch")
        payload["data"].update(url="https://example.test/reference")
        raw = result_event(payload)
        raw["params"]["turnId"] = "t3"
        self.adapter.consume_raw_event(raw)
        self.adapter.consume_raw_event(raw)
        workflow = self.workflow()
        self.assertEqual(len(workflow["attempts"]), 1)
        step = workflow["attempts"][0]
        self.assertIn(original, step["action"]["harness"]["request_context_input_ids"])
        self.assertTrue(step["execution_observation_id"])
        self.assertFalse(workflow["completion_established"])

    def test_native_identity_binding_does_not_duplicate_request(self):
        self.start("Inspect the selected reference", "t1")
        self.adapter.consume_raw_event(event("item/completed", turnId="t1", item={
            "type": "userMessage", "id": "native-user", "content": [{"type": "text", "text": "Inspect the selected reference"}]}))
        requests = self.workflow()["request_continuity"]["inputs"]
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["metadata"]["provenance"]["item_id"], "native-user")
        self.assertEqual(requests[0]["metadata"]["provenance"]["turn_id"], "t1")
        self.assertIn("native-user", requests[0]["source_event_ids"])

    def test_append_retains_both_requests_without_granting_fallback(self):
        self.start("Only use Google. No fallback. Research agent runtimes.", "t1")
        self.finish("t1")
        self.start("Compare cancellation behavior as well", "t2", "append")
        self.finish("t2")
        projection = self.start("Continue", "t3")
        self.assertIn("cancellation", str(projection.payload["workflow_continuation"]))
        self.assertEqual(len(self.workflow()["request_continuity"]["retained_input_ids"]), 3)
        decision = self.adapter.validate_tool_action("thread", "web.search", {
            "provider": "google", "allow_fallback": True}, turn_id="t3", call_id="bad")
        self.assertFalse(decision["valid"])

    def test_replace_retires_old_request_without_deleting_facts_or_permissions(self):
        old = "Read source A and investigate its deployment"
        self.start(old + ". Only use Google. No fallback.", "t1")
        self.finish("t1")
        self.start("Investigate source B interfaces instead", "t2", "replace")
        self.finish("t2")
        projection = self.start("Continue", "t3")
        history = str(projection.payload["workflow_continuation"])
        self.assertNotIn("source A", history)
        self.assertIn("source B", history)
        requests = self.workflow()["request_continuity"]["inputs"]
        self.assertEqual(requests[0]["status"], "superseded")
        self.assertIn(old, requests[0]["metadata"]["text"])
        self.assertTrue(requests[0]["metadata"]["ended_by_input_id"])
        self.assertEqual(projection.payload["constraints"], ["web.provider=google", "web.fallback=forbidden"])

    def test_cancel_and_plain_continue_do_not_reactivate_old_work(self):
        self.start("Inspect source A. Only use Google. No fallback.", "t1")
        self.finish("t1")
        self.start("Cancel this request", "t2", "cancel")
        self.finish("t2")
        projection = self.start("Continue", "t3")
        context = projection.payload["workflow_continuation"]
        self.assertEqual(context["request_state"], "cancelled")
        self.assertNotIn("source A", str(context))
        self.assertEqual(self.workflow()["request_continuity"]["retained_input_ids"], [])
        self.assertFalse(self.workflow()["completion_established"])
        self.finish("t3")
        restarted = self.start("Investigate source B", "t4", "replace")
        self.assertNotIn("source A", str(restarted.payload["workflow_continuation"]))
        self.assertIn("source B", str(restarted.payload["workflow_continuation"]))

    def test_freeform_interpretation_is_retained_not_silently_promoted_or_retired(self):
        self.start("Research SDKs", "t1")
        self.finish("t1")
        self.start("Maybe focus on protocol interfaces instead", "t2")
        requests = self.workflow()["request_continuity"]["inputs"]
        self.assertTrue(all(item["status"] == "retained" for item in requests))
        self.assertTrue(all(item["metadata"]["authority_level"] == "interpretation" for item in requests))
        self.assertEqual(self.adapter.snapshot("thread")["constraints"], [])

    def test_failed_or_cancelled_turn_never_completes_request(self):
        for terminal in ("failed", "interrupted", "completed"):
            with self.subTest(terminal=terminal):
                self.setUp()
                self.start("Inspect the reference", "t1")
                self.finish("t1", terminal)
                self.assertEqual(self.workflow()["request_continuity"]["state"], "retained")
                self.assertEqual(self.workflow()["request_continuity"]["fulfillment"], "not_established")

    def test_no_cross_thread_or_workflow_request_leakage(self):
        self.start("Inspect source A", "t1")
        self.finish("t1")
        self.adapter.prepare_turn("other", "Inspect source B", turn_id="other1")
        self.assertNotIn("source A", str(self.adapter.snapshot("other")["workflow_continuity"]["request_continuity"]))
        projection = self.start("新任务：研究编译器", "t2")
        self.assertNotIn("source A", str(projection.payload["workflow_continuation"]))

    def test_dense_no_action_request_fits_budget_with_constraints(self):
        self.start("Only use Google. Do not use Bing. Do not use DuckDuckGo. No fallback. Research runtimes.", "t1")
        self.finish("t1")
        self.start("Inspect the selected sources and compare cancellation, continuation and evidence interfaces. " * 4, "t2")
        self.finish("t2")
        projection = self.start("Continue", "t3")
        context = turn_context_payload([], semantic_projection=projection.payload)
        self.assertLessEqual(sum(len(context[k]["value"]) for k in (
            "uaea.semantic_state_projection", "uaea.semantic_interpretations")), 2400)
        self.assertEqual(len(projection.payload["constraints"]), 4)
        self.assertIn("Inspect the selected sources", str(projection.payload["workflow_continuation"]))
        request_id = self.workflow()["request_continuity"]["inputs"][1]["object_id"]
        record = self.adapter._state_for("thread").runtime_objects.projections[-1]
        self.assertIn(request_id, record.source_object_ids)

    def test_explicit_controls_are_not_natural_language_keyword_extraction(self):
        self.assertEqual(parse_request_operation("Please cancel or replace whichever seems better"), "retain")
        self.assertEqual(parse_request_operation("/request cancel"), "cancel")
        self.assertEqual(parse_request_operation("/request replace Read another reference"), "replace")
        self.assertEqual(parse_request_operation("/request append Compare interfaces"), "append")
        for text in ("/request replace", "/request cancel something", "/request guessed text"):
            with self.assertRaises(ValueError):
                parse_request_operation(text)


if __name__ == "__main__":
    unittest.main()
