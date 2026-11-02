from __future__ import annotations
import json
import unittest
from harness.codex_dynamic_tools import _bounded_json_text, _model_visible_tool_data
from phase2.web_adapter import _parse_google_search_results
from tests import test_google_serpapi_backend as google_fixture


class SearchTransportParsingTests(unittest.TestCase):
    def test_relative_identity_restored_without_decoding_opaque_target(self):
        d = []
        r = _parse_google_search_results({"organic_results": [
            {"title": "Source", "link": "/goto?url=opaque", "snippet": "original"}]}, diagnostics=d)
        self.assertEqual(r[0].url, "https://www.google.com/goto?url=opaque")
        self.assertEqual(r[0].source_link, "/goto?url=opaque")
        self.assertEqual(r[0].to_dict()["destination_identity"], "unresolved")
        self.assertEqual(d[0]["reason"], "same_origin_reference")

    def test_malformed_or_ambiguous_urls_are_diagnosed_not_guessed(self):
        links = ["//evil.test/x", "javascript:bad", "file:///tmp/a", "/\\evil.test/x",
                 "https://user:password@example.test", "https://[bad", "https://example.test:bad",
                 " /goto?url=x", "/goto?\nurl=x", "goto?url=x"]
        d = []
        self.assertEqual(_parse_google_search_results({"organic_results": [
            {"title": "bad", "link": u} for u in links]}, diagnostics=d), [])
        self.assertEqual(len(d), len(links))
        self.assertTrue(all(x["status"] == "rejected" for x in d))


class SearchTransportPipelineTests(unittest.TestCase):
    setUp = google_fixture.GoogleSerpApiBackendTests.setUp
    call = google_fixture.GoogleSerpApiBackendTests.call

    def test_all_stages_and_bounded_visible_count_are_distinct(self):
        p = google_fixture.serp_payload()
        p["organic_results"] = [
            {"title": f"Source {i}", "link": f"/goto?url=opaque-{i}", "snippet": "source snippet"} for i in range(8)]
        r = self.call(p, arguments={"query": "research", "provider": "google", "allow_fallback": False, "max_results": 5})
        self.assertEqual(r.data["search_transport"]["backend_raw"], 8)
        self.assertEqual(r.data["search_transport"]["parsed"], 8)
        self.assertEqual(r.data["search_transport"]["candidate_projected"], 5)
        payload = {"ok": True, "capability": "web.search", "tool": "web_search",
                   "status": "success", "message": r.message, "data": _model_visible_tool_data("web.search", r.data)}
        projected = json.loads(_bounded_json_text(payload, 4000))["data"]
        self.assertEqual(projected["search_transport"]["model_visible"], len(projected["citable_results"]))
        self.assertGreater(projected["search_transport"]["model_visible"], 0)
        self.assertNotIn("diagnostics", projected["search_transport"])
        self.assertEqual(projected["evidence_counts"]["raw"], 8)
        self.assertEqual(r.data["search_transport"]["model_visible"], 5)

    def test_parse_failure_is_not_provider_empty(self):
        p = google_fixture.serp_payload()
        p["organic_results"] = [{"title": "unsafe", "link": "javascript:bad"}]
        r = self.call(p)
        self.assertTrue(r.ok)
        self.assertEqual(r.data["search_transport"]["backend_raw"], 1)
        self.assertEqual(r.data["search_transport"]["parsed"], 0)
        self.assertEqual(len(r.data["citable_results"]), 0)
        self.assertIn("not proof", r.data["bounded_evidence_block"])
