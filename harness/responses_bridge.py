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


class ContextBudgetError(ValueError):
    """Required Host facts cannot fit the configured recovery-byte budget."""


HOP_HEADERS = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "host", "content-length",
})


class ProviderHistoryBridge:
    """Loopback Responses transport; only outgoing history copies are projected."""

    def __init__(
        self, upstream_url: str, *, journal_path: Path, timeout: float | None = 420,
        raw_events_path: Path | None = None,
        audit_path: Path | None = None,
        max_recovery_bytes: int = 24000,
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
        if max_recovery_bytes <= 0:
            raise ValueError("Recovery byte budget must be positive")
        self.max_recovery_bytes = max_recovery_bytes
        self._compaction_turn_id: str | None = None

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
                # Manual inference can take an unknown time, but establishing a
                # loopback transport still needs a bounded failure check.
                connection = http.client.HTTPConnection(
                    owner.host, owner.port, timeout=10 if owner.timeout is None else owner.timeout)
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
                        forwarded, restoration = owner.restore_runtime_context(
                            projection.request, compact=self.path.split("?", 1)[0] == "/v1/responses/compact")
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
                    if owner.timeout is None and connection.sock is not None:
                        connection.sock.settimeout(None)
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
                except ContextBudgetError:
                    if owner.audit is not None:
                        owner.audit.write({"schema": "uaea.model_http_audit.v1",
                            "event": "request_blocked", "reason": "required_host_context_over_budget",
                            "upstream_forwarded": False, "task_retained": True,
                            "original_bytes_sha256": hashlib.sha256(original_body).hexdigest()})
                    transport_error = "ContextBudgetError"
                    if not headers_sent:
                        error = json.dumps({"error": {"type": "uaea_context_budget_exceeded",
                            "code": 413, "param": "host_context_bytes",
                            "message": "Required Host facts exceed recovery byte budget; request not forwarded. Task retained."}}).encode()
                        self.send_response(413)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(error)))
                        self.end_headers()
                        self.wfile.write(error)
                except ConnectionRefusedError as exc:
                    # Nothing was accepted by the loopback provider. Treat this
                    # as an unavailable service, not a retryable inference or
                    # authorization failure; the Host retains task/receipts.
                    transport_error = type(exc).__name__
                    if not headers_sent:
                        error = json.dumps({"error": {
                            "type": "uaea_provider_unavailable", "code": "provider_connection_refused",
                            "message": "Local model service is not listening. Task and observations remain retained. "
                                       "Restart the service explicitly before continuing; no automatic service reload.",
                            "retryable": False, "workflow_completed": False,
                        }}).encode("utf-8")
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(error)))
                        self.end_headers()
                        self.wfile.write(error)
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
            # Keep authoritative facts outside the model window. The serialized
            # transport copy is bounded in restore_runtime_context; rejecting here
            # would discard the snapshot after a successful tool execution.
            self._runtime_context = deepcopy({
                "blocks": context, "thread_id": thread_id, "input_id": input_id,
                "context_sha256": hashlib.sha256(json.dumps(
                    context, sort_keys=True, ensure_ascii=False).encode()).hexdigest()})

    def set_compaction(self, turn_id: str, active: bool) -> None:
        """Host lifecycle signal only; never infer compaction from model prose."""
        if not turn_id:
            raise ValueError("Compaction identity required")
        with self._lock:
            if active:
                self._compaction_turn_id = turn_id
            elif self._compaction_turn_id == turn_id:
                self._compaction_turn_id = None

    @staticmethod
    def _without_host_blocks(request, blocks):
        labels = {key if value["kind"] == "application" else "external_"+key:
                  "developer" if value["kind"] == "application" else "user"
                  for key, value in blocks.items()}
        # A new Workflow with no acquired sources intentionally publishes no
        # directory. Its previous Workflow's owned directory must still expire.
        labels.setdefault("external_uaea.recovery_source_index", "user")
        result = deepcopy(request)
        removed = 0
        for field in ("input", "previous_input_messages"):
            items = result.get(field)
            if not isinstance(items, list):
                continue
            retained = []
            for item in items:
                if (not isinstance(item, dict) or item.get("type", "message") != "message"
                        or not isinstance(item.get("content"), list)):
                    retained.append(item)
                    continue
                content = []
                for part in item["content"]:
                    value = part.get("text") if isinstance(part, dict) else None
                    text = value.strip() if isinstance(value, str) else ""
                    owned = any(item.get("role") == role
                        and text.startswith("<"+label+">") and text.endswith("</"+label+">")
                        # A complete single envelope only; never strip quoted source text.
                        and text.count("<"+label+">") == 1
                        for label, role in labels.items())
                    if owned:
                        removed += 1
                    else:
                        content.append(part)
                if content or not item["content"]:
                    retained.append({**item, "content": content})
            result[field] = retained
        return result, removed

    @staticmethod
    def _render_blocks(blocks):
        return [{"role": "developer" if block["kind"] == "application" else "user",
                 "content": [{"type": "input_text", "text":
                    "<"+(key if block["kind"] == "application" else "external_"+key)+">\n"+
                    block["value"]+"\n</"+(key if block["kind"] == "application" else "external_"+key)+">"}]}
                for key, block in blocks.items()]

    def _bounded_blocks(self, original):
        blocks = deepcopy(original)
        omitted = []
        def size():
            return len(json.dumps(self._render_blocks(blocks), ensure_ascii=False).encode())
        if size() > self.max_recovery_bytes:
            # Explanatory duplicates are optional; current input, effective
            # constraints, capability state and receipt/source identities are not.
            for key in ("uaea.runtime_facts.model", "uaea.runtime_facts.web_limits",
                        "uaea.runtime_facts.capabilities", "uaea.runtime_facts.interaction",
                        "uaea.runtime_facts.filesystem", "uaea.runtime_facts.execution"):
                if key in blocks:
                    blocks.pop(key);omitted.append(key)
                if size() <= self.max_recovery_bytes:
                    break
        if size() > self.max_recovery_bytes and "uaea.semantic_interpretations" in blocks:
            key = "uaea.semantic_interpretations"
            payload = json.loads(blocks[key]["value"])
            if isinstance(payload, dict) and "background" in payload:
                payload.pop("background")
                payload["background_omitted_for_budget"] = True
                blocks[key]["value"] = json.dumps(payload, ensure_ascii=False)
                omitted.append(key+".background")
        # Lookup hints are lower priority than actual recent evidence. Omit
        # whole identities before shortening source text; never silently cut IDs.
        key = "uaea.recovery_source_index"
        if size() > self.max_recovery_bytes and key in blocks:
            index = json.loads(blocks[key]["value"])
            while index["entries"] and size() > self.max_recovery_bytes:
                index["entries"].pop()
                index["omitted_sources"] += 1
                blocks[key]["value"] = json.dumps(index, ensure_ascii=False)
            omitted.append(key + ".entries:" + str(index["omitted_sources"]))
            if size() > self.max_recovery_bytes:
                blocks.pop(key)
                omitted.append(key)
        if size() > self.max_recovery_bytes and "uaea.recovery_sources" in blocks:
            for limit in (160, 0):
                sources = json.loads(blocks["uaea.recovery_sources"]["value"])
                for source in sources:
                    text = source.get("text", "")
                    source["text"] = text[:limit]
                    source["text_sha256"] = hashlib.sha256(source["text"].encode()).hexdigest()
                    source["supplied_chars"] = len(source["text"])
                    if "start_char" in source and "extracted_text_chars" in source:
                        end = source["start_char"] + len(source["text"])
                        total = source["extracted_text_chars"]
                        source.update(end_char=end, has_more=end < total,
                                      next_start_char=end if end < total else None)
                    # historical_supply describes past results, not this recovery slice.
                    source["truncated_for_budget"] = True
                    source["excerpt_omitted_for_budget"] = not bool(source["text"])
                blocks["uaea.recovery_sources"]["value"] = json.dumps(sources, ensure_ascii=False)
                omitted.append("uaea.recovery_sources.text:"+str(limit))
                if size() <= self.max_recovery_bytes:
                    break
        if size() > self.max_recovery_bytes:
            raise ContextBudgetError("Required current request/constraints/source facts exceed recovery budget")
        return blocks, omitted, size()

    def restore_runtime_context(self, request: dict[str, Any], *, compact=False):
        """Replace stale projections, never append an unbounded second Host copy."""
        with self._lock:
            state = deepcopy(self._runtime_context)
            required = self._context_required
            compaction = compact or self._compaction_turn_id is not None
        if state is None:
            if required:
                raise ValueError("Required Host context unavailable; refusing to forward")
            return request, []
        if not isinstance(request.get("input"), list):
            raise ValueError("Recovery requires explicit Responses input messages")
        restored, removed = self._without_host_blocks(request, state["blocks"])
        if compaction:
            # The immutable Host retains authority/receipts outside the model
            # summary. Reinject them on the next ordinary model request.
            blocks, omitted, supplied_bytes = {}, [], 0
        else:
            blocks, omitted, supplied_bytes = self._bounded_blocks(state["blocks"])
            restored["input"].extend(self._render_blocks(blocks))
        if restored == request and not compaction:
            return request, []
        expected = json.loads(state["blocks"]["uaea.semantic_state_projection"]["value"])
        return restored, [{
            "kind": "host_context_deferred_for_compaction" if compaction else "host_context_restored",
            "reason": "compaction_host_state_retained_out_of_band" if compaction else "host_context_normalized",
            "thread_id": state["thread_id"], "input_id": state["input_id"],
            "task_id": expected["task_id"], "effective_state_id": expected["effective_state_id"],
            "host_context_sha256": state["context_sha256"],
            "block_keys": list(blocks), "source": "published_host_snapshot",
            "removed_host_blocks": removed, "omitted_fields": omitted,
            "recovery_bytes": supplied_bytes, "recovery_byte_limit": self.max_recovery_bytes,
            "token_count": "not_measured; byte budget is not model token count",
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
