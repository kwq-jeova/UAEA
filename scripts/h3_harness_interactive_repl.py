from __future__ import annotations

import argparse
import json
import math
import os
import queue
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from harness.codex_dynamic_tools import (  # noqa: E402
    DynamicToolBinding,
    HarnessDynamicToolAdapter,
)
from harness.io_contract import (  # noqa: E402
    effective_capability_summary,
    runtime_fact_summary,
    turn_context_payload,
)
from harness.semantic_state_adapter import (  # noqa: E402
    HarnessSemanticStateAdapter,
    ProjectionCapacityError,
    SEMANTIC_STATE_SCHEMA,
)
from harness.user_interaction import collect_answers, InputCancelled
from harness.responses_bridge import ProviderHistoryBridge  # noqa: E402
from harness.semantic_promotion_audit import build_promotion_audit  # noqa: E402
from harness.trajectory_writer import HarnessTrajectoryWriter  # noqa: E402
from phase2.web_adapter import WebAdapter  # noqa: E402
from phase2.web_capability import (  # noqa: E402
    WebFetchCapability,
    WebSearchCapability,
    web_fetch_metadata,
    web_search_metadata,
)
from phase2.web_context import ProjectionLimits  # noqa: E402
from phase2.web_environment import WebEnvironmentError, load_web_environment  # noqa: E402
from phase2.terminal_input import read_user_input  # noqa: E402
from runtime.ledger import LedgerStub  # noqa: E402
from runtime.sandbox import Sandbox  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402

from h3_context_characterization import (  # noqa: E402
    DEFAULT_CODEX_BIN,
    DEFAULT_CODEX_HOME_ROOT,
    DEFAULT_GPU_MEMORY_UTILIZATION,
    DEFAULT_HEALTH_TIMEOUT,
    DEFAULT_MODEL,
    DEFAULT_MODEL_ROOT,
    DEFAULT_PORT,
    DEFAULT_RESULT_ROOT,
    DEFAULT_VLLM_ROOT,
    DEFAULT_WORKSPACE_ROOT,
    ensure_endpoint_not_serving,
    start_vllm,
    stop_process,
    wait_for_health,
    wait_for_external_health,
    write_config,
)


DEFAULT_CONTEXT_WINDOW = 32768
DEFAULT_TURN_TIMEOUT = 0  # Manual interaction has no fixed Turn deadline.


RUNTIME_FACT_SUMMARY = runtime_fact_summary()


