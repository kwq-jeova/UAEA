from __future__ import annotations
from copy import deepcopy
import json
import unittest

from harness.evidence_provenance import (digest, ground_claim, source_inventory,
                                        provenance_snapshot, record_model_output)
from harness.event_normalizer import TrajectoryEvent, AGENT_OUTPUT
from harness.io_contract import turn_context_payload
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from tests.test_harness_workflow_continuity import event, output, result_event


class EvidenceProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.adapter = HarnessSemanticStateAdapter()
        self.adapter.prepare_turn("thread", "Research this topic", turn_id="turn1")
        self.state = self.adapter._state_for("thread")
        self.url = "https://example.test/report"

    def search(self):
        self.adapter.consume_raw_event(event("item/tool/call", callId="s", tool="web_search", arguments={"query": "research"}))
        p = output("s", eligibility="candidates_available")
        p["data"].update(access_event_id="search-event", citable_results=[
            {"url": self.url, "title": "Report", "source_id": "candidate-1"}])
        self.adapter.consume_raw_event(result_event(p))

    def fetch(self, *, malformed_excerpt=False, capability="web.fetch"):
        self.adapter.consume_raw_event(event("item/tool/call", callId="f", tool="web_fetch", arguments={"url": self.url}))
        p = output("f")
        p.update(capability=capability, tool="web_fetch")
        p["data"] = {"execution_succeeded": True, "result_available": True,
                     "url": self.url, "access_event_id": "page-event", "content_sha256": "body-hash",
                     "source_excerpt": {"source_event_id": "page-event", "content_sha256": "body-hash",
                        "text": "Q3 2025. Revenue declined.", "text_sha256": digest(
                            "original" if malformed_excerpt else "Q3 2025. Revenue declined.")}}
        self.adapter.consume_raw_event(result_event(p))

    def sources(self):
        return source_inventory(self.state.runtime_objects.step_runs)

    def claim(self, **kwargs):
        return ground_claim(self.sources(), text="model claim", **kwargs)

    def test_search_is_discovery_not_reading_or_semantic_support(self):
        self.search()
        s = self.sources()[0]
        self.assertTrue(s["execution_grounded"])
        self.assertEqual(s["scope"], "search_discovery")
        self.assertFalse(s["page_fetch_observed"])
        c = self.claim(urls=[self.url], execution_claim={"operation": "web.fetch", "url": self.url})
        self.assertEqual(c["source_linked"]["status"], "linked")
        self.assertEqual(c["execution_grounded"]["status"], "not_established")
        self.assertTrue(c["content_supported"].startswith("not_assessed"))

    def test_claiming_reading_does_not_create_fetch_fact(self):
        self.search()
        before = deepcopy(self.sources())
        self.adapter.consume_raw_event(event("item/completed", item={
            "type": "agentMessage", "id": "claim", "text": "I read everything at " + self.url}))
        self.assertEqual(before, self.sources())
        snapshot = self.adapter.snapshot("thread")
        self.assertEqual(snapshot["evidence_provenance"]["fetch_observations"], 0)
        self.assertFalse(snapshot["workflow_continuity"]["completion_established"])
        self.assertFalse(provenance_snapshot(self.state.runtime_objects, self.state.current_task_id)[
            "model_outputs"][0]["metadata"]["grounding_at_output"]["source_evidence"])

    def test_fetch_and_wrong_semantic_conclusion_remain_separate(self):
        self.search()
        self.fetch()
        c = self.claim(source_ids=["page-event"], quote="Q3 2025.",
                       execution_claim={"operation": "web.fetch", "url": self.url})
        self.assertEqual(c["execution_grounded"]["status"], "supported")
        self.assertEqual(c["quote_match"]["status"], "exact_in_supplied_excerpt")
        self.assertEqual(c["content_supported"], "not_assessed_requires_semantic_judgment")
        self.assertFalse(c["workflow_completion_established"])

    def test_quote_not_found_and_malformed_projection_do_not_validate(self):
        self.fetch(malformed_excerpt=True)
        self.assertFalse(self.sources()[0]["excerpt_supplied"])
        self.assertEqual(self.claim(source_ids=["page-event"], quote="Q3 2025.")[
            "quote_match"]["status"], "not_found_in_supplied_excerpt")

    def test_historical_model_claims_never_become_sources_or_gain_authority(self):
        self.search()
        for turn in ["turn1", "turn2"]:
            record_model_output(self.state.runtime_objects, self.state.current_task_id,
                text="I established the cause. " + self.url, event_id=turn, turn_id=turn)
        c = self.claim(prior_model_output_ids=["prior-output"])
        self.assertFalse(c["source_evidence"])
        self.assertFalse(c["history_confers_source_authority"])
        self.assertEqual(len(self.sources()), 1)

    def test_insufficient_evidence_answer_preserves_unfinished_workflow(self):
        self.adapter.consume_raw_event(event("item/completed", item={
            "type": "agentMessage", "id": "honest", "text": "I have not fetched a source; evidence is insufficient."}))
        self.adapter.consume_raw_event(event("turn/completed", turn={"id": "turn1", "status": "completed"}))
        w = self.adapter.snapshot("thread")["workflow_continuity"]
        self.assertEqual(w["status"], "active")
        self.assertFalse(w["completion_established"])
        self.assertEqual(w["attempts"], [])

    def test_later_fetch_does_not_retroactively_ground_earlier_output(self):
        self.search()
        r = record_model_output(self.state.runtime_objects, self.state.current_task_id,
            text=self.url, event_id="a", turn_id="turn1")
        self.fetch()
        self.assertFalse(r["metadata"]["grounding_at_output"]["linked_source_facts"][0]["page_fetch_observed"])

    def test_url_or_id_alone_cannot_prove_content_support(self):
        self.search()
        c = self.claim(source_ids=["nonexistent"], urls=["https://unknown.test"])
        self.assertEqual(c["source_linked"]["status"], "not_linked")
        self.assertEqual(c["source_linked"]["unresolved_source_ids"], ["nonexistent"])
        self.assertEqual(c["execution_grounded"]["status"], "not_asserted")

    def test_non_web_capability_uses_same_source_and_quote_boundary(self):
        self.fetch(capability="document.read_section")
        s = self.sources()[0]
        self.assertEqual(s["scope"], "capability_result")
        self.assertFalse(s["page_fetch_observed"])
        self.assertEqual(self.claim(execution_claim={
            "operation": "document.read_section", "source_id": "page-event"})[
                "execution_grounded"]["status"], "supported")
        self.assertEqual(self.claim(source_ids=["page-event"], quote="Q3 2025.")[
            "quote_match"]["status"], "exact_in_supplied_excerpt")

    def test_codex_and_simulated_x_normalized_output_produce_equivalent_facts(self):
        from types import SimpleNamespace
        self.search()
        self.fetch()
        # Simulated X protocol has neither Codex event names nor contentItems.
        x_wire = {"results": [
            {"ability": step.capability, "receipt": deepcopy(step.action["outcome"]),
             "request_key": step.action["harness"]["call_id"],
             "round": step.action["harness"]["turn_id"]}
            for step in self.state.runtime_objects.step_runs]}
        normalized = [SimpleNamespace(capability=r["ability"], action={
            "outcome": r["receipt"], "harness": {"call_id": r["request_key"], "turn_id": r["round"]}})
            for r in x_wire["results"]]
        self.assertEqual(self.sources(), source_inventory(normalized))
        args = dict(text="The source says Q3 2026.", source_ids=["page-event"],
                    execution_claim={"operation": "web.fetch", "url": self.url}, quote="Q3 2025.")
        self.assertEqual(ground_claim(self.sources(), **args),
                         ground_claim(source_inventory(normalized), **args))
        # Both wrappers still leave semantic entailment unassessed.
        self.assertTrue(ground_claim(source_inventory(normalized), **args)[
            "content_supported"].startswith("not_assessed"))

    def test_feedback_carries_only_facts_not_historical_generated_text(self):
        self.adapter.consume_raw_event(event("item/completed", item={
            "type": "agentMessage", "id": "a", "text": "UNTRUSTED INVENTED CAUSE"}))
        summary = self.adapter.snapshot("thread")["evidence_provenance"]
        context = turn_context_payload([], evidence_provenance=summary)
        v = context["uaea.evidence_provenance"]
        self.assertEqual(v["kind"], "application")
        self.assertNotIn("UNTRUSTED", v["value"])
        self.assertFalse(json.loads(v["value"])["model_output_is_source_evidence"])

    def test_streaming_deltas_and_empty_start_are_not_duplicate_claims(self):
        for text in ["I ", "read ", "everything."]:
            self.adapter.consume_event(TrajectoryEvent(sequence=1, event_type=AGENT_OUTPUT,
                thread_id="thread", turn_id="turn1", payload={"delta": text, "is_delta": True}))
        self.adapter.consume_event(TrajectoryEvent(sequence=2, event_type=AGENT_OUTPUT,
            thread_id="thread", turn_id="turn1", payload={"text": ""}))
        self.adapter.consume_raw_event(event("item/completed", item={
            "type": "agentMessage", "id": "a", "text": "I read everything."}))
        self.assertEqual(self.adapter.snapshot("thread")["evidence_provenance"]["model_outputs"], 1)
