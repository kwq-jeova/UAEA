from copy import deepcopy
import hashlib
import json
import unittest
from harness.codex_dynamic_tools import _bounded_json_text

class FetchEvidenceBudgetTests(unittest.TestCase):
    def payload(self, text="实际摘录内容"*180):
        return {"ok":True,"capability":"web.fetch","tool":"web_fetch","status":"success",
                "identity":{"call_id":"call","thread_id":"thread"},"message":"Fetched",
                "data":{"execution_succeeded":True,"execution_status":"success","http_attempted":True,
                        "http_status":200,"url":"https://example.org/page","access_event_id":"evt",
                        "content_sha256":"raw-source-hash",
                        "source_excerpt":{"text":text,"text_sha256":hashlib.sha256(text.encode()).hexdigest(),
                                          "scope":"projected_page_excerpt"},
                        "temporal_facts":{"accessed_at":"2026-11-02","published_at":None,
                                          "content_period":{"value":None,"status":"unknown"}},
                        "projection_metrics":{"source_chars":19000,"projected_chars":len(text)},
                        "execution_decision":{"allowed":True,"reason":"allowed","authorization":{},
                            "effective_parameters":{"url":"https://example.org/page"},
                            "parameter_sources":{"url":{"basis":"action_proposal"}},
                            "compatibility_guard":{"diagnostic":"audit "*2000}}}}
    def project(self,p,budget=5000):
        wire=_bounded_json_text(p,budget)
        self.assertLessEqual(len(wire),budget)
        return json.loads(wire)
    def test_shared_audit_does_not_starve_full_existing_excerpt(self):
        p=self.payload();before=deepcopy(p);d=self.project(p)["data"]
        self.assertEqual(d["source_excerpt"],p["data"]["source_excerpt"])
        self.assertEqual(d["evidence_extent"]["source_text_chars"],19000)
        self.assertEqual(d["execution_decision"]["full_decision_sha256"],
            hashlib.sha256(json.dumps(p["data"]["execution_decision"],ensure_ascii=False,sort_keys=True).encode()).hexdigest())
        self.assertEqual(d["execution_decision"]["authorization"],{})
        self.assertEqual(d["temporal_facts"],p["data"]["temporal_facts"])
        self.assertEqual(p,before)
    def test_limited_budget_supplies_exact_prefix_and_hash(self):
        p=self.payload("Evidence source "*1000);d=self.project(p)["data"];e=d["source_excerpt"]
        self.assertGreater(len(e["text"]),80)
        self.assertTrue(p["data"]["source_excerpt"]["text"].startswith(e["text"]))
        self.assertEqual(e["text_sha256"],hashlib.sha256(e["text"].encode()).hexdigest())
        self.assertEqual(e["projection"]["acquired_chars"],len(p["data"]["source_excerpt"]["text"]))
        self.assertEqual(e["projection"]["supplied_chars"],len(e["text"]))
        self.assertTrue(e["projection"]["truncated"])
    def test_source_declared_date_is_retained_when_text_is_shortened(self):
        p=self.payload("Source evidence "*900)
        temporal={"accessed_at":"2026-11-02T03:00:00Z","published_at":"2026-06-06",
                  "publication_status":"source_declared","publication_claims":[
                    {"field":"jsonld.datePublished","value":"2026-06-06","source_event_id":"evt",
                     "content_sha256":"raw-source-hash"}],
                  "content_period":{"value":None,"status":"unknown"}}
        p["data"]["temporal_facts"]=temporal
        d=self.project(p)["data"]
        self.assertEqual(d["temporal_facts"],temporal)
        self.assertTrue(d["source_excerpt"]["projection"]["truncated"])
        self.assertNotEqual(d["temporal_facts"]["published_at"],"2026-11-02")
    def test_very_small_budget_omits_excerpt_explicitly(self):
        p=self.payload("Long source "*300)
        p["data"].pop("execution_decision")
        d=self.project(p,900)["data"]
        self.assertNotIn("source_excerpt",d)
        self.assertEqual(d["source_excerpt_status"],"omitted_for_budget")
        self.assertTrue(d["execution_succeeded"])
        self.assertEqual(d["content_sha256"],"raw-source-hash")
    def test_metadata_only_budget_refuses_instead_of_losing_authority(self):
        with self.assertRaises(ValueError):self.project(self.payload(),100)
    def test_bad_acquired_hash_not_rehashed_into_evidence(self):
        p=self.payload();p["data"]["source_excerpt"]["text_sha256"]="bad"
        d=self.project(p)["data"]
        self.assertNotIn("source_excerpt",d)
        self.assertEqual(d["source_excerpt_status"],"invalid_acquired_excerpt_hash")
    def test_failure_remains_failure_without_successful_excerpt(self):
        p=self.payload();p["ok"]=False;p["status"]="failed";p["data"].update(
            execution_succeeded=False,execution_status="failed",reason="TLS verification failed")
        p["data"].pop("source_excerpt");p["data"].pop("execution_decision")
        d=self.project(p)
        self.assertFalse(d["ok"]);self.assertFalse(d["data"]["execution_succeeded"])
        self.assertNotIn("source_excerpt",d["data"])
    def test_decision_conflict_not_converted_to_permission(self):
        p=self.payload();p["data"]["execution_decision"].update(allowed=False,reason="conflict",retryable=False)
        d=self.project(p)["data"]["execution_decision"]
        self.assertFalse(d["allowed"]);self.assertEqual(d["reason"],"conflict")
    def test_small_untruncated_payload_keeps_existing_shape(self):
        p=self.payload("short");p["data"].pop("execution_decision")
        self.assertEqual(self.project(p),p)

if __name__ == "__main__":unittest.main()
