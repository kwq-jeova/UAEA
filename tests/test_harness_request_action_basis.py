from __future__ import annotations

import json
import unittest

from harness.io_contract import turn_context_payload
from tests import test_harness_source_coverage as coverage_tests
from tests.test_harness_workflow_continuity import event, output, result_event


class RequestActionBasisTests(unittest.TestCase):
    def setUp(self):
        self.fixture = coverage_tests.SourceCoverageTests()
        self.fixture.setup_sources()
        self.adapter = self.fixture.adapter

    def test_short_action_followups_keep_origin_without_mislabeling_latest_request(self):
        self.fixture.fetch("first", self.fixture.urls[0])
        self.fixture.finish("turn2")
        for number in (3, 4, 5):
            turn = f"turn{number}"
            self.adapter.prepare_turn("thread", "Continue", turn_id=turn)
            self.adapter.consume_raw_event(event("item/tool/call", turnId=turn,
                callId=f"fetch{number}", tool="web_fetch", arguments={"url": self.fixture.urls[1]}))
            self.fixture.finish(turn)
        projection = self.adapter.prepare_turn("thread", "How would you build the runtime?", turn_id="turn6")
        snapshot = self.adapter.snapshot("thread")["workflow_continuity"]
        origin = snapshot["action_request_origin"]
        self.assertIn("Explore these six links", origin["user_request"])
        self.assertEqual(origin["call_id"], "first")
        self.assertEqual(origin["turn_id"], "turn2")
        self.assertTrue(origin["input_id"])
        self.assertEqual(snapshot["last_action_request"]["user_request"], "Continue")
        context = turn_context_payload([], semantic_projection=projection.payload)
        interpretation = json.loads(context["uaea.semantic_interpretations"]["value"])
        authority = context["uaea.semantic_state_projection"]["value"]
        self.assertIn("Explore these six links", interpretation["workflow_continuation"]["request_history"][0])
        self.assertNotIn("Explore these six links", authority)
        self.assertEqual(context["uaea.semantic_interpretations"]["kind"], "untrusted")
        self.assertFalse(snapshot["completion_established"])
        self.assertLessEqual(sum(len(context[k]["value"]) for k in (
            "uaea.semantic_state_projection", "uaea.semantic_interpretations")), 2400)

    def test_origin_is_historical_not_a_replacement_for_later_user_correction(self):
        self.fixture.fetch("first", self.fixture.urls[0])
        self.fixture.finish("turn2")
        correction = "Continue the same research, but inspect the repository instead of these pages."
        self.adapter.prepare_turn("thread", correction, turn_id="turn3")
        self.adapter.consume_raw_event(event("item/tool/call", turnId="turn3", callId="corrected",
            tool="web_search", arguments={"query": "official repository"}))
        self.fixture.finish("turn3")
        projection = self.adapter.prepare_turn("thread", "What remains?", turn_id="turn4")
        history = projection.payload["workflow_continuation"]["request_history"]
        self.assertIn("Explore these six links", history[0])
        self.assertTrue(any("repository" in text for text in history))
        self.assertEqual(projection.payload["constraints"], ["web.provider=google", "web.fallback=forbidden"])

    def test_query_is_a_proposed_action_not_a_verified_task_interpretation(self):
        self.adapter.consume_raw_event(event("item/tool/call", turnId="turn2", callId="assumed",
            tool="web_search", arguments={"query": "MCP Multi-Container Platform"}))
        payload = output("assumed", succeeded=False, status="validation_failed")
        raw = result_event(payload)
        raw["params"]["turnId"] = "turn2"
        self.adapter.consume_raw_event(raw)
        self.fixture.finish("turn2")
        projection = self.adapter.prepare_turn("thread", "Continue", turn_id="turn3")
        search = projection.payload["workflow_execution"]["last_search_action"]
        self.assertEqual(search["query"], "MCP Multi-Container Platform")
        self.assertEqual(search["task_alignment"], "not_evaluated")
        self.assertEqual(search["call_id"], "assumed")
        self.assertFalse(projection.payload["workflow_execution"]["last_attempt"]["execution_succeeded"])
        self.assertNotIn("Multi-Container Platform", projection.payload["topic"])

    def test_task_and_thread_isolation(self):
        self.fixture.fetch("first", self.fixture.urls[0])
        self.fixture.finish("turn2")
        self.adapter.prepare_turn("other", "Unrelated task")
        self.assertEqual(self.adapter.snapshot("other")["workflow_continuity"]["action_request_origin"], {})
        self.adapter.prepare_turn("thread", "新任务：研究编译器", turn_id="turn3")
        current = self.adapter.snapshot("thread")["workflow_continuity"]
        self.assertEqual(current["action_request_origin"], {})
        self.assertNotIn("last_search_action", self.adapter.snapshot("thread")["last_projection"]["workflow_execution"])

    def test_dense_budget_keeps_constraints_and_does_not_mutate_request_or_query(self):
        self.fixture.setup_sources(dense=True)
        self.adapter = self.fixture.adapter
        self.fixture.fetch("first", self.fixture.urls[0])
        self.fixture.finish("turn2")
        self.adapter.prepare_turn("thread", "Continue", turn_id="turn3")
        query = "unconfirmed interpretation " * 100
        self.adapter.consume_raw_event(event("item/tool/call", turnId="turn3", callId="long_query",
            tool="web_search", arguments={"query": query}))
        self.fixture.finish("turn3")
        projection = self.adapter.prepare_turn("thread", "What remains?", turn_id="turn4")
        context = turn_context_payload([], semantic_projection=projection.payload)
        self.assertLessEqual(sum(len(context[k]["value"]) for k in (
            "uaea.semantic_state_projection", "uaea.semantic_interpretations")), 2400)
        self.assertEqual(len(projection.payload["constraints"]), 4)
        self.assertIn("Explore these six links", projection.payload["workflow_continuation"]["request_history"][0])
        snapshot = self.adapter.snapshot("thread")["workflow_continuity"]
        self.assertEqual(snapshot["attempts"][-1]["action"]["arguments"]["query"], query)
        self.assertEqual(snapshot["action_request_origin"]["user_request"],
                         "Explore these six links to inform a local runtime design.")


if __name__ == "__main__":
    unittest.main()
