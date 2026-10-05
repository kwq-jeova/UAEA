from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .provider_history import project_provider_history


HOP_HEADERS = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "host", "content-length",
})


class ProviderHistoryBridge:
    """Loopback Responses transport; only outgoing history copies are projected."""

    def __init__(
        self, upstream_url: str, *, journal_path: Path, timeout: float = 420,
        raw_events_path: Path | None = None,
    ) -> None:
        parsed = urlsplit(upstream_url)
        if (
            parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
            or not parsed.port or parsed.port == 8001 or parsed.username
            or parsed.password or parsed.path.rstrip("/") or parsed.query or parsed.fragment
        ):
            raise ValueError("History bridge requires a loopback diagnostic HTTP endpoint, not 8001.")
        self.host, self.port = parsed.hostname, parsed.port
        self.timeout = timeout
        self.journal_path = Path(journal_path)
        self.raw_events_path = raw_events_path
        self._lock = threading.Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._journal: Any = None
        self.request_count = 0
        self.projected_count = 0

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("History bridge is not started")
        return f"http://127.0.0.1:{self._server.server_port}"

    def start(self) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                self._forward()

            def do_POST(self) -> None:
                self._forward()

            def _forward(self) -> None:
                connection = http.client.HTTPConnection(owner.host, owner.port, timeout=owner.timeout)
                headers_sent = False
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length < 0 or length > 32 * 1024 * 1024:
                        self.send_error(413)
                        return
                    if self.headers.get("Transfer-Encoding"):
                        self.send_error(400, "Chunked request bodies are not supported")
                        return
                    body = self.rfile.read(length) if length else None
                    if body and self.path.split("?", 1)[0] in {
                        "/v1/responses", "/v1/responses/compact",
                    }:
                        request = json.loads(body)
                        if not isinstance(request, dict):
                            self.send_error(400, "Responses request must be an object")
                            return
                        projection = project_provider_history(request)
                        if projection.decisions:
                            body = json.dumps(projection.request, ensure_ascii=False).encode("utf-8")
                        owner._record(projection.decisions, self.headers.get("thread-id", ""))
                    headers = {
                        key: value for key, value in self.headers.items()
                        if key.lower() not in HOP_HEADERS
                    }
                    connection.request(self.command, self.path, body=body, headers=headers)
                    response = connection.getresponse()
                    self.send_response(response.status)
                    for key, value in response.getheaders():
                        if key.lower() not in HOP_HEADERS:
                            self.send_header(key, value)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    headers_sent = True
                    # HTTPResponse.read1 preserves incremental SSE delivery.
                    while chunk := response.read1(65536):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except (OSError, ValueError, TypeError):
                    if not headers_sent:
                        self.send_error(502, "Local provider transport failed")
                finally:
                    self.close_connection = True
                    connection.close()

        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self._journal = self.journal_path.open("a", encoding="utf-8")
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def _record(self, decisions: tuple[dict[str, Any], ...], thread_id: str) -> None:
        with self._lock:
            self.request_count += 1
            self.projected_count += len(decisions)
            if self._journal is not None:
                for decision in decisions:
                    self._journal.write(json.dumps({
                        "provider_request_sequence": self.request_count,
                        "thread_id": thread_id,
                        "source": "uaea.provider_history_projection",
                        "raw_event_reference": {
                            "path": str(self.raw_events_path) if self.raw_events_path else None,
                            "thread_id": thread_id, "turn_id": decision["turn_id"],
                            "call_id": decision["call_id"], "item_id": decision["item_id"],
                        },
                        **decision,
                    }, ensure_ascii=False) + "\n")
                self._journal.flush()

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        if self._journal is not None:
            self._journal.close()
            self._journal = None

    def __enter__(self) -> "ProviderHistoryBridge":
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
