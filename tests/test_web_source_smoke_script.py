from __future__ import annotations

import http.server
import tempfile
import threading
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

from memory.sqlite_store import connect, counts
from scripts.smoke_web_source_pipeline import _print_text, run_smoke


class WebSourceSmokeScriptTests(unittest.TestCase):
    def test_smoke_script_fetch_repeat_preserves_source_history_and_projection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                db_path = Path(tmpdir) / "source.sqlite"
                result = run_smoke(
                    db_path=db_path,
                    snapshot_root=Path(tmpdir) / "snapshots",
                    fetch_urls=[f"{server}/article.html"],
                    search_queries=[],
                    repeat=2,
                    project=True,
                    max_sources=2,
                    per_source_chars=240,
                    total_chars=480,
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                with closing(connect(db_path)) as connection:
                    actual_counts = counts(connection)

        self.assertEqual(len(result["operations"]), 2)
        self.assertEqual({operation["status"] for operation in result["operations"]}, {"fetched"})
        self.assertEqual(len(result["traces"]), 2)
        self.assertEqual(actual_counts["web_sources"], 1)
        self.assertEqual(actual_counts["web_access_events"], 2)
        self.assertEqual(actual_counts["candidates"], 0)
        self.assertEqual(actual_counts["evidence_references"], 0)
        assert result["projection"] is not None
        self.assertEqual(result["projection"]["metrics"]["context_source_count"], 2)
        self.assertIn("Smoke Web Article", result["projection"]["evidence_block"])

    def test_smoke_script_search_records_result_projection_without_runtime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                result = run_smoke(
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    fetch_urls=[],
                    search_queries=["vLLM AWQ"],
                    repeat=1,
                    project=True,
                    max_sources=1,
                    per_source_chars=320,
                    total_chars=320,
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )

        self.assertEqual(len(result["operations"]), 1)
        self.assertEqual(result["operations"][0]["kind"], "search")
        self.assertEqual(result["operations"][0]["search_result_count"], 1)
        self.assertEqual(result["warnings"], [])
        assert result["projection"] is not None
        self.assertIn("Search query: vLLM AWQ", result["projection"]["evidence_block"])
        self.assertIn("vLLM AWQ result", result["projection"]["evidence_block"])

    def test_smoke_script_warns_when_search_page_has_no_parsed_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                result = run_smoke(
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    fetch_urls=[],
                    search_queries=["empty query"],
                    repeat=1,
                    project=True,
                    max_sources=1,
                    per_source_chars=320,
                    total_chars=320,
                    timeout_seconds=5,
                    search_url_template=f"{server}/empty-search.html?q={{query}}",
                )

        self.assertEqual(result["operations"][0]["status"], "fetched")
        self.assertEqual(result["operations"][0]["search_result_count"], 0)
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("search returned no parsed results", result["warnings"][0])

    def test_smoke_script_requires_an_operation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                run_smoke(
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    fetch_urls=[],
                    search_queries=[],
                    repeat=1,
                    project=True,
                    max_sources=1,
                    per_source_chars=100,
                    total_chars=100,
                    timeout_seconds=5,
                    search_url_template="https://example.test/?q={query}",
                )

    def test_text_output_accepts_unicode_evidence_blocks(self):
        result = {
            "db": "memory.sqlite",
            "snapshot_root": "snapshots",
            "before_counts": {"web_sources": 0, "web_access_events": 0},
            "after_counts": {"web_sources": 1, "web_access_events": 1},
            "operations": [
                {
                    "kind": "fetch",
                    "iteration": 1,
                    "access_event_id": "WEB-EV-1",
                    "status": "fetched",
                    "http_status": 200,
                    "url": "https://example.test",
                    "error": "",
                    "search_result_count": 0,
                    "related_access_event_ids": [],
                }
            ],
            "warnings": [],
            "traces": [
                {
                    "access_event": {
                        "access_event_id": "WEB-EV-1",
                        "access_status": "fetched",
                        "content_chars": 12,
                        "content_sha256": "abc",
                        "content_ref": "snapshot.html",
                    },
                    "web_source": {"web_source_id": "WEB-SRC-1"},
                }
            ],
            "projection": {
                "metrics": {"projected_chars": 12},
                "evidence_block": "unicode: ¶ 中文",
            },
        }

        _print_text(result)


@contextmanager
def local_web_server() -> Iterator[str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _SmokeRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


class _SmokeRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/article.html"):
            self._send(
                200,
                b"""
                <!doctype html>
                <html>
                  <head><title>Smoke fixture</title></head>
                  <body>
                    <main>
                      <h1>Smoke Web Article</h1>
                      <p>This page validates the reusable web source smoke script.</p>
                    </main>
                  </body>
                </html>
                """,
                "text/html; charset=utf-8",
            )
            return
        if self.path.startswith("/search.html"):
            self._send(
                200,
                b"""
                <!doctype html>
                <html>
                  <body>
                    <a class="result__a" href="https://example.test/vllm-awq">vLLM AWQ result</a>
                    <div class="result__snippet">Search smoke fixture result.</div>
                  </body>
                </html>
                """,
                "text/html; charset=utf-8",
            )
            return
        if self.path.startswith("/empty-search.html"):
            self._send(
                200,
                b"""
                <!doctype html>
                <html>
                  <body>
                    <p>No parser-visible result records on this page.</p>
                  </body>
                </html>
                """,
                "text/html; charset=utf-8",
            )
            return
        self._send(404, b"missing", "text/plain")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    unittest.main()
