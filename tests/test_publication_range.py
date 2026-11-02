from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phase2.web_adapter import WebAdapter, normalize_search_constraints
from phase2.web_capability import WebSearchCapability
from harness.codex_dynamic_tools import _bounded_json_text


class PublicationRangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.adapter = WebAdapter(snapshot_root=self.root / "snapshots")
        self.capability = WebSearchCapability(db_path=self.root / "source.sqlite", adapter=self.adapter)
        self.args = {"query": "Example 2026 Q3 research", "provider": "google", "allow_fallback": False,
                     "published_from": "2026-10-01", "published_to": "2026-10-30"}

    def backend(self, params, **kwargs):
        return {"search_parameters": {"engine": "google", "q": params["q"], **(
                    {"tbs": params["tbs"]} if "tbs" in params else {})},
                "organic_results": [
                    {"title": "Source 2026 Q3", "link": "https://example.test/current",
                     "snippet": "Published research", "date": "1 day ago"},
                    {"title": "Historical comparison", "link": "https://example.test/history",
                     "snippet": "May not meet the requested period", "date": "Oct 30, 2025"}]}

    def test_native_provider_parameter_and_observation_preserve_exact_range_and_echo(self):
        with patch("phase2.web_adapter.google_search", side_effect=self.backend) as backend:
            result = self.capability(self.args, "range")
        self.assertTrue(result.ok)
        sent = backend.call_args.args[0]
        self.assertEqual(sent["tbs"], "cdr:1,cd_min:10/01/2026,cd_max:10/30/2026")
        self.assertEqual(sent["q"], self.args["query"])
        self.assertEqual(result.data["requested_constraints"]["published_from"], "2026-10-01")
        facts = result.data["publication_filter"]
        self.assertEqual(facts["provider_confirmation"], "echo_match")
        self.assertEqual(facts["date_semantics"], "publication_date_only")
        self.assertEqual(facts["content_period_satisfied"], "not_established")
        self.assertTrue(all(x["constraints_satisfied"] == "not_established"
                            for x in result.data["citable_results"]))

    def test_source_date_label_preserved_without_inventing_publication_or_content_period(self):
        with patch("phase2.web_adapter.google_search", side_effect=self.backend):
            result = self.capability(self.args, "labels")
        candidates = result.data["citable_results"]
        self.assertEqual(candidates[0]["source_date_text"], "1 day ago")
        self.assertEqual(candidates[1]["source_date_text"], "Oct 30, 2025")
        self.assertEqual(candidates[0]["source_date_kind"], "search_provider_label")
        self.assertEqual(candidates[0]["source_date_anchor"], result.data["temporal_facts"]["accessed_at"])
        self.assertIsNone(result.data["temporal_facts"]["published_at"])
        self.assertIsNone(result.data["temporal_facts"]["content_period"]["value"])

    def test_projection_retains_date_labels_and_filter_provenance(self):
        with patch("phase2.web_adapter.google_search", side_effect=self.backend):
            result = self.capability(self.args, "projection")
        payload = {"ok": True, "capability": "web.search", "tool": "web_search", "status": "success",
                   "message": result.message, "data": result.data}
        original = json.dumps(result.data)
        projected = json.loads(_bounded_json_text(payload, 5000))["data"]
        self.assertEqual(projected["publication_filter"]["provider_confirmation"], "echo_match")
        self.assertEqual(projected["citable_results"][0]["source_date_text"], "1 day ago")
        self.assertEqual(json.dumps(result.data), original)

    def test_invalid_partial_reversed_and_non_iso_ranges_fail_before_http(self):
        for changes in [
            {"published_to": ""}, {"published_from": ""}, {"published_from": "2026-11-01"},
            {"published_from": "2026-02-30"}, {"published_from": "2026/10/01"},
            {"freshness": "week"}, {"provider": "bing"}, {"allow_fallback": True}]:
            with self.subTest(changes=changes), patch("phase2.web_adapter.google_search") as backend, \
                    patch.object(self.adapter, "_http_get") as http:
                result = self.capability({**self.args, **changes}, "invalid")
                self.assertFalse(result.ok)
                self.assertFalse(result.data["http_attempted"])
                backend.assert_not_called()
                http.assert_not_called()

    def test_missing_provider_does_not_silently_drop_the_filter(self):
        args = {**self.args}
        args.pop("provider")
        with patch("phase2.web_adapter.google_search") as backend:
            self.assertFalse(self.capability(args, "unknown provider").ok)
            backend.assert_not_called()

    def test_provider_not_echoing_the_filter_is_not_reported_as_confirmation(self):
        def no_echo(params, **kwargs):
            payload = self.backend(params, **kwargs)
            payload["search_parameters"].pop("tbs")
            return payload
        with patch("phase2.web_adapter.google_search", side_effect=no_echo):
            result = self.capability(self.args, "no echo")
        self.assertEqual(result.data["publication_filter"]["provider_confirmation"], "not_confirmed")
        self.assertIsNone(result.data["publication_filter"]["provider_reported_value"])

    def test_search_without_absolute_range_keeps_existing_parameter_behavior(self):
        args = {key: value for key, value in self.args.items() if not key.startswith("published_")}
        with patch("phase2.web_adapter.google_search", side_effect=self.backend) as backend:
            self.assertTrue(self.capability(args, "no range").ok)
        self.assertNotIn("tbs", backend.call_args.args[0])
        self.assertEqual(normalize_search_constraints(args).published_from, "")


if __name__ == "__main__":
    unittest.main()
