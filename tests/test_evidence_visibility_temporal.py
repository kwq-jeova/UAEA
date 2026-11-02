from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from phase2.evidence_boundary import candidate_view, temporal_facts
from phase2.web_capability import _search_contract
from harness.codex_dynamic_tools import _bounded_json_text, _model_visible_tool_data
from harness.io_contract import turn_context_payload
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from harness.request_continuity import retained_request_view


def search_data(status="uncertain"):
    results = [{"title": f"Source {i}", "url": f"https://example.test/{i}",
                "snippet": "A source-provided search snippet."} for i in range(3)]
    data = {"access_event_id": "observed-search", "raw_search_result_count": 9,
            "evidence_relevance": {"status": status},
            "execution_succeeded": True, "execution_status": "success",
            "actual_provider": "google", "search_query": "research",
            "evidence_reference": {"source_kind": "web_access_event", "source_id": "observed-search"}}
    data.update(candidate_view(data, results))
    data["search_contract"] = _search_contract(data)
    return data


class EvidenceBoundaryTests(unittest.TestCase):
    def test_weak_lexical_status_cannot_veto_real_candidate_visibility(self):
        for status in ("low_relevance", "uncertain", "relevant"):
            with self.subTest(status=status):
                data = search_data(status)
                self.assertEqual(data["evidence_status"], "candidates_available")
                self.assertEqual(data["evidence_relevance"]["status"], status)
                self.assertFalse(data["evidence_relevance"]["semantic_authority"])
                self.assertEqual(len(data["candidate_evidence_results"]), 3)
                self.assertEqual(data["evidence_counts"], {
                    "raw": 9, "retained": 3, "visible": 3,
                    "discovery_citable": 3, "page_content_acquired": 0})
                for i, item in enumerate(data["citable_results"]):
                    self.assertEqual(item["source_event_id"], "observed-search")
                    self.assertEqual(item["url"], f"https://example.test/{i}")
                    self.assertEqual(item["citation_scope"], "search_result_only")
                    self.assertEqual(item["semantic_relevance"], "unassessed")
                    self.assertEqual(item["constraints_satisfied"], "not_established")
                    self.assertFalse(item["page_acquired"])

    def test_bounded_harness_projection_preserves_scope_identities_and_actual_counts(self):
        for status in ("low_relevance", "uncertain"):
            data = search_data(status)
            original = deepcopy(data)
            projected = _model_visible_tool_data("web.search", data)
            payload = {"ok": True, "capability": "web.search", "tool": "web_search",
                       "status": "success", "message": "Search executed", "data": projected}
            for budget in (4000, 3000):
                out = json.loads(_bounded_json_text(payload, budget))["data"]
                self.assertGreater(len(out["citable_results"]), 0)
                self.assertEqual(out["evidence_counts"]["raw"], 9)
                self.assertEqual(out["evidence_counts"]["retained"], 3)
                self.assertEqual(out["evidence_counts"]["visible"], len(out["citable_results"]))
                self.assertEqual(out["search_contract"]["semantic_relevance"], "unassessed")
                for item in out["citable_results"]:
                    self.assertIn(item["source_id"],
                                  [x["source_id"] for x in original["candidate_evidence_results"]])
                    self.assertEqual(item["citation_scope"], "search_result_only")
            self.assertEqual(data, original)

    def test_versioned_boundary_is_not_vetoed_by_legacy_lexical_label(self):
        data = search_data("low_relevance")
        data["search_contract"]["candidate_status"] = "low_relevance"
        payload = {"ok": True, "capability": "web.search", "tool": "web_search",
                   "status": "success", "message": "Search executed", "data": data}
        out = json.loads(_bounded_json_text(payload, 4000))["data"]
        self.assertEqual(len(out["citable_results"]), 3)
        self.assertEqual(out["search_contract"]["semantic_relevance"], "unassessed")

    def test_projection_limit_does_not_claim_empty_search(self):
        data = search_data()
        for item in data["citable_results"]:
            item["url"] += "x" * 6000
        payload = {"ok": True, "capability": "web.search", "tool": "web_search",
                   "status": "success", "message": "Search executed", "data": data}
        out = json.loads(_bounded_json_text(payload, 3000))["data"]
        self.assertEqual(out["evidence_counts"]["raw"], 9)
        self.assertEqual(out["evidence_counts"]["retained"], 3)
        self.assertEqual(out["evidence_counts"]["visible"], 0)
        self.assertEqual(out["projection_status"], "identity_exceeds_budget")

    def temporal(self, html):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "page.html"
            path.write_text(html)
            return temporal_facts({
                "access_event_id": "fetch", "accessed_at": "2026-10-29T01:07:34Z",
                "access_status": "fetched", "source_type": "web_page",
                "content_ref": str(path), "content_sha256": "original-hash",
                # A model-supplied interpretation must not overwrite original source facts.
                "content_period": "2026 Q3",
            })

    def test_published_time_is_source_declared_and_content_period_remains_unknown(self):
        result = self.temporal(
            '<meta property="article:published_time" content="2025-10-10T13:50:18+00:00">'
            '<script type="application/ld+json">{"@type":"NewsArticle",'
            '"datePublished":"2025-10-10T13:50:18Z"}</script><p>Q3 2025 investor letter.</p>')
        self.assertEqual(result["accessed_at"], "2026-10-29T01:07:34Z")
        self.assertTrue(result["published_at"].startswith("2025-10-10"))
        self.assertEqual(result["publication_status"], "source_declared")
        self.assertEqual(result["content_period"]["status"], "unknown")
        self.assertIsNone(result["content_period"]["value"])
        self.assertTrue(all(x["content_sha256"] == "original-hash"
                            for x in result["publication_claims"]))

    def test_no_publication_metadata_does_not_infer_from_clock_or_body(self):
        result = self.temporal("<p>Q3 2025. Published 2025-10-10.</p>")
        self.assertIsNone(result["published_at"])
        self.assertEqual(result["publication_status"], "unknown")
        self.assertIsNone(result["content_period"]["value"])

    def test_conflicting_source_dates_remain_unknown(self):
        result = self.temporal(
            '<script type="application/ld+json">[{"@type":"Article","datePublished":"2025-10-10"},'
            '{"@type":"Article","datePublished":"2026-10-10"}]</script>')
        self.assertIsNone(result["published_at"])
        self.assertEqual(result["publication_status"], "conflicting_source_declarations")

    def test_unrelated_structured_dates_and_malformed_metadata_are_not_facts(self):
        for body in ('{"@type":null,"datePublished":"2026-01-01"}',
                     '{"@type":"Person","datePublished":"2026-01-01"}', 'not JSON'):
            with self.subTest(body=body):
                self.assertIsNone(self.temporal(
                    '<script type="application/ld+json">' + body + '</script>')["published_at"])

    def test_query_rewrite_keeps_original_temporal_input_without_nlu_or_authority_promotion(self):
        semantic = HarnessSemanticStateAdapter()
        for i, text in enumerate([
            "搜索资料", "使用英文查询，时间指定2026年",
            "相关度高的也可以", "分析链接1", "继续", "再比较一下"]):
            semantic.prepare_turn("thread", text, turn_id=str(i))
        retained = semantic.retained_requests("thread")
        self.assertEqual(retained["retained_count"], 6)
        self.assertEqual(retained["omitted_count"], 0)
        self.assertIn("时间指定2026年", json.dumps(retained, ensure_ascii=False))
        payload = turn_context_payload([], retained_requests=retained)
        self.assertEqual(payload["uaea.retained_user_requests"]["kind"], "untrusted")
        state = semantic.snapshot("thread")
        self.assertEqual(state["constraints"], [])
        self.assertFalse(state["workflow_continuity"]["completion_established"])
        self.assertTrue(all(x["status"] == "retained"
                            for x in state["workflow_continuity"]["request_continuity"]["inputs"]))

    def test_context_budget_reports_omissions_without_cancelling_requests(self):
        semantic = HarnessSemanticStateAdapter()
        for i in range(12):
            semantic.prepare_turn("thread", f"Request {i}: " + "原文" * 150, turn_id=str(i))
        state = semantic._state_for("thread")
        view = retained_request_view(state.runtime_objects, state.current_task_id, max_chars=1500)
        self.assertGreater(view["omitted_count"], 0)
        self.assertEqual(view["retained_count"], 12)
        self.assertEqual(len([x for x in state.runtime_objects.objects
                              if x.object_type == "workflow_request_input" and x.status == "retained"]), 12)


if __name__ == "__main__":
    unittest.main()
