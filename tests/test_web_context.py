from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

from memory.sqlite_store import connect, counts, ingest_web_fixture, initialize, insert_web_access_event
from phase2.web_context import ProjectionLimits, project_web_access_events


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_FIXTURE_PATH = PROJECT_ROOT / "data" / "memory_test_fixtures" / "web_source_w0_deterministic.json"


class WebContextProjectionTests(unittest.TestCase):
    def test_projection_preserves_web_metadata_and_evidence_reference(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            projection = project_web_access_events(connection, ["WEB-E001"])

        self.assertEqual(len(projection.sources), 1)
        source = projection.sources[0]
        self.assertEqual(source.access_event_id, "WEB-E001")
        self.assertEqual(source.url, "https://example.test/uaea/ds14b-wna16-vllm")
        self.assertEqual(source.accessed_at, "2026-08-24T08:00:00Z")
        self.assertEqual(source.source_provenance, "external")
        self.assertEqual(source.evidence_reference["source_kind"], "web_access_event")
        self.assertEqual(source.evidence_reference["source_id"], "WEB-E001")
        self.assertIn("content_sha256:", projection.evidence_block())

    def test_html_projection_keeps_document_structure_instead_of_naive_prefix(self):
        with self.fixture_connection() as connection:
            initialize(connection)
            html_path = Path(tempfile.mkdtemp()) / "structured.html"
            html_path.write_text(
                """
                <html>
                  <body>
                    <nav>Cookie banner Navigation Home Pricing Login</nav>
                    <main>
                      <h1>Main Compatibility Result</h1>
                      <p>The relevant result is preserved after boilerplate removal.</p>
                    </main>
                    <footer>Footer legal links</footer>
                  </body>
                </html>
                """,
                encoding="utf-8",
            )
            insert_web_access_event(
                connection,
                {
                    "access_event_id": "WEB-STRUCTURED",
                    "url": "https://example.test/structured",
                    "title": "Structured source",
                    "accessed_at": "2026-08-25T01:00:00Z",
                    "access_status": "fetched",
                    "source_type": "web_page",
                    "http_status": 200,
                    "content_ref": str(html_path),
                    "excerpt": "Fallback excerpt should not be needed when snapshot exists.",
                },
            )
            projection = project_web_access_events(connection, ["WEB-STRUCTURED"])

        text = projection.sources[0].projected_text
        self.assertIn("Main Compatibility Result", text)
        self.assertIn("The relevant result is preserved", text)
        self.assertNotIn("Cookie banner", text)
        self.assertNotIn("Footer legal links", text)

    def test_large_source_projection_is_bounded_and_metrics_are_reported(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            projection = project_web_access_events(
                connection,
                ["WEB-E003"],
                limits=ProjectionLimits(max_sources=1, per_source_chars=120, total_chars=120),
            )

        source = projection.sources[0]
        self.assertLessEqual(source.projected_chars, 120)
        self.assertTrue(source.truncated)
        self.assertGreater(source.source_chars, source.projected_chars)
        metrics = projection.metrics()
        self.assertEqual(metrics["context_source_count"], 1)
        self.assertEqual(metrics["projected_chars"], source.projected_chars)
        self.assertGreater(metrics["estimated_prompt_tokens"], 0)

    def test_multiple_sources_respect_source_count_limit(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            projection = project_web_access_events(
                connection,
                ["WEB-E001", "WEB-E002", "WEB-E003", "WEB-E004", "WEB-E005"],
                limits=ProjectionLimits(max_sources=2, per_source_chars=300, total_chars=600),
            )

        self.assertEqual(len(projection.sources), 2)
        self.assertEqual(projection.dropped_source_count, 3)
        self.assertEqual([source.access_event_id for source in projection.sources], ["WEB-E001", "WEB-E002"])

    def test_failed_source_is_visible_without_fabricated_content(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            projection = project_web_access_events(connection, ["WEB-E004"])

        source = projection.sources[0]
        self.assertEqual(source.access_status, "failed")
        self.assertEqual(source.projected_text, "")
        self.assertEqual(source.projected_chars, 0)
        self.assertIn("http_status=503", source.failure_reason)
        self.assertIn("excerpt: <none>", projection.evidence_block())

    def test_conflicting_sources_remain_separate_projection_items(self):
        with self.fixture_connection() as connection:
            initialize(connection)
            insert_web_access_event(
                connection,
                {
                    "access_event_id": "WEB-CONFLICT-A",
                    "url": "https://example.test/conflict/a",
                    "title": "Compatibility source A",
                    "accessed_at": "2026-08-25T02:00:00Z",
                    "access_status": "fetched",
                    "source_type": "web_page",
                    "http_status": 200,
                    "excerpt": "Source A states that the tested backend combination is supported.",
                },
            )
            insert_web_access_event(
                connection,
                {
                    "access_event_id": "WEB-CONFLICT-B",
                    "url": "https://example.test/conflict/b",
                    "title": "Compatibility source B",
                    "accessed_at": "2026-08-25T02:05:00Z",
                    "access_status": "fetched",
                    "source_type": "web_page",
                    "http_status": 200,
                    "excerpt": "Source B states that the tested backend combination is not supported.",
                },
            )
            projection = project_web_access_events(connection, ["WEB-CONFLICT-A", "WEB-CONFLICT-B"])
            actual_counts = counts(connection)

        self.assertEqual(len(projection.sources), 2)
        self.assertIn("Source A states", projection.sources[0].projected_text)
        self.assertIn("Source B states", projection.sources[1].projected_text)
        self.assertEqual(actual_counts["candidates"], 0)
        self.assertEqual(actual_counts["evidence_references"], 0)

    def test_stale_source_keeps_access_timestamp_visible(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            projection = project_web_access_events(connection, ["WEB-E001", "WEB-E002"])

        block = projection.evidence_block()
        self.assertIn("accessed_at: 2026-08-24T08:00:00Z", block)
        self.assertIn("accessed_at: 2026-08-24T08:20:00Z", block)

    @contextmanager
    def fixture_connection(self) -> Iterator[sqlite3.Connection]:
        with tempfile.TemporaryDirectory() as tmpdir:
            with closing(connect(Path(tmpdir) / "memory.db")) as connection:
                yield connection


if __name__ == "__main__":
    unittest.main()
