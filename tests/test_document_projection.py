import copy
import hashlib
import json
import unittest
from harness.codex_dynamic_tools import _bounded_json_text


class DocumentProjectionTests(unittest.TestCase):
    def payload(self, content, capability="document.read_section", catalog=None):
        h = hashlib.sha256(content.encode()).hexdigest()
        return {"ok": True, "capability": capability, "tool": "read_section", "status": "success",
                "message": "Read selected source",
                "identity": {"thread_id": "t", "turn_id": "u", "call_id": "c", "observation_id": "o"},
                "data": {"path": "/readonly/source.md", "resolved_path": "/readonly/source.md",
                         "content": content, "content_hash": h, "source_hash": "a" * 64,
                         "size_chars": len(content), "section_index": 2, "section": "Financial results",
                         "line_start": 1, "line_end": content.count("\n") + 1,
                         "section_catalog": catalog or []}}

    def project(self, p, budget=12000):
        text = _bounded_json_text(p, budget)
        self.assertLessEqual(len(text), budget)
        self.assertLessEqual(len(text.encode("utf-8")), budget)
        return json.loads(text)

    def test_full_financial_table_and_basis_survive_oversized_catalog(self):
        content = "USD millions; quarter ended 2026-07-26; GAAP\n| Metric | Current | Prior |\n| Revenue | 96,221 | 46,743 |\n"
        catalog = [{"section_index": i, "heading": "Unrelated chapter " + str(i),
                    "line_start": i * 10} for i in range(1, 1000)]
        p = self.payload(content, catalog=catalog)
        before = copy.deepcopy(p)
        q = self.project(p)
        self.assertEqual(q["data"]["content"], content)
        self.assertTrue(q["data"]["document_projection"]["content_complete"])
        self.assertGreater(q["data"]["document_projection"]["catalog_omitted"], 0)
        self.assertEqual(q["identity"], p["identity"])
        self.assertEqual(p, before)

    def test_large_selected_catalog_cannot_evict_full_body(self):
        content = "complete row line\n" * 110
        p = self.payload(content, catalog=[{"section_index": 2, "heading": "h" * 2200, "line_start": 1}])
        q = self.project(p, 4000)
        self.assertEqual(q["data"]["content"], content)
        self.assertTrue(q["data"]["document_projection"]["content_complete"])
        self.assertEqual(q["data"]["document_projection"]["catalog_supplied"], 0)

    def test_complete_metadata_shorter_than_partial_does_not_break_fit(self):
        content = "x" * 1000 + "\nY"
        base = self.payload(content)
        full = self.project(base)
        full["data"]["document_projection"].update(catalog_total=1, catalog_complete=False, catalog_omitted=1)
        budget = len(json.dumps(full, ensure_ascii=False))
        for _ in range(3):
            full["data"]["document_projection"]["budget_utf8_bytes"] = budget
            budget = len(json.dumps(full, ensure_ascii=False))
        p = self.payload(content, catalog=[{"section_index": 5, "heading": "huge" * 1000}])
        q = self.project(p, budget)
        self.assertEqual(q["data"]["content"], content)
        self.assertTrue(q["data"]["document_projection"]["content_complete"])

    def test_body_uses_remaining_budget_instead_of_800_field_fallback(self):
        content = "Source header\n" * 60 + "Quarter ended 2026-07-26; USD millions\n| Revenue | 96,221 |\n" + "complete row\n" * 3000
        p = self.payload(content)
        q = self.project(p)
        visible = q["data"]["content"]
        self.assertGreater(len(visible), 8000)
        self.assertIn("96,221", visible)
        self.assertTrue(content.startswith(visible))
        self.assertTrue(visible.endswith("\n"))
        self.assertFalse(q["data"]["document_projection"]["content_complete"])
        self.assertNotIn("[field truncated]", visible)
        self.assertEqual(q["data"]["content_hash"], p["data"]["content_hash"])
        self.assertEqual(q["data"]["document_projection"]["visible_content_sha256"],
                         hashlib.sha256(visible.encode()).hexdigest())
        self.assertNotEqual(q["data"]["content_hash"],
                            q["data"]["document_projection"]["visible_content_sha256"])

    def test_catalog_discovery_is_bounded_and_explicit(self):
        catalog = [{"section_index": i, "heading": "chapter " + str(i),
                    "line_start": i} for i in range(1, 2000)]
        q = self.project(self.payload("not all evidence\n" * 2000, "document.read_file", catalog), 4000)
        d = q["data"]
        self.assertGreater(len(d["section_catalog"]), 0)
        self.assertFalse(d["document_projection"]["catalog_complete"])
        self.assertEqual(d["document_projection"]["catalog_supplied"] +
                         d["document_projection"]["catalog_omitted"], len(catalog))

    def test_never_cut_a_long_row_or_fabricate_pagination(self):
        q = self.project(self.payload("a" * 30000), 2000)
        self.assertEqual(q["data"]["content"], "")
        self.assertEqual(q["data"]["document_projection"]["visible_end_char"], 0)
        self.assertEqual(q["data"]["document_projection"]["omitted_content_chars"], 30000)
        self.assertNotIn("next_offset", q["data"]["document_projection"])

    def test_multibyte_and_json_escaping_match_exact_prefix_hash(self):
        p = self.payload(('数值单位：万元；\"引号\"与\\路径\n' * 4000))
        q = self.project(p, 3000)
        d = q["data"]; m = d["document_projection"]
        self.assertEqual(d["content"], p["data"]["content"][:m["visible_end_char"]])
        self.assertEqual(m["visible_content_sha256"], hashlib.sha256(d["content"].encode()).hexdigest())

    def test_utf8_byte_ceiling_prevents_native_middle_truncation(self):
        p = self.payload(("非ASCII原文™财务表\\n" * 3000))
        q = self.project(p, 12000)
        text = json.dumps(q, ensure_ascii=False)
        self.assertLessEqual(len(text.encode()), 12000)
        self.assertFalse(q["data"]["document_projection"]["content_complete"])
        visible = q["data"]["content"]
        self.assertEqual(q["data"]["document_projection"]["visible_content_sha256"],
                         hashlib.sha256(visible.encode()).hexdigest())

    def test_small_legacy_receipt_remains_complete(self):
        p = self.payload("complete body")
        self.assertEqual(self.project(p, len(json.dumps(p, ensure_ascii=False)))["data"]["content"], "complete body")

    def test_too_small_identity_budget_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "identity/contract"):
            self.project(self.payload("body" * 1000), 100)

    def test_failed_or_denied_document_is_not_success_projection(self):
        for ok, allowed in [(False, False), (False, True), (True, False)]:
            p = self.payload("body")
            p["ok"] = ok
            p["data"]["execution_decision"] = {"allowed": allowed, "reason": "actual decision"}
            q = self.project(p)
            self.assertEqual(q["data"]["execution_decision"], p["data"]["execution_decision"])
            self.assertNotIn("document_projection", q["data"])

    def test_full_content_hash_and_range_are_independent_of_source_version(self):
        p = self.payload("| Date | Unit | Value |\n| 2026-09-26 | USD million | 13,377 |\n")
        q = self.project(p)
        d = q["data"];m = d["document_projection"]
        self.assertTrue(m["content_complete"])
        self.assertEqual(m["visible_end_char"], len(p["data"]["content"]))
        self.assertEqual(m["original_content_sha256"], p["data"]["content_hash"])
        self.assertEqual(m["visible_content_sha256"], p["data"]["content_hash"])
        self.assertEqual(d["source_hash"], "a" * 64)

if __name__ == "__main__":
    unittest.main()
