from __future__ import annotations

import json
import unittest

from harness.io_contract import turn_context_payload
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from tests.test_harness_workflow_continuity import event, output, result_event


class SourceCoverageTests(unittest.TestCase):
    def setup_sources(self, *, dense=False, urls=None):
        self.adapter = HarnessSemanticStateAdapter()
        self.adapter.prepare_turn("thread", (
            "Only use Google. Do not use Bing. Do not use DuckDuckGo. No fallback. Research Agents SDK and MCP."
            if dense else "Research Agents SDK and MCP. Only use Google. No fallback."), turn_id="turn1")
        self.urls = urls or [f"https://example.test/source-{i}" for i in range(6)]
        payload = output("search", eligibility="relevant")
        payload["data"]["citable_results"] = [{"url": url, "title": f"Source {i}"}
                                                 for i, url in enumerate(self.urls)]
        self.adapter.consume_raw_event(event("item/tool/call", callId="search", tool="web_search",
                                            arguments={"query": "Agents SDK MCP"}))
        self.adapter.consume_raw_event(result_event(payload))
        self.finish("turn1")
        self.adapter.prepare_turn("thread", "Explore these six links to inform a local runtime design.", turn_id="turn2")

    def finish(self, turn):
        self.adapter.consume_raw_event(event("turn/completed", turnId=turn, turn={"id": turn, "status": "completed"}))

    def fetch(self, call, url, *, succeeded=True, status="success"):
        self.adapter.consume_raw_event(event("item/tool/call", turnId="turn2", callId=call,
                                            tool="web_fetch", arguments={"url": url}))
        payload = output(call, succeeded=succeeded, status=status)
        payload.update({"capability": "web.fetch", "tool": "web_fetch"})
        payload["data"] = {"execution_status": status, "execution_succeeded": succeeded,
                           "http_attempted": status != "validation_failed", "result_available": succeeded,
                           "url": url if succeeded else None, "access_event_id": f"event-{call}"}
        raw = result_event(payload)
        raw["params"]["turnId"] = "turn2"
        self.adapter.consume_raw_event(raw)
        return payload

    def coverage(self):
        return self.adapter.snapshot("thread")["workflow_continuity"]["source_coverage"]

    def test_six_discovered_two_fetched_and_four_unattempted(self):
        self.setup_sources()
        self.fetch("read1", self.urls[0])
        self.fetch("read2", self.urls[3])
        coverage = self.coverage()
        self.assertEqual([coverage[key] for key in ("discovered", "fetched", "unattempted", "failed")], [6, 2, 4, 0])
        self.assertEqual(coverage["sources"][0]["fetch_attempts"][0]["call_id"], "read1")
        self.assertEqual(coverage["sources"][0]["discovered_by"][0]["call_id"], "search")
        self.finish("turn2")
        projection = self.adapter.prepare_turn("thread", "What did we actually obtain?", turn_id="turn3")
        projected = projection.payload["workflow_execution"]["source_coverage"]
        self.assertEqual(projected["fetched"], 2)
        self.assertEqual(projected["unattempted"], 4)
        self.assertEqual(projected["omitted_sources"] + len(projected["sources"]), 6)
        self.assertFalse(projection.payload["workflow_execution"]["completion_established"])

    def test_failed_retry_is_retained_but_successful_recovery_changes_url_coverage(self):
        self.setup_sources()
        self.fetch("bad", self.urls[0], succeeded=False, status="network_failure")
        self.assertEqual(self.coverage()["failed"], 1)
        self.adapter.consume_raw_event(event("item/tool/call", turnId="turn2", callId="good",
                                            tool="web_fetch", arguments={"url": self.urls[0]}))
        self.assertEqual(self.coverage()["pending"], 1)
        self.fetch("good", self.urls[0])
        self.assertEqual(self.coverage()["fetched"], 1)
        self.assertEqual(self.coverage()["failed"], 0)
        self.assertEqual(len(self.coverage()["sources"][0]["fetch_attempts"]), 2)
        self.fetch("later_failure", self.urls[0], succeeded=False, status="http_failure")
        self.assertEqual(self.coverage()["fetched"], 1)
        self.assertEqual(len(self.coverage()["sources"][0]["fetch_attempts"]), 3)

    def test_duplicate_results_and_repeated_calls_are_not_independent_sources(self):
        self.setup_sources()
        payload = self.fetch("read1", self.urls[0])
        raw = result_event(payload, raw=True)
        raw["params"]["turnId"] = "turn2"
        self.adapter.consume_raw_event(raw)
        self.fetch("read2", self.urls[0])
        self.assertEqual(self.coverage()["fetched"], 1)
        self.assertEqual(len(self.coverage()["sources"][0]["fetch_attempts"]), 2)
        payload = output("search2", eligibility="relevant")
        payload["data"]["citable_results"] = [{"url": self.urls[0], "title": "Repeated candidate"}]
        raw = result_event(payload)
        raw["params"]["turnId"] = "turn2"
        self.adapter.consume_raw_event(raw)
        self.assertEqual(self.coverage()["discovered"], 6)
        self.assertEqual(len(self.coverage()["sources"][0]["discovered_by"]), 2)

    def test_model_claim_and_guessed_url_do_not_expand_discovery_inventory(self):
        self.setup_sources()
        self.adapter.consume_raw_event(event("item/completed", turnId="turn2", item={
            "type": "agentMessage", "id": "claim", "text": "All six pages were read, including Wikipedia."}))
        self.assertEqual(self.coverage()["fetched"], 0)
        self.fetch("guess", "https://example.test/not-a-search-candidate")
        coverage = self.coverage()
        self.assertEqual(coverage["discovered"], 6)
        self.assertEqual(coverage["fetched"], 0)
        self.assertEqual(len(coverage["other_fetches"]), 1)

    def test_rejected_attempt_and_missing_outcome_are_not_successful_fetches(self):
        self.setup_sources()
        self.fetch("rejected", self.urls[0], succeeded=False, status="validation_failed")
        self.adapter.consume_raw_event(event("item/tool/call", turnId="turn2", callId="missing",
                                            tool="web_fetch", arguments={"url": self.urls[1]}))
        self.assertEqual(self.coverage()["pending"], 1)
        self.finish("turn2")
        self.assertEqual(self.coverage()["fetched"], 0)
        self.assertEqual(self.coverage()["failed"], 2)

    def test_low_relevance_results_are_not_eligible_discovery_sources(self):
        self.setup_sources()
        payload = output("irrelevant", eligibility="low_relevance")
        payload["data"]["citable_results"] = [{"url": "https://example.test/irrelevant"}]
        raw = result_event(payload)
        raw["params"]["turnId"] = "turn2"
        self.adapter.consume_raw_event(raw)
        self.assertEqual(self.coverage()["discovered"], 6)

    def test_execution_success_without_available_page_is_not_a_pending_or_successful_fetch(self):
        self.setup_sources()
        self.adapter.consume_raw_event(event("item/tool/call", turnId="turn2", callId="no_page",
                                            tool="web_fetch", arguments={"url": self.urls[0]}))
        payload = output("no_page", succeeded=True)
        payload.update(capability="web.fetch", tool="web_fetch")
        payload["data"].update(execution_succeeded=True, result_available=False)
        raw = result_event(payload)
        raw["params"]["turnId"] = "turn2"
        self.adapter.consume_raw_event(raw)
        coverage = self.coverage()
        self.assertEqual((coverage["fetched"], coverage["failed"], coverage["pending"]), (0, 1, 0))
        step = self.adapter.snapshot("thread")["workflow_continuity"]["attempts"][-1]
        self.assertTrue(step["action"]["outcome"]["execution_succeeded"])
        self.assertFalse(step["action"]["outcome"]["result_available"])

    def test_action_bearing_request_survives_non_action_followups_without_authority(self):
        self.setup_sources()
        self.fetch("read1", self.urls[0])
        self.finish("turn2")
        self.adapter.prepare_turn("thread", "What results did we get?", turn_id="turn3")
        self.finish("turn3")
        projection = self.adapter.prepare_turn("thread", "How does this help the project?", turn_id="turn4")
        context = turn_context_payload([], semantic_projection=projection.payload)
        interpretations = json.loads(context["uaea.semantic_interpretations"]["value"])
        self.assertIn("Explore these six links", interpretations["workflow_continuation"]["last_action_request"])
        authority = json.loads(context["uaea.semantic_state_projection"]["value"])
        self.assertNotIn("last_action_request", context["uaea.semantic_state_projection"]["value"])
        self.assertEqual(context["uaea.semantic_interpretations"]["kind"], "untrusted")
        self.assertEqual(authority["constraints"], ["web.provider=google", "web.fallback=forbidden"])
        request = self.adapter.snapshot("thread")["workflow_continuity"]["last_action_request"]
        self.assertEqual(request["call_id"], "read1")
        self.assertTrue(request["input_id"])

    def test_dense_projection_keeps_counts_and_never_truncates_urls(self):
        self.setup_sources(dense=True, urls=[f"https://example.test/{i}/" + "long" * 200 for i in range(6)])
        self.fetch("read1", self.urls[0])
        self.finish("turn2")
        before = self.coverage()
        projection = self.adapter.prepare_turn("thread", "What is still pending?", turn_id="turn3")
        coverage = projection.payload["workflow_execution"]["source_coverage"]
        self.assertEqual(coverage["discovered"], 6)
        self.assertEqual(coverage["fetched"], 1)
        self.assertEqual(coverage["unattempted"], 5)
        self.assertTrue(all(source["url"] in self.urls for source in coverage["sources"]))
        self.assertEqual(coverage["omitted_sources"] + len(coverage["sources"]), 6)
        context = turn_context_payload([], semantic_projection=projection.payload)
        self.assertLessEqual(sum(len(context[k]["value"]) for k in
                                 ("uaea.semantic_state_projection", "uaea.semantic_interpretations")), 2400)
        self.assertEqual(before, self.coverage())
        self.assertEqual(len(projection.payload["constraints"]), 4)

    def test_thread_and_task_inventory_isolation(self):
        self.setup_sources()
        self.adapter.prepare_turn("other", "Unrelated research")
        self.assertEqual(self.adapter.snapshot("other")["workflow_continuity"]["source_coverage"]["discovered"], 0)
        self.adapter.prepare_turn("thread", "新任务：研究编译器", turn_id="turn3")
        self.assertEqual(self.coverage()["discovered"], 0)

    def test_failure_counts_with_native_ids_four_constraints_and_sticky_request_fit(self):
        thread = "01a14ce0-cf12-7481-b378-2690d0d75d2f"
        t1 = "01a14ce0-1111-7481-b378-2690d0d75d2f"
        t2, t3 = t1.replace("1111", "2222"), t1.replace("1111", "3333")
        for status in ("network_failure", "validation_failed", "timeout"):
            with self.subTest(status=status):
                adapter = HarnessSemanticStateAdapter()

                def finish(turn):
                    adapter.consume_raw_event({"method": "turn/completed", "params": {
                        "threadId": thread, "turn": {"id": turn, "status": "completed"}}})

                def receive(payload, turn):
                    raw = result_event(payload)
                    raw["params"].update(threadId=thread, turnId=turn)
                    adapter.consume_raw_event(raw)

                adapter.prepare_turn(thread, "Only use Google. Do not use Bing. Do not use DuckDuckGo. No fallback. Research OpenAI Agents SDK and Model Context Protocol.", turn_id=t1)
                payload = output("search_native_id", eligibility="relevant")
                payload["data"]["citable_results"] = [{"url": f"https://example.test/{i}"} for i in range(6)]
                receive(payload, t1)
                finish(t1)
                adapter.prepare_turn(thread, "Explore all discovered sources and compare their mechanisms for local agent runtimes, their lifecycle and context interfaces, and any unverified design claims.", turn_id=t2)
                adapter.consume_raw_event(event("item/tool/call", threadId=thread, turnId=t2,
                                                callId="call_1234567890123456", tool="web_fetch",
                                                arguments={"url": "https://example.test/0"}))
                payload = output("call_1234567890123456", succeeded=False, status=status)
                payload.update(capability="web.fetch", tool="web_fetch")
                payload["data"]["http_attempted"] = status != "validation_failed"
                receive(payload, t2)
                finish(t2)
                adapter.prepare_turn(thread, "What did we obtain?", turn_id=t3)
                finish(t3)
                projection = adapter.prepare_turn(thread, "How does that advance our current project?")
                context = turn_context_payload([], semantic_projection=projection.payload)
                self.assertLessEqual(sum(len(context[k]["value"]) for k in
                                         ("uaea.semantic_state_projection", "uaea.semantic_interpretations")), 2400)
                coverage = projection.payload["workflow_execution"]["source_coverage"]
                self.assertEqual((coverage["discovered"], coverage["fetched"], coverage["failed"]), (6, 0, 1))
                self.assertEqual(len(projection.payload["constraints"]), 4)
                self.assertIn("Explore all discovered sources", projection.payload["workflow_continuation"]["last_action_request"])
                self.assertEqual(projection.payload["workflow_execution"]["last_attempt"]["execution_status"], status)


if __name__ == "__main__":
    unittest.main()
