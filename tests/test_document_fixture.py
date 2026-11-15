import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from research.document_fixture import render_snapshot, prepare


class DocumentFixtureTests(unittest.TestCase):
    def render(self, html, **kwargs):
        return render_snapshot(html, url="https://example.test/release",
                               captured_utc="2026-11-13T08:00:00Z", title="Original", **kwargs)

    def test_directory_and_source_table_not_question_selected(self):
        html = '<article><p>GAAP results</p><table><tr><th>USD million</th><th>2026</th><th>2025</th></tr><tr><td>Revenue</td><td>13,377</td><td>9,246</td></tr></table><p>End note</p></article>'
        body, m = self.render(html)
        self.assertEqual(m["sections"][0]["name"], "Directory and provenance")
        table = next(x for x in m["sections"] if x["provenance"]["kind"] == "original_table_rows")
        self.assertIn("USD million", table["body"])
        self.assertIn("Revenue | 13,377 | 9,246", table["body"])
        self.assertNotIn("13,377", table["name"])
        self.assertEqual(m["tables"][0]["rows"][1]["cells"][1]["text"], "13,377")
        self.assertEqual(m["raw_html_sha256"], hashlib.sha256(html.encode()).hexdigest())

    def test_displayed_ordinals_match_existing_read_section_catalogue(self):
        from h3_context_characterization import build_adapter
        html = '<article><p>Original date</p><table><tr><th>USD million</th><th>2026</th></tr><tr><td>Revenue</td><td>7</td></tr></table></article>'
        body, mapping = self.render(html)
        with tempfile.TemporaryDirectory() as td:
            adapter = build_adapter(Path(td))
            path = Path(td)/"sandbox"/"rendered.md"
            path.write_text(body)
            root = adapter.registry.execute_capability(
                "document.read_section", {"path":str(path),"section_index":1}, "CPU root check")
            self.assertTrue(root.ok)
            self.assertEqual(root.data["section_index"], 1)
            self.assertEqual(root.data["section"], "1. Original")
            self.assertIn(body.strip(), root.data["content"])
            for section in mapping["sections"]:
                ordinal = section["section_index"]
                result = adapter.registry.execute_capability(
                    "document.read_section", {"path":str(path),"section_index":ordinal}, "CPU ordinal check")
                self.assertTrue(result.ok)
                self.assertEqual(result.data["section_index"], ordinal)
                self.assertEqual(result.data["section"], str(ordinal)+". "+section["name"])
                self.assertIn(section["body"], result.data["content"])

    def test_spans_and_nested_paragraph_dates_remain_explicit(self):
        html = '<article><p>Original</p><table><tr><td colspan="3">Three months ended</td></tr><tr><td><p>September 26,</p><p>2026</p></td><td rowspan="2">USD</td><td>13,377</td></tr></table></article>'
        body, m = self.render(html)
        self.assertIn("colspan=3", body)
        self.assertIn("rowspan=2", body)
        self.assertIn("September 26, 2026", body)
        self.assertEqual(m["tables"][0]["rows"][0]["cells"][0]["colspan"], 3)

    def test_long_tables_repeat_source_context_without_dropping_rows(self):
        html = '<article><p>Original table</p><table><tr><td>Metric</td><td>USD millions</td></tr>' + ''.join('<tr><td>row '+str(i)+'</td><td>'+str(i)+'</td></tr>'for i in range(100)) + '</table></article>'
        body, m = self.render(html, max_part_chars=800)
        parts = [x for x in m["sections"] if x["provenance"]["kind"] == "original_table_rows"]
        seen = [r for p in parts for r in p["provenance"]["rows"]]
        self.assertEqual(seen, list(range(1, 102)))
        self.assertGreater(len(parts), 1)
        self.assertIn("Repeated original context rows", parts[1]["body"])
        self.assertTrue(parts[1]["name"].endswith("/ part 2"))
        self.assertIn("USD millions", parts[1]["body"])

    def test_scripts_navigation_and_external_tables_not_article_evidence(self):
        html = '<nav>OUTSIDE_NAV_TEXT</nav><table><tr><td>outside</td></tr></table><article><script>invented number</script><p>Real text only</p></article>'
        body, m = self.render(html)
        self.assertNotIn("invented number", body)
        self.assertNotIn("outside", body)
        self.assertNotIn("OUTSIDE_NAV_TEXT", body)
        self.assertIn("Real text only", body)

    def test_unknown_container_rejected_instead_of_guessing(self):
        with self.assertRaisesRegex(ValueError, "article container"):
            self.render("<div>unknown source body</div>")

    def test_raw_crlf_hash_not_silently_normalized(self):
        raw = b"<article>\r\n<p>original</p>\r\n</article>"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"raw").write_bytes(raw)
            (p/"capture").write_text(json.dumps({"url":"https://example.test","captured_UTC":"now",
                "sha256":hashlib.sha256(raw).hexdigest()}))
            prepare(p/"raw",p/"capture",p/"out",p/"map")
            self.assertEqual(json.loads((p/"map").read_text())["raw_html_sha256"],hashlib.sha256(raw).hexdigest())
            (p/"raw").write_bytes(raw+b"tamper")
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                prepare(p/"raw",p/"capture",p/"out2",p/"map2")


if __name__ == "__main__":
    unittest.main()