def _optional_wait_timeout(value: float | None) -> float | None:
    """0/None disable an interactive wait deadline; positive values opt in."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Wait timeout must be finite and non-negative, or None")
    return None if value == 0 else value


def json_line(value: Any) -> str:
    return json.dumps(
        _sanitize_json_value(value),
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def _sanitize_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return _remove_unicode_surrogates(value)
    if isinstance(value, dict):
        return {
            _remove_unicode_surrogates(str(key)): _sanitize_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_json_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_json_value(item) for item in value)
    return value


def _remove_unicode_surrogates(value: str) -> str:
    return "".join(char for char in value if not 0xD800 <= ord(char) <= 0xDFFF)


def utc_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")


def build_interactive_adapter(root: Path) -> HarnessDynamicToolAdapter:
    sandbox_root = PROJECT_ROOT
    trace_root = root / "traces"
    db_path = root / "source.sqlite"
    snapshot_root = root / "web-snapshots"
    trace_root.mkdir(parents=True, exist_ok=True)
    snapshot_root.mkdir(parents=True, exist_ok=True)

    registry = ToolRegistry(Sandbox(PROJECT_ROOT, sandbox_root), LedgerStub(trace_root))
    web_adapter = WebAdapter(snapshot_root=snapshot_root, timeout_seconds=20)
    projection_limits = ProjectionLimits(max_sources=3, per_source_chars=900, total_chars=2800)
    registry.register_capability(
        web_search_metadata(),
        WebSearchCapability(
            db_path=db_path,
            adapter=web_adapter,
            projection_limits=projection_limits,
        ),
    )
    registry.register_capability(
        web_fetch_metadata(),
        WebFetchCapability(
            db_path=db_path,
            adapter=web_adapter,
            projection_limits=projection_limits,
        ),
    )

    return HarnessDynamicToolAdapter(
        registry,
        [
            DynamicToolBinding.from_registry(
                registry,
                "document.read_section",
                description=(
                    "Read one Markdown section from a project file. Use this for "
                    "requests to read or summarize a specific section of README.md "
                    "or another accessible project Markdown file."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "section": {"type": "string"},
                        "section_index": {"type": "integer"},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            ),
            DynamicToolBinding.from_registry(
                registry,
                "fs.list",
                description="List files under an accessible project directory.",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "additionalProperties": False,
                },
            ),
            DynamicToolBinding.from_registry(
                registry,
                "web.search",
                description=(
                    "Discover candidate public web sources from a search results page. "
                    "Preserve user constraints as structured arguments when present. "
                    "Use provider for a requested search provider such as google, bing, or duckduckgo; "
                    "when provider is set, also set allow_fallback explicitly. "
                    "Use allow_fallback=false when the user forbids fallback to another provider. "
                    "Do not encode search provider requirements as preferred_domains. "
                    "Use web.fetch on a selected result URL when page-level evidence is needed. "
                    "Constraint enforcement is best-effort and actual provider details are returned. "
                    "Only cite URLs returned by web.search or web.fetch. "
                    "Use published_from/published_to for a publication-date range; this does not verify "
                    "the period discussed in the content. Ask the user if those meanings are ambiguous."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
                        "provider": {
                            "type": "string",
                            "enum": ["google", "bing", "duckduckgo"],
                            "description": "Requested search provider. Google is a provider request, not a preferred result domain.",
                        },
                        "allow_fallback": {
                            "type": "boolean",
                            "description": "A proposed provider switch, not an authorization grant. true requires effective provider-switch authorization; unknown authorization is not permission. Use false for a same-provider request when switching is not authorized. The Runtime validates each proposal.",
                        },
                        "language": {"type": "string", "description": "Preferred language code, for example en or zh."},
                        "region": {
                            "type": "string",
                            "description": "Preferred region code such as us or cn. Omit this field for global/no specific region.",
                        },
                        "exclude_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Domains to exclude best-effort, for example baidu.com.",
                        },
                        "preferred_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Domains to prefer best-effort.",
                        },
                        "source_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["academic", "forum", "news", "documentation", "general"],
                            },
                        },
                        "published_from": {
                            "type": "string", "description": "Inclusive publication-date lower bound YYYY-MM-DD; supply with published_to."
                        },
                        "published_to": {
                            "type": "string", "description": "Inclusive publication-date upper bound YYYY-MM-DD, not the content's financial/research period. Native date filtering currently supports provider=google with allow_fallback=false."
                        },
                        "freshness": {
                            "type": "string",
                            "enum": ["day", "week", "month", "year", "recent", "any"],
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            ),
            DynamicToolBinding.from_registry(
                registry,
                "web.fetch",
                description=(
                    "Fetch a specific public URL and return bounded page-level evidence from it. "
                    "Use this after web.search when a candidate source needs verification or summary. "
                    "Only the returned source_excerpt segment was supplied, not the full page. "
                    "For more text, reuse its source_event_id and next_start_char as start_char "
                    "with the same URL; this reads the saved snapshot without another HTTP fetch. "
                    "uaea.recovery_source_index lists older Host-acquired source IDs after compaction. "
                    "An index entry is not page content: read its saved snapshot when needed and allowed. "
                    "If unavailable or tools are forbidden, keep missing details unknown; never substitute another source. "
                    "max_chars is bounded to 3000; actual supplied end_char/next_start_char "
                    "reflect the tool output budget. HTTP success does not prove article content."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "source_event_id": {"type": "string", "description": "Previous fetch access_event_id in this run; fixes snapshot version."},
                        "start_char": {"type": "integer", "minimum": 0, "description": "Use previous next_start_char; nonzero requires source_event_id."},
                        "max_chars": {"type": "integer", "minimum": 1, "maximum": 3000},
                    },
                    "required": ["url"],
                    "additionalProperties": False,
                },
            ),
        ],
        max_output_chars=5000,
    )


class InteractiveAppServer:
    def __init__(
        self,
        *,
        codex: Path,
        codex_home: Path,
        workspace: Path,
        base_url: str,
        adapter: HarnessDynamicToolAdapter,
        events_path: Path,
        stderr_path: Path,
        turn_timeout: float | None,
        model: str = DEFAULT_MODEL,
        user_input_timeout: float | None = 0,
        reasoning_effort: str = "none",
        execution_contract: str = "legacy",
        goal_mode: str = "off",
        goal_projection: str = "optional",
        input_actor: str = "operator",
    ) -> None:
        self.codex = codex
        self.codex_home = codex_home
        self.workspace = workspace
        self.base_url = base_url.rstrip("/")
        self.adapter = adapter
        self.events_path = events_path
        self.stderr_path = stderr_path
        self.turn_timeout = _optional_wait_timeout(turn_timeout)
        self.model = model
        if reasoning_effort not in {"none", "low", "medium", "high"}:
            raise ValueError("Unsupported Harness reasoning effort")
        self.reasoning_effort = reasoning_effort
        self.user_input_timeout = _optional_wait_timeout(user_input_timeout)
        self._input_wait_seconds = 0.0
        self._native_input_responses: dict[str, tuple[str, dict]] = {}
        self._pending_user_input: str | None = None
        self._dynamic_tools: list[dict[str, Any]] = []
        self.process: subprocess.Popen[str] | None = None
        self.thread_id = ""
        self._queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self._request_id = 1
        self._turn_wait: dict[str, Any] | None = None
        self._pending_turn: dict[str, Any] | None = None
        self._handled_call_ids: set[str] = set()
        self._events_file: Any = None
        self._stderr_file: Any = None
        self._semantic_snapshots_file: Any = None
        self._promotion_audit_file: Any = None
        self._promotion_audit_sequence = 0
        self._last_turn_context: dict[str, Any] | None = None
        self._history_bridge: ProviderHistoryBridge | None = None
        self._trajectory_writer: HarnessTrajectoryWriter | None = None
        self.semantic_state = HarnessSemanticStateAdapter(require_registered_input=True)
        from harness.goal_integration import GoalIntegration
        self.goals = GoalIntegration(self.semantic_state, events_path.with_name("goal-events.jsonl"),
                                     mode=goal_mode, input_actor=input_actor, projection=goal_projection)
        self.adapter.bind_semantic_state_adapter(self.semantic_state)
        if execution_contract not in {"legacy", "shared"}:
            raise ValueError("Unknown execution contract mode")
        self.execution_contract = execution_contract
        if execution_contract == "shared":
            from harness.execution_host import SharedExecutionHost
            self.adapter.execution_boundary = SharedExecutionHost(
                self.adapter.registry, self.semantic_state,
                events_path.with_name("execution-contract.trajectory.jsonl"))

    def start(self, *, resume_thread_id: str = "") -> None:
        from harness.version_manifest import codex_process_environment, identify_harness, verify_binary_digest, verify_binary_platform

        env = codex_process_environment(self.codex_home)
        provenance = identify_harness(self.codex)
        verify_binary_platform(self.codex, provenance)
        verify_binary_digest(self.codex, provenance)
        provenance["reported_version"] = subprocess.check_output(
            [str(self.codex), "--version"], text=True, timeout=30, env=env).strip()
        if (provenance["tag"] != "explicit_binary_override"
                and provenance["tag"].removeprefix("rust-v") not in provenance["reported_version"]):
            raise RuntimeError("Harness binary version does not match the selected manifest entry")
        print(f"[HARNESS VERSION] tag={provenance['tag']} commit={provenance['commit']} "
              f"binary={self.codex}", flush=True)
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.with_name("harness-versions.jsonl").open("a", encoding="utf-8") as journal:
            journal.write(json_line(provenance) + "\n")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._events_file = self.events_path.open("a", encoding="utf-8")
        self._stderr_file = self.stderr_path.open("a", encoding="utf-8")
        self._semantic_snapshots_file = self.events_path.with_name(
            "semantic-state-snapshots.jsonl"
        ).open("a", encoding="utf-8")
        self._trajectory_writer = HarnessTrajectoryWriter(
            self.events_path.parent / "normalized-trajectories",
            run_id=f"{self.events_path.parent.name}.{self.events_path.stem}.{uuid.uuid4().hex}",
        )
        try:
            self._promotion_audit_file = self.events_path.with_name(
                "semantic-promotion-audit.jsonl"
            ).open("a", encoding="utf-8")
        except OSError as exc:
            print(f"[AUDIT] shadow journal unavailable: {type(exc).__name__}", flush=True)
        self._write_run_manifest()
        self._history_bridge = ProviderHistoryBridge(
            self.base_url,
            journal_path=self.events_path.with_name("provider-history-decisions.jsonl"),
            timeout=self.turn_timeout,
            raw_events_path=self.events_path,
            audit_path=self.events_path.with_name("model-http-audit.jsonl"),
        )
        self._history_bridge.start()
        self.process = subprocess.Popen(
            [
                str(self.codex),
                "app-server",
                "--stdio",
                "-c",
                f'model_providers.uaea_local_vllm.base_url="{self._history_bridge.base_url}/v1"',
            ],
            cwd=str(self.workspace),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        for stream, label in (
            (self.process.stdout, "stdout"),
            (self.process.stderr, "stderr"),
        ):
            threading.Thread(
                target=self._read_stream,
                args=(stream, label, self._queue),
                daemon=True,
            ).start()
        initialize_id = self._next_id()
        initialized = self._request(
            {
                "jsonrpc": "2.0",
                "id": initialize_id,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "uaea-h3-harness-interactive-repl",
                        "title": "UAEA H3 Harness Interactive REPL",
                        "version": "0.1.0",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            },
            lambda message: message.get("id") == initialize_id,
            timeout=60,
        )
        if initialized is None or initialized.get("error") is not None:
            raise RuntimeError(f"app-server initialize failed: {initialized}")
        thread_id = self._next_id()
        self._dynamic_tools = self.adapter.dynamic_tools()
        thread = self._request(
            {
                "jsonrpc": "2.0",
                "id": thread_id,
                "method": "thread/resume" if resume_thread_id else "thread/start",
                "params": {
                    "model": self.model,
                    "modelProvider": "uaea_local_vllm",
                    "cwd": str(self.workspace),
                    **({"threadId": resume_thread_id} if resume_thread_id else {"ephemeral": False}),
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "personality": "none",
                    "experimentalRawEvents": True,
                    **({} if resume_thread_id else {"dynamicTools": self._dynamic_tools}),
                },
            },
            lambda message: message.get("id") == thread_id,
            timeout=60,
        )
        if thread is None or thread.get("error") is not None:
            raise RuntimeError(f"thread/start failed: {thread}")
        self.thread_id = str(thread["result"]["thread"]["id"])

    def run_turn(self, text: str) -> None:
        from harness.request_continuity import parse_request_operation

        if text.startswith("/turn "):
            self._control_turn(text)
            return
        if self._pending_turn is not None:
            # Consume an already queued terminal event before considering a new
            # request. Never replace current_input_id while the old Turn runs.
            self._resume_pending_turn(timeout=0.05)
            if self._pending_turn is not None:
                print("[HARNESS] previous Turn is still active or unconfirmed. "
                      "Input not sent or retained. Use /turn wait, /turn status, "
                      "or /turn cancel; ordinary text cannot start another Turn.", flush=True)
                self._turn_lifecycle("new_input_blocked")
                return
        if text.startswith("/goal "):
            try:
                result = self.goals.control(self.thread_id, text)
                self._publish_runtime_context()
                print("[UAEA GOAL] " + json_line(result), flush=True)
            except ValueError as exc:
                print("[UAEA GOAL] rejected: " + str(exc), flush=True)
            return
        try:
            request_operation = parse_request_operation(text)
        except ValueError as exc:
            print(f"[UAEA] {exc}", flush=True)
            return
        request_id = self._next_id()
        try:
            semantic_projection = self.semantic_state.prepare_turn(
                self.thread_id, text, request_operation=request_operation)
        except ProjectionCapacityError as exc:
            self._last_turn_context = {}
            print(
                "[UAEA] pre-turn projection rejected: "
                f"required_chars={exc.required_chars} budget_chars={exc.budget_chars}; "
                "constraints retained, no Harness request sent; session remains open. "
                "Explicitly revise constraints before retrying, or use a new thread.",
                flush=True,
            )
            # This is a local pre-turn fact, not a Harness terminal event or a sent projection.
            if self._semantic_snapshots_file is not None:
                try:
                    snapshot = self.semantic_state.snapshot(self.thread_id)
                    self._semantic_snapshots_file.write(json_line({
                        "observed_at": datetime.utcnow().isoformat(),
                        "event": "PRE_TURN_REJECTED",
                        "thread_id": self.thread_id,
                        "turn_id": "",
                        "input_id": snapshot["current_input_id"],
                        "prior_turn_id": snapshot["last_turn_id"],
                        "projection_failure": {
                            "required_chars": exc.required_chars,
                            "budget_chars": exc.budget_chars,
                            "app_server_requested": False,
                            "last_projection_is_previous": True,
                        },
                        "snapshot": snapshot,
                    }) + "\n")
                    self._semantic_snapshots_file.flush()
                except Exception as diagnostic_exc:
                    print(f"[UAEA] capacity diagnostic failed: {type(diagnostic_exc).__name__}", flush=True)
            return
        self._last_turn_context = turn_context_payload(
            self._dynamic_tools, model=self.model, semantic_projection=semantic_projection.payload,
            evidence_provenance=self.semantic_state.snapshot(self.thread_id)["evidence_provenance"],
            retained_requests=self.semantic_state.retained_requests(self.thread_id),
            filesystem_root=str(PROJECT_ROOT),
        )
        self._last_turn_context.update(self.goals.context(self.thread_id))
        goal_input_id = self.semantic_state.snapshot(self.thread_id)["current_input_id"]
        from harness.request_audit import RequestAudit, digest
        projection_snapshot = self.semantic_state.snapshot(self.thread_id)
        RequestAudit(self.events_path.with_name("context-projections.jsonl")).write({
            "schema": "uaea.context_delivery.v1", "stage": "prepared_for_app_server",
            "thread_id": self.thread_id,
            "manifest": projection_snapshot["projection_manifest"],
            "blocks": {key: {"kind": block["kind"], "chars": len(block["value"]),
                             "value_sha256": digest(block["value"].encode())}
                       for key, block in self._last_turn_context.items()},
            "upstream_http_delivery": "see model-http-audit.jsonl",
        })
        self._publish_runtime_context()
        self._write_promotion_audit("PRE_TURN")
        print("\n[HARNESS] turn/start", flush=True)
        print(f"[UAEA] runtime_facts injected: {runtime_fact_summary(model=self.model)}", flush=True)
        print(
            "[UAEA] effective_capability_state injected: "
            f"{effective_capability_summary(self._dynamic_tools)}",
            flush=True,
        )
        print(
            "[UAEA] semantic_state projection: "
            f"topic={semantic_projection.payload.get('topic') or '-'} "
            f"relation={semantic_projection.payload['turn_relation']['relation']} "
            f"constraints={len(semantic_projection.payload.get('constraints') or [])}",
            flush=True,
        )
        completion = self._request_turn(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "turn/start",
                "params": {
                    "threadId": self.thread_id,
                    "input": [{"type": "text", "text": text}],
                    "effort": self.reasoning_effort,
                    "model": self.model,
                    "additionalContext": self._last_turn_context,
                    # Goal metadata is an optional observable final envelope.
                    # Do not constrain every provider sampling step: native
                    # tool-call generation must retain its original protocol.
                },
            },
            timeout=self.turn_timeout,
        )
        self._report_turn_completion(completion, goal_input_id)

    def _report_turn_completion(self, completion, goal_input_id) -> None:
        if completion is not None and self.goals.mode != "off":
            turn = (completion.get("params") or {}).get("turn") or {}
            if turn.get("status") == "completed":
                messages = [x for x in turn.get("items", []) if x.get("type") == "agentMessage"]
                if messages:
                    final = messages[-1]
                    try:
                        candidate = self.goals.observe_final(
                            self.thread_id, input_id=goal_input_id, turn_id=turn["id"],
                            model_event_id=final["id"], text=extract_text(final))
                        if candidate is not None:
                            print("[UAEA GOAL] candidate=" + candidate.object_id
                                  + " relation=" + candidate.metadata["proposal"]["relation"]
                                  + " references_valid=" + str(candidate.metadata["reference_validation"]["valid"])
                                  + " summary=" + candidate.metadata["hypothesis"]["hypothesis"], flush=True)
                    except (ValueError, KeyError, TypeError) as exc:
                        self.goals._event(self.thread_id, "GOAL_PROPOSAL_REJECTED",
                            {"input_id": goal_input_id, "turn_id": turn.get("id"),
                             "reason": type(exc).__name__, "detail": str(exc)[:160]})
                        print("[UAEA GOAL] final proposal rejected; no Goal adoption.", flush=True)
        if completion is None:
            print("[HARNESS] Turn is NOT confirmed stopped; no terminal event received. "
                  "Use /turn wait to keep waiting, /turn cancel to request "
                  "interruption, or /turn status. Workflow remains unfinished.", flush=True)
        elif completion.get("error") is not None:
            print(f"[HARNESS] turn error: {completion['error']}", flush=True)
        else:
            turn = (completion.get("params") or {}).get("turn") or {}
            status = turn.get("status")
            error = turn.get("error")
            if status and status != "completed":
                print(f"[HARNESS] turn/{status} error={error}", flush=True)
            else:
                print("[HARNESS] turn/completed", flush=True)

    def _turn_lifecycle(self, event: str) -> None:
        pending = self._pending_turn or {}
        with self.events_path.with_name("turn-lifecycle.jsonl").open("a", encoding="utf-8") as log:
            log.write(json_line({
                "event": event, "observed_at": datetime.utcnow().isoformat(),
                "thread_id": self.thread_id, "turn_id": pending.get("turn_id"),
                "start_request_id": pending.get("request_id"),
                "input_id": pending.get("input_id"), "workflow_completed": False,
                "turn_timeout_seconds": self.turn_timeout,
            }) + "\n")

    def _matches_pending_turn(self, message: dict[str, Any]) -> bool:
        pending = self._turn_wait
        if pending is None:
            return False
        return (
            message.get("method") == "turn/completed"
            and (message.get("params") or {}).get("threadId") == self.thread_id
            and pending["turn_id"] is not None
            and (message.get("params") or {}).get("turn", {}).get("id") == pending["turn_id"]
        ) or (message.get("id") == pending["request_id"] and message.get("error") is not None)

    def _resume_pending_turn(self, *, timeout: float | None, journal_unconfirmed: bool = True) -> None:
        pending = self._pending_turn
        if pending is None:
            return
        self._turn_wait = pending
        try:
            completion = self._wait_for(self._matches_pending_turn, timeout)
        except KeyboardInterrupt:
            self._turn_lifecycle("wait_interrupted")
            return
        finally:
            self._turn_wait = None
        if completion is not None:
            self._turn_lifecycle("terminal_confirmed")
            self._pending_turn = None
            self._report_turn_completion(completion, pending.get("input_id"))
        elif journal_unconfirmed:
            self._turn_lifecycle("still_unconfirmed")

    def poll_pending_turn(self) -> None:
        """Service the existing Turn while the operator decides what to do."""
        if self._pending_turn is not None:
            self._resume_pending_turn(timeout=0.01, journal_unconfirmed=False)
        if self.process is not None and self.process.poll() is not None:
            raise EOFError("Harness process ended; pending work is not completed")

    def _control_turn(self, text: str) -> None:
        operation = text.strip()
        if operation not in {"/turn wait", "/turn status", "/turn cancel"}:
            print("[HARNESS] Use /turn wait, /turn status, or /turn cancel.", flush=True)
            return
        if self._pending_turn is None:
            print("[HARNESS] no pending Turn.", flush=True)
            return
        if operation == "/turn status":
            print("[HARNESS] pending Turn (last observed, not completion): "
                  + json_line(self._pending_turn), flush=True)
            return
        if operation == "/turn cancel":
            # Resolve a late ACK/terminal first. Without a known Turn ID, do not
            # guess which native operation to interrupt.
            self._resume_pending_turn(timeout=0.05)
            if self._pending_turn is None:
                return
            turn_id = self._pending_turn["turn_id"]
            if not turn_id:
                print("[HARNESS] start ACK not received; cannot target cancellation. "
                      "Use /turn wait or exit this Harness session.", flush=True)
                return
            self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "turn/interrupt",
                        "params": {"threadId": self.thread_id, "turnId": turn_id}})
            self._turn_lifecycle("interrupt_requested")
            self._resume_pending_turn(timeout=10)
        else:
            self._turn_lifecycle("wait_requested")
            self._resume_pending_turn(timeout=self.turn_timeout)
        if self._pending_turn is not None:
            print("[HARNESS] Turn still active/unconfirmed; no new input will be sent.", flush=True)

    def close(self) -> None:
        if self.process is not None:
            try:
                if self.process.stdin is not None:
                    self.process.stdin.close()
            except OSError:
                pass
            if self.process.poll() is None:
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except (OSError, ProcessLookupError):
                    self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    except (OSError, ProcessLookupError):
                        self.process.kill()
                    self.process.wait(timeout=10)
            self.process = None
        for handle in (self._events_file, self._stderr_file):
            if handle is not None and not handle.closed:
                handle.flush()
                handle.close()
        self._events_file = None
        self._stderr_file = None
        if self._history_bridge is not None:
            self._history_bridge.close()
            self._history_bridge = None
        if self._trajectory_writer is not None:
            self._trajectory_writer.close()
            self._trajectory_writer = None
        if self._semantic_snapshots_file is not None:
            self._semantic_snapshots_file.flush()
            self._semantic_snapshots_file.close()
            self._semantic_snapshots_file = None
        if self._promotion_audit_file is not None:
            try:
                self._promotion_audit_file.close()
            except OSError:
                pass
            self._promotion_audit_file = None

    def _write_run_manifest(self) -> None:
        import hashlib
        sources = {}
        for folder in ("harness", "phase2", "scripts"):
            for path in sorted((PROJECT_ROOT / folder).glob("*.py")):
                sources[str(path.relative_to(PROJECT_ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True, timeout=3).strip()
            status = subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, timeout=3)
            dirty = bool(status)
        except (OSError, subprocess.SubprocessError):
            head, dirty = None, None
        from urllib.parse import urlsplit
        endpoint = urlsplit(self.base_url)
        safe_endpoint = f"{endpoint.scheme}://{endpoint.hostname}:{endpoint.port}"
        manifest = {
            "schema": "uaea.run_manifest.v1", "execution_contract": self.execution_contract,
            "goal_mode": self.goals.mode, "goal_projection": self.goals.projection,
            "input_actor": self.goals.input_actor,
            "uaea_head": head, "git_dirty": dirty,
            "source_tree_sha256": hashlib.sha256(json_line(sources).encode()).hexdigest(),
            "source_files_sha256": sources, "model": self.model,
            "base_url": safe_endpoint,
            "turn_timeout_seconds": self.turn_timeout,
            "user_input_timeout_seconds": self.user_input_timeout,
            "turn_wait_policy": "unbounded" if self.turn_timeout is None else "finite_opt_in",
            "manual_wait_changes_safety_policy": False,
            "reasoning_effort": self.reasoning_effort,
            "model_behavior": "not_evaluated_by_manifest",
        }
        self.events_path.with_name("run-manifest.json").write_text(json_line(manifest)+"\n")

    def _publish_runtime_context(self) -> None:
        try:
            self._publish_runtime_context_snapshot()
        except Exception:
            if self._history_bridge is not None:
                self._history_bridge.invalidate_runtime_context()
            raise

    def _publish_runtime_context_snapshot(self) -> None:
        if self._history_bridge is None or not self.thread_id:
            return
        snapshot = self.semantic_state.snapshot(self.thread_id)
        if not snapshot.get("current_input_id"):
            return
        projection = self.semantic_state.current_projection(self.thread_id)
        context = turn_context_payload(
            self._dynamic_tools, model=self.model, semantic_projection=projection.payload,
            evidence_provenance=snapshot["evidence_provenance"],
            retained_requests=self.semantic_state.retained_requests(self.thread_id),
            filesystem_root=str(PROJECT_ROOT))
        current = next((x for x in snapshot["workflow_continuity"]["request_continuity"]["inputs"]
                        if x["object_id"] == snapshot["current_input_id"]), None)
        if current is not None:
            context["uaea.current_user_request"] = {
                "kind": "untrusted", "value": json_line({
                    "input_id": current["object_id"], "text": current["metadata"]["text"],
                    "raw_text_sha256": current["metadata"]["raw_text_sha256"],
                    "authorization_established": False})}
        context["uaea.recovery_sources"] = {
            "kind": "untrusted", "value": json_line(self.semantic_state.recovery_sources(self.thread_id))}
        source_index = self.semantic_state.recovery_source_index(self.thread_id)
        if (source_index["total_sources"] or source_index["invalid_receipts"]
                or source_index["conflicting_identities"]):
            context["uaea.recovery_source_index"] = {
                "kind": "untrusted", "value": json_line(source_index)}
        context.update(self.goals.context(self.thread_id))
        self._history_bridge.set_runtime_context(
            context, thread_id=self.thread_id, input_id=snapshot["current_input_id"])

    def _write_promotion_audit(
        self, stage: str, *, snapshot: dict[str, Any] | None = None,
    ) -> None:
        if self._promotion_audit_file is None:
            return
        if snapshot is not None and snapshot.get("schema") != SEMANTIC_STATE_SCHEMA:
            return
        try:
            report = build_promotion_audit(
                snapshot if snapshot is not None else self.semantic_state.snapshot(self.thread_id),
                stage=stage, additional_context=self._last_turn_context,
            )
            self._promotion_audit_sequence += 1
            report.update({
                "audit_sequence": self._promotion_audit_sequence,
                "run_id": self._trajectory_writer.run_id if self._trajectory_writer else "",
                "snapshot_reference": {
                    "path": str(self.events_path.with_name("semantic-state-snapshots.jsonl")),
                    "persisted_at_this_stage": (
                        stage == "POST_TURN" and self._semantic_snapshots_file is not None
                    ),
                },
                "raw_events_reference": str(self.events_path),
            })
            self._promotion_audit_file.write(json_line(report) + "\n")
            self._promotion_audit_file.flush()
        except Exception as exc:
            print(f"[AUDIT] shadow record failed: {type(exc).__name__}", flush=True)

    def _next_id(self) -> int:
        value = self._request_id
        self._request_id += 1
        return value

    def _send(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("app-server stdin is unavailable")
        if self._trajectory_writer is not None:
            self._trajectory_writer.write_raw_event({"direction": "client", "message": message})
        self.process.stdin.write(json_line(message) + "\n")
        self.process.stdin.flush()

    def _request_turn(self, message: dict[str, Any], *, timeout: float | None) -> dict[str, Any] | None:
        # Keep identity binding beyond the outer waiting deadline. Native Turn
        # completion, not an RPC ACK or timeout, releases the next-input gate.
        if self._pending_turn is not None:
            raise RuntimeError("Previous native Turn has not terminated")
        self._turn_wait = {
            "request_id": message["id"], "turn_id": None,
            "input_id": self.semantic_state.snapshot(self.thread_id).get("current_input_id"),
        }
        pending = self._turn_wait
        self._pending_turn = pending
        try:
            completion = self._request(message, self._matches_pending_turn, timeout=timeout)
            if completion is not None:
                self._pending_turn = None
            else:
                self._turn_lifecycle("wait_timeout")
            return completion
        except KeyboardInterrupt:
            # Return control deliberately, without inventing a native terminal.
            # The operator can wait, inspect or explicitly cancel this same Turn.
            self._turn_lifecycle("wait_interrupted")
            return None
        finally:
            self._turn_wait = None

    def _request(
        self,
        message: dict[str, Any],
        predicate: Callable[[dict[str, Any]], bool],
        *,
        timeout: float | None,
    ) -> dict[str, Any] | None:
        self._send(message)
        return self._wait_for(predicate, timeout)

    def _wait_for(
        self,
        predicate: Callable[[dict[str, Any]], bool],
        timeout: float | None,
    ) -> dict[str, Any] | None:
        deadline = None if timeout is None else time.monotonic() + timeout
        while deadline is None or time.monotonic() < deadline:
            try:
                label, line = self._queue.get(timeout=0.25)
            except queue.Empty:
                if self.process is not None and self.process.poll() is not None:
                    return None
                continue
            if line is None:
                continue
            if label == "stderr":
                if self._stderr_file is not None:
                    self._stderr_file.write(line + "\n")
                    self._stderr_file.flush()
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            waiting = getattr(self, "_turn_wait", None)
            if waiting is not None and message.get("id") == waiting["request_id"]:
                native = (message.get("result") or {}).get("turn", {}).get("id")
                if isinstance(native, str) and native:
                    waiting["turn_id"] = native
            terminal = message.get("method") == "turn/completed"
            params = message.get("params") or {}
            foreign_terminal = (waiting is not None and terminal and
                                params.get("threadId") == self.thread_id and
                                (waiting["turn_id"] is None or
                                 params.get("turn", {}).get("id") != waiting["turn_id"]))
            if self._events_file is not None:
                observed_at = datetime.utcnow().isoformat()
                self._events_file.write(
                    json_line({"observed_at": observed_at, "message": message}) + "\n"
                )
                self._events_file.flush()
                if self._trajectory_writer is not None:
                    self._trajectory_writer.write_raw_event(
                        {"observed_at": observed_at, "message": message},
                        raw_event_reference={"path": str(self.events_path)},
                    )
                if foreign_terminal:
                    with self.events_path.with_name("turn-correlation.jsonl").open("a", encoding="utf-8") as log:
                        log.write(json_line({
                            "reason": "terminal_not_bound_to_active_start",
                            "start_request_id": waiting["request_id"],
                            "expected_turn_id": waiting["turn_id"],
                            "observed_turn_id": params.get("turn", {}).get("id"),
                            "semantic_state_updated": False}) + chr(10))
                semantic_updates = [] if foreign_terminal else self.semantic_state.consume_raw_event(
                    {"observed_at": observed_at, "message": message},
                    raw_event_reference={"path": str(self.events_path)},
                )
                for snapshot in semantic_updates:
                    # Observation records remain in the trajectory, not terminal snapshots.
                    if snapshot.get("schema") != SEMANTIC_STATE_SCHEMA:
                        continue
                    if self._semantic_snapshots_file is not None:
                        self._semantic_snapshots_file.write(
                            json_line(
                                {
                                    "observed_at": observed_at,
                                    "event": "TURN_COMPLETED",
                                    "snapshot": snapshot,
                                }
                            )
                            + "\n"
                        )
                        self._semantic_snapshots_file.flush()
                    self._write_promotion_audit("POST_TURN", snapshot=snapshot)
            if (terminal and params.get("threadId") == self.thread_id and self._history_bridge is not None
                    and params.get("turn", {}).get("id")):
                self._history_bridge.set_compaction(params.get("turn", {}).get("id", ""), False)
            if foreign_terminal:
                continue
            prior_wait = self._input_wait_seconds
            self._handle_message(message)
            if ((message.get("method") == "item/completed" and
                    (message.get("params") or {}).get("item", {}).get("type") in
                    {"dynamicToolCall", "contextCompaction"})
                    or (message.get("method") == "rawResponseItem/completed" and
                        (message.get("params") or {}).get("item", {}).get("type") == "function_call_output")):
                self._publish_runtime_context()
            # Human think time has its own timeout and does not consume inference time.
            if deadline is not None:
                deadline += self._input_wait_seconds - prior_wait
            if predicate(message):
                return message
        return None

    def _handle_message(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        params = message.get("params") or {}
        bridge = getattr(self, "_history_bridge", None)
        if (bridge is not None and params.get("threadId") == self.thread_id
                and params.get("item", {}).get("type") == "contextCompaction"
                and method in {"item/started", "item/completed"}):
            bridge.set_compaction(params["turnId"], method == "item/started")
        if method == "error" and params.get("threadId") == self.thread_id:
            error = params.get("error") or {}
            details = error.get("additionalDetails")
            try:
                typed = json.loads(details).get("error", {}) if isinstance(details, str) else {}
            except (ValueError, AttributeError):
                typed = {}
            budget_error = (typed.get("code") == 400 and typed.get("param") == "input_tokens"
                            or typed.get("type") == "uaea_context_budget_exceeded")
            turn_id = params.get("turnId")
            stopped = getattr(self, "_context_budget_stops", set())
            waiting = getattr(self, "_turn_wait", None)
            if (budget_error and turn_id and waiting is not None
                    and turn_id == waiting["turn_id"] and turn_id not in stopped):
                self._context_budget_stops = stopped | {turn_id}
                self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "turn/interrupt",
                            "params": {"threadId": self.thread_id, "turnId": turn_id}})
                with self.events_path.with_name("context-budget-events.jsonl").open("a", encoding="utf-8") as log:
                    log.write(json_line({"state": "blocked", "reason": "context_budget",
                        "turn_id": turn_id, "task_retained": True, "workflow_completed": False,
                        "automatic_identical_retry_interrupted": True})+"\n")
                print("[UAEA] Context budget blocked; task/receipts retained. No identical automatic retry.", flush=True)
        if method == "item/tool/requestUserInput":
            self._handle_user_input_request(message)
            return
        if method == "item/tool/call":
            self._handle_tool_call(message)
            return
        if method == "thread/tokenUsage/updated":
            usage = (message.get("params") or {}).get("tokenUsage") or {}
            window = usage.get("modelContextWindow")
            last = usage.get("last") or {}
            if window:
                print(
                    f"[HARNESS] context={window} input_tokens={last.get('inputTokens')}",
                    flush=True,
                )
            return
        if method == "item/completed":
            item = (message.get("params") or {}).get("item") or {}
            if item.get("type") == "agentMessage":
                text = extract_text(item)
                if text:
                    if self.goals.mode != "off" and not (
                            self._history_bridge is not None and self._history_bridge._compaction_turn_id):
                        from harness.goal_integration import decode_final
                        try:
                            text = decode_final(text)["answer"]
                        except (ValueError, TypeError):
                            pass
                    print(f"\n[ASSISTANT]\n{text}", flush=True)
            elif item.get("type") == "dynamicToolCall":
                print(_format_dynamic_tool_result(item), flush=True)

    def _handle_user_input_request(self, message: dict[str, Any]) -> None:
        params = message.get("params") or {}
        if (not isinstance(params, dict) or params.get("threadId") != self.thread_id
                or any(not isinstance(params.get(key), str) or not params[key]
                       for key in ("threadId", "turnId", "itemId"))):
            self._send({"jsonrpc": "2.0", "id": message.get("id"),
                        "error": {"code": -32602, "message": "Interaction scope/identity mismatch"}})
            return
        identity = ":".join(params[key] for key in ("threadId", "turnId", "itemId"))
        fingerprint = json_line(params)
        prior = self._native_input_responses.get(identity)
        if prior:
            if prior[0] != fingerprint:
                self._send({"jsonrpc": "2.0", "id": message.get("id"),
                            "error": {"code": -32602, "message": "Interaction identity conflict"}})
            else:
                self._send({**prior[1], "id": message.get("id")})
            return
        started = time.monotonic()
        questions = params.get("questions") or []
        status = "awaiting_input"
        response = None
        self._pending_user_input = identity

        def journal(state, answers=None):
            record = self.semantic_state.record_interaction(
                params.get("threadId") or self.thread_id, identity,
                status=state, questions=questions, answers=answers)
            with (self.events_path.parent / "user-input-events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json_line({
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "kind": "native_interaction", "request_id": message.get("id"),
                    "thread_id": params.get("threadId"), "turn_id": params.get("turnId"),
                    "item_id": params.get("itemId"), "status": state, "record": record,
                    "authorization_established": False,
                }) + "\n")

        def alive():
            if self.process is not None and self.process.poll() is not None:
                raise EOFError("Harness process ended while waiting for input")

        try:
            journal("awaiting_input")
            print("\n[WAITING_FOR_USER] native input; no option is selected automatically.", flush=True)
            deadline = None if self.user_input_timeout is None else time.monotonic() + self.user_input_timeout

            def read(prompt):
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise TimeoutError
                return read_user_input(prompt, on_idle=alive, timeout=remaining)

            answers = collect_answers(questions, read)
            status = "answered"
            journal(status, answers)
            response = {"jsonrpc": "2.0", "id": message.get("id"), "result": {"answers": answers}}
        except ValueError:
            status = "rejected"
            journal(status)
            response = {"jsonrpc": "2.0", "id": message.get("id"),
                        "error": {"code": -32602, "message": "Unsupported native question payload"}}
        except (InputCancelled, KeyboardInterrupt, EOFError, TimeoutError) as exc:
            status = "timed_out" if isinstance(exc, TimeoutError) else "cancelled"
            journal(status)
            response = {"jsonrpc": "2.0", "id": message.get("id"),
                        "error": {"code": -32800, "message": f"User input {status}"}}
        finally:
            self._pending_user_input = None
            self._input_wait_seconds += time.monotonic() - started
        if status in {"cancelled", "timed_out"}:
            # Interrupt first; do not resume the model with an empty/default answer.
            self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "turn/interrupt",
                        "params": {"threadId": params.get("threadId"), "turnId": params.get("turnId")}})
        if response is not None:
            self._native_input_responses[identity] = (fingerprint, response)
            self._send(response)
        print(f"[USER_INPUT] {status}", flush=True)

    def _handle_tool_call(self, message: dict[str, Any]) -> None:
        params = message.get("params") or {}
        call_id = str(params.get("callId") or "")
        if call_id in self._handled_call_ids:
            return
        self._handled_call_ids.add(call_id)
        tool_name = str(params.get("tool") or "")
        print(
            f"[UAEA] tool_call tool={tool_name} arguments={json.dumps(params.get('arguments'), ensure_ascii=False)}",
            flush=True,
        )
        dispatch = None
        try:
            dispatch = self.adapter.dispatch(
                params,
                objective="H3 interactive Harness bridge manual turn",
            )
            response = dispatch.to_app_server_response()
        except Exception as exc:
            status = "validation_failed" if isinstance(exc, (ValueError, TypeError)) else "failed"
            data = {"execution_status": status, "execution_succeeded": False,
                    "reason": "tool_boundary_exception", "result_available": False}
            if dispatch is not None:
                status = "failed"
                data.update({key: dispatch.tool_result.data[key] for key in (
                    "execution_status", "execution_succeeded", "http_attempted",
                    "requested_provider", "actual_provider", "fallback_occurred",
                ) if key in dispatch.tool_result.data})
                data.update({"reason": "result_projection_failed", "error_kind": "projection_failure",
                             "retryable": False, "failure_stage": "result_projection"})
            self._send({
                "jsonrpc": "2.0", "id": message.get("id"),
                "result": {"success": False, "contentItems": [{
                    "type": "inputText", "text": json_line({
                        "ok": False, "status": status,
                        "message": f"Dynamic tool boundary raised {type(exc).__name__}",
                        "data": data,
                    }),
                }]},
            })
            return
        if self.execution_contract == "shared":
            # Shared Host already persisted the Observation; publish it before
            # replying, so a subsequent provider request cannot race its echo.
            self._publish_runtime_context()
        self._write_promotion_audit("POST_ACTION_VALIDATION")
        trace = dispatch.to_trace_metadata()
        print(
            "[UAEA] action_request "
            f"capability={trace['action_request']['capability']} "
            f"request_id={trace['action_request']['request_id']} "
            f"status={trace['execution_observation']['status']}",
            flush=True,
        )
        self._send(
            {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": response,
            }
        )

    @staticmethod
    def _read_stream(stream: Any, label: str, output: queue.Queue) -> None:
        for line in iter(stream.readline, ""):
            output.put((label, line.rstrip("\r\n")))
        output.put((label, None))


def extract_text(value: Any) -> str:
    parts: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("text"), str):
                parts.append(node["text"])
            if isinstance(node.get("content"), str):
                parts.append(node["content"])
            for child in node.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    seen: set[str] = set()
    deduped: list[str] = []
    for part in parts:
        text = part.strip()
        if text and text not in seen:
            seen.add(text)
            deduped.append(text)
    return "\n".join(deduped)


def _format_dynamic_tool_result(item: dict[str, Any]) -> str:
    tool = item.get("tool") or "unknown"
    status = item.get("status") or "unknown"
    success = item.get("success")
    text = extract_text(item.get("contentItems") or [])
    capability = ""
    message = ""
    try:
        payload = json.loads(text) if text else {}
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict):
        capability = str(payload.get("capability") or "")
        message = str(payload.get("message") or "")
    summary = message or text[:240]
    if len(summary) > 240:
        summary = summary[:240] + "..."
    return (
        "\n[UAEA] tool_result "
        f"tool={tool} capability={capability or '-'} status={status} "
        f"success={success} summary={summary}"
    )


def run(args: argparse.Namespace) -> int:
    try:
        load_web_environment()
    except WebEnvironmentError as exc:
        print(f"[WEB ENV] ERROR: {exc}", file=sys.stderr)
        return 2
    os.environ.setdefault("UAEA_REPL_INPUT_MODE", "raw")
    context_window = args.context
    base_url = getattr(args, "base_url", f"http://127.0.0.1:{DEFAULT_PORT}").rstrip("/")
    model = getattr(args, "model", DEFAULT_MODEL)
    external = getattr(args, "vllm_mode", "managed") == "external"
    if external and args.generation_diagnostics:
        raise ValueError("Generation diagnostics cannot modify a caller-owned external service")
    stamp = utc_stamp()
    result_dir = args.result_root / f"interactive-{context_window}-{stamp}"
    codex_home = args.codex_home_root / f"interactive-{context_window}-{stamp}"
    workspace = args.workspace_root / f"interactive-{context_window}-{stamp}"
    result_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    write_config(codex_home, base_url, context_window, model=model, n1x=getattr(args, "profile", "") == "n1x", reasoning_effort=getattr(args, "reasoning_effort", "none"))
    (result_dir / "connection.json").write_text(json_line({
        "vllm_mode": "external" if external else "managed",
        "endpoint": base_url, "model": model, "context_window": context_window,
        "codex_binary": str(args.codex_bin),
    }) + "\n", encoding="utf-8")

    vllm_process: subprocess.Popen[Any] | None = None
    app: InteractiveAppServer | None = None
    try:
        if external:
            print(f"[CONNECT] caller-owned vLLM endpoint={base_url}/v1 model={model}", flush=True)
            health_seconds = wait_for_external_health(base_url, model, context_window, args.health_timeout)
        else:
            ensure_endpoint_not_serving(base_url)
            print(
                "[START] vLLM 32K diagnostic "
                f"endpoint={base_url}/v1 gpu_memory_utilization={args.gpu_memory_utilization}",
                flush=True,
            )
            vllm_process = start_vllm(
                context_window,
                base_url,
                result_dir / "vllm.log",
                args.vllm_root,
                args.model_root,
                args.gpu_memory_utilization,
                generation_diagnostics_path=(result_dir / "generation-diagnostics.jsonl"
                                             if args.generation_diagnostics else None),
            )
            if args.generation_diagnostics:
                print(f"[DIAGNOSTICS] bounded generation/parser evidence: {result_dir / 'generation-diagnostics.jsonl'}", flush=True)
            health_seconds = wait_for_health(base_url, vllm_process, args.health_timeout)
        print(f"[READY] vLLM health OK in {health_seconds}s", flush=True)

        adapter = build_interactive_adapter(result_dir / "adapter")
        app = InteractiveAppServer(
            codex=args.codex_bin,
            codex_home=codex_home,
            workspace=workspace,
            base_url=base_url,
            adapter=adapter,
            events_path=result_dir / "app-server-events.jsonl",
            stderr_path=result_dir / "app-server-stderr.log",
            turn_timeout=args.turn_timeout,
            model=model,
            user_input_timeout=getattr(args, "user_input_timeout", 0),
            reasoning_effort=getattr(args, "reasoning_effort", "none"),
            execution_contract=getattr(args, "execution_contract", "legacy"),
            goal_mode=getattr(args, "goal_mode", "off"),
            goal_projection=getattr(args, "goal_projection", "optional"),
        )
        app.start()
        print(f"[READY] source-built Codex app-server thread={app.thread_id}", flush=True)
        print(f"[ARTIFACTS] {result_dir}", flush=True)
        print("[WAIT POLICY] Turn=" + ("unlimited" if app.turn_timeout is None else f"{app.turn_timeout}s")
              + "; user reply=" + ("unlimited" if app.user_input_timeout is None else f"{app.user_input_timeout}s")
              + ". Resource and transport failure detection remain enabled.", flush=True)
        print("Ctrl+C during a Turn returns to controls without confirming cancellation. "
              "Use /turn status, /turn wait, /turn cancel.", flush=True)
        print("Type exit or quit to stop app-server"
              + ("; external vLLM remains running.\n" if external else " and managed vLLM.\n"), flush=True)
        while True:
            try:
                user_input = read_user_input(
                    "[USER] ", on_idle=app.poll_pending_turn if app._pending_turn is not None else None,
                ).strip()
            except (EOFError, KeyboardInterrupt):
                print("", flush=True)
                break
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "/exit", "/quit"}:
                break
            app.run_turn(user_input)
        return 0
    finally:
        if app is not None:
            app.close()
        if external:
            print("[STOP] app-server stopped; external vLLM left running", flush=True)
        else:
            returncode = stop_process(vllm_process)
            print(f"[STOP] app-server stopped; managed vLLM returncode={returncode}", flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    from urllib.parse import urlsplit
    from harness.version_manifest import current_platform, selected_harness

    parser = argparse.ArgumentParser(description="Interactive UAEA H3 Harness bridge REPL.")
    parser.add_argument("--profile", choices=("h3", "n1x"),
                        default="n1x" if current_platform() == "linux-aarch64" else "h3")
    parser.add_argument("--context", type=int, choices=(32768, 65536))
    parser.add_argument("--experimental-context-64k", action="store_true",
                        help="Explicit N1X external-service experiment; does not change profile defaults or configure vLLM.")
    parser.add_argument("--vllm-mode", choices=("managed", "external"))
    parser.add_argument("--base-url", help="Loopback server root URL, without /v1")
    parser.add_argument("--model", help="Exact served model name")
    parser.add_argument("--reasoning-effort", choices=("none", "low", "medium", "high"), default="none",
                        help="Forwarded to Harness config and turn/start; default preserves existing profiles.")
    parser.add_argument("--result-root", type=Path)
    parser.add_argument("--codex-bin", type=Path)
    parser.add_argument("--codex-home-root", type=Path)
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--vllm-root", type=Path, default=DEFAULT_VLLM_ROOT)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.75,
                        help="Managed H3 profile only; external service is not reconfigured.")
    parser.add_argument("--health-timeout", type=int, default=DEFAULT_HEALTH_TIMEOUT)
    parser.add_argument("--turn-timeout", type=int, default=DEFAULT_TURN_TIMEOUT,
                        help="Turn wait seconds; default 0 waits until terminal/interruption. Positive values opt into a finite experiment wait.")
    parser.add_argument("--user-input-timeout", type=int, default=0,
                        help="Native user reply wait seconds; default 0 has no deadline or auto-selection.")
    parser.add_argument("--execution-contract", choices=("legacy", "shared"), default="legacy",
                        help="Opt-in shared read-only execution contract; legacy is the rollback path.")
    parser.add_argument("--goal-projection", choices=("none", "optional"), default="optional",
                        help="none: passive Goal collection only; optional: bounded Goal context, no forced format.")
    parser.add_argument("--goal-mode", choices=("off", "shadow", "adopt"), default="off",
                        help="Opt-in Goal shadow/adoption experiment; explicit Host /goal controls only.")
    parser.add_argument("--generation-diagnostics", action="store_true",
                        help="Managed service only; no parser behavior changes.")
    args = parser.parse_args(argv)
    if args.turn_timeout < 0 or args.user_input_timeout < 0:
        parser.error("--turn-timeout and --user-input-timeout must be non-negative (0 disables the wait deadline)")
    n1x = args.profile == "n1x"
    host = current_platform()
    required_host = "linux-aarch64" if n1x else "linux-x86_64"
    if host != required_host:
        parser.error(f"Profile {args.profile} requires {required_host}; current platform is {host}")
    if args.codex_bin is None:
        args.codex_bin = Path(selected_harness()["binary"])
    from harness.version_manifest import identify_harness
    selected_target = identify_harness(args.codex_bin).get("build_target")
    expected_target = "aarch64-unknown-linux-gnu" if n1x else "x86_64-unknown-linux-gnu"
    if selected_target not in (None, expected_target):
        parser.error(f"Harness binary target {selected_target} is incompatible with profile {args.profile}")
    n1x_profile = (json.loads((PROJECT_ROOT / "harness/n1x_profile.json").read_text())
                    if n1x else {})
    local = Path.home() / "uaea-n1x" / "runs"
    tag = selected_harness()["tag"]
    defaults = {
        "context": n1x_profile["context_window"] if n1x else DEFAULT_CONTEXT_WINDOW,
        "vllm_mode": n1x_profile["vllm_mode"] if n1x else "managed",
        "base_url": n1x_profile["base_url"] if n1x else f"http://127.0.0.1:{DEFAULT_PORT}",
        "model": n1x_profile["model"] if n1x else DEFAULT_MODEL,
        "result_root": local / "h3-results" if n1x else DEFAULT_RESULT_ROOT,
        "codex_home_root": local / "codex-home" / tag if n1x else DEFAULT_CODEX_HOME_ROOT,
        "workspace_root": local / "codex-workspace" / tag if n1x else DEFAULT_WORKSPACE_ROOT,
    }
    for name, value in defaults.items():
        if getattr(args, name) is None:
            setattr(args, name, value)
    args.base_url = args.base_url.rstrip("/")
    parsed = urlsplit(args.base_url)
    try:
        port = parsed.port
    except ValueError:
        parser.error("Invalid endpoint port")
    if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost")
            or not port or port == 8001 or parsed.path or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        parser.error("Use a loopback HTTP server root with an explicit port, excluding frozen 8001")
    if not args.model.strip():
        parser.error("Model name cannot be empty")
    if args.vllm_mode == "managed" and (args.base_url != f"http://127.0.0.1:{DEFAULT_PORT}" or args.model != DEFAULT_MODEL):
        parser.error("Managed H3 keeps its validated endpoint/model; use external mode for overrides")
    if args.context == 65536 and not (n1x and args.vllm_mode == "external" and args.experimental_context_64k):
        parser.error("65536 requires N1X external mode and --experimental-context-64k")
    if args.experimental_context_64k and args.context != 65536:
        parser.error("--experimental-context-64k requires --context 65536")
    if n1x and (args.vllm_mode != "external" or args.context not in (32768, 65536)):
        parser.error("N1X requires an external service with a supported explicit context")
    if args.vllm_mode == "external" and args.generation_diagnostics:
        parser.error("Generation diagnostics require a managed service")
    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
