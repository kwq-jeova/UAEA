from __future__ import annotations

from copy import deepcopy
import http.client
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .provider_history import project_provider_history
from .request_audit import RequestAudit


HOP_HEADERS = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "host", "content-length",
})


class ProviderHistoryBridge:
    """Loopback Responses transport; only outgoing history copies are projected."""

    def __init__(
        self, upstream_url: str, *, journal_path: Path, timeout: float = 420,
        raw_events_path: Path | None = None,
        audit_path: Path | None = None,
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
        self.audit = RequestAudit(audit_path) if audit_path is not None else None
        self.audit_errors = 0
        self._runtime_context: dict[str, Any] | None = None
        self._context_required = False

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
                audit_id = None
                response_status = None
                received = 0
                transport_error = None
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
                        original_body = body
                        request = json.loads(body)
                        if not isinstance(request, dict):
                            self.send_error(400, "Responses request must be an object")
                            return
                        projection = project_provider_history(request)
                        forwarded, restoration = owner.restore_runtime_context(projection.request)
                        decisions = projection.decisions + tuple(restoration)
                        if decisions:
                            body = json.dumps(forwarded, ensure_ascii=False).encode("utf-8")
                        sequence = owner._record(decisions, self.headers.get("thread-id", ""))
                        if owner.audit is not None:
                            audit_id = owner.audit.request(
                                original_body, body, path=self.path, sequence=sequence,
                                decisions=decisions)
                    headers = {
                        key: value for key, value in self.headers.items()
                        if key.lower() not in HOP_HEADERS
                    }
                    connection.request(self.command, self.path, body=body, headers=headers)
                    response = connection.getresponse()
                    response_status = response.status
                    self.send_response(response.status)
                    for key, value in response.getheaders():
                        if key.lower() not in HOP_HEADERS:
                            self.send_header(key, value)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    headers_sent = True
                    # HTTPResponse.read1 preserves incremental SSE delivery.
                    while chunk := response.read1(65536):
                        received += len(chunk)
                        self.wfile.write(chunk)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError) as exc:
                    transport_error = type(exc).__name__
                except (OSError, ValueError, TypeError, http.client.HTTPException) as exc:
                    transport_error = type(exc).__name__
                    if not headers_sent:
                        self.send_error(502, "Local provider transport failed")
                finally:
                    if audit_id is not None:
                        try:
                            owner.audit.response(audit_id, status=response_status,
                                                 bytes_received=received, error=transport_error)
                        except OSError:
                            # A response audit failure cannot cause a second model/tool execution.
                            owner.audit_errors += 1
                    self.close_connection = True
                    connection.close()

        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self._journal = self.journal_path.open("a", encoding="utf-8")
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def invalidate_runtime_context(self) -> None:
        with self._lock:
            self._context_required = True
            self._runtime_context = None

    def set_runtime_context(self, context: dict[str, Any], *, thread_id: str, input_id: str) -> None:
        """Publish an immutable host snapshot; never obtain state from model messages."""
        with self._lock:
            self._context_required = True
            self._runtime_context = None
            if not thread_id or not input_id:
                raise ValueError("Host context identity missing")
            block = context.get("uaea.semantic_state_projection", {})
            if block.get("kind") != "application":
                raise ValueError("Host state projection missing")
            projection = json.loads(block["value"])
            if not projection.get("task_id") or not projection.get("effective_state_id"):
                raise ValueError("Host state scope/version missing")
            for block in context.values():
                if block.get("kind") not in {"application", "untrusted"} or not isinstance(block.get("value"), str):
                    raise ValueError("Invalid host context block")
            if sum(len(b["value"]) for b in context.values()) > 24000:
                raise ValueError("Host recovery context exceeds bounded budget")
            self._runtime_context = deepcopy({
                "blocks": context, "thread_id": thread_id, "input_id": input_id,
                "context_sha256": hashlib.sha256(json.dumps(
                    context, sort_keys=True, ensure_ascii=False).encode()).hexdigest()})

    def restore_runtime_context(self, request: dict[str, Any]):
        """Responses adapter: recover lost host context, not the Harness's reasoning/history."""
        with self._lock:
            state = deepcopy(self._runtime_context)
            required = self._context_required
        if state is None:
            if required:
                raise ValueError("Required Host context unavailable; refusing to forward")
            return request, []
        items = request.get("input")
        if not isinstance(items, list):
            raise ValueError("Recovery requires explicit Responses input messages")
        tag = "uaea.semantic_state_projection"
        expected = json.loads(state["blocks"][tag]["value"])
        found = None
        critical = {"uaea.semantic_state_projection", "uaea.context_boundary",
                    "uaea.effective_capability_state", "uaea.retained_user_requests",
                    "uaea.evidence_provenance", "uaea.semantic_interpretations"} & state["blocks"].keys()
        seen = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            for part in item.get("content", []):
                text = part.get("text", "") if isinstance(part, dict) else ""
                for key in critical:
                    trusted = state["blocks"][key]["kind"] == "application"
                    label = key if trusted else "external_"+key
                    if (item.get("role") == ("developer" if trusted else "user")
                            and text.strip().startswith("<"+label+">")
                            and text.strip().endswith("</"+label+">")):
                        seen.add(key)
                if (item.get("role") == "developer" and text.strip().startswith("<"+tag+">")
                        and text.strip().endswith("</"+tag+">")):
                    try:
                        found = json.loads(text.strip()[len(tag)+2:-(len(tag)+3)])
                    except ValueError:
                        found = None
        if (critical <= seen and isinstance(found, dict)
                and all(found.get(k) == expected[k] for k in ("task_id", "effective_state_id"))):
            return request, []
        restored = deepcopy(request)
        blocks = state["blocks"]
        for key, block in blocks.items():
            label = key if block["kind"] == "application" else "external_"+key
            restored["input"].append({
                "role": "developer" if block["kind"] == "application" else "user",
                "content": [{"type": "input_text", "text":
                    "<"+label+">\n"+block["value"]+"\n</"+label+">"}]})
        return restored, [{
            "kind": "host_context_restored", "reason": "host_context_missing_or_stale",
            "thread_id": state["thread_id"], "input_id": state["input_id"],
            "task_id": expected["task_id"], "effective_state_id": expected["effective_state_id"],
            "host_context_sha256": state["context_sha256"],
            "block_keys": list(blocks), "source": "published_host_snapshot",
            "turn_id": "", "call_id": "", "item_id": "",
            "creates_execution_or_authorization": False,
        }]

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
            return self.request_count

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
