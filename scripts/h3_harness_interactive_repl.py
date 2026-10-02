from __future__ import annotations

import argparse
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
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
)
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
    write_config,
)


DEFAULT_CONTEXT_WINDOW = 32768
DEFAULT_TURN_TIMEOUT = 300


RUNTIME_FACT_SUMMARY = runtime_fact_summary()


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
                    "Only cite URLs returned by web.search or web.fetch."
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
                            "description": "Whether UAEA may use another provider when the requested provider is unsupported or unavailable. Required whenever provider is set; set false when the user forbids fallback.",
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
                    "Use this after web.search when a candidate source needs verification or summary."
                ),
                input_schema={
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
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
        turn_timeout: int,
    ) -> None:
        self.codex = codex
        self.codex_home = codex_home
        self.workspace = workspace
        self.base_url = base_url.rstrip("/")
        self.adapter = adapter
        self.events_path = events_path
        self.stderr_path = stderr_path
        self.turn_timeout = turn_timeout
        self._dynamic_tools: list[dict[str, Any]] = []
        self.process: subprocess.Popen[str] | None = None
        self.thread_id = ""
        self._queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self._request_id = 1
        self._handled_call_ids: set[str] = set()
        self._events_file: Any = None
        self._stderr_file: Any = None
        self._semantic_snapshots_file: Any = None
        self.semantic_state = HarnessSemanticStateAdapter()
        self.adapter.bind_semantic_state_adapter(self.semantic_state)

    def start(self) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._events_file = self.events_path.open("w", encoding="utf-8")
        self._stderr_file = self.stderr_path.open("w", encoding="utf-8")
        self._semantic_snapshots_file = self.events_path.with_name(
            "semantic-state-snapshots.jsonl"
        ).open("w", encoding="utf-8")
        env = os.environ.copy()
        env["CODEX_HOME"] = str(self.codex_home)
        for name in (
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "CODEX_API_KEY",
            "CHATGPT_API_KEY",
            "SERPAPI_KEY",
        ):
            env.pop(name, None)
        self.process = subprocess.Popen(
            [
                str(self.codex),
                "app-server",
                "--stdio",
                "-c",
                f'model_providers.uaea_local_vllm.base_url="{self.base_url}/v1"',
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
                "method": "thread/start",
                "params": {
                    "model": DEFAULT_MODEL,
                    "modelProvider": "uaea_local_vllm",
                    "cwd": str(self.workspace),
                    "ephemeral": True,
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "personality": "none",
                    "experimentalRawEvents": True,
                    "dynamicTools": self._dynamic_tools,
                },
            },
            lambda message: message.get("id") == thread_id,
            timeout=60,
        )
        if thread is None or thread.get("error") is not None:
            raise RuntimeError(f"thread/start failed: {thread}")
        self.thread_id = str(thread["result"]["thread"]["id"])

    def run_turn(self, text: str) -> None:
        request_id = self._next_id()
        semantic_projection = self.semantic_state.prepare_turn(self.thread_id, text)
        print("\n[HARNESS] turn/start", flush=True)
        print(f"[UAEA] runtime_facts injected: {RUNTIME_FACT_SUMMARY}", flush=True)
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
        completion = self._request(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "turn/start",
                "params": {
                    "threadId": self.thread_id,
                    "input": [{"type": "text", "text": text}],
                    "effort": "none",
                    "model": DEFAULT_MODEL,
                    "additionalContext": turn_context_payload(
                        self._dynamic_tools,
                        semantic_projection=semantic_projection.payload,
                    ),
                },
            },
            lambda message: (
                message.get("method") == "turn/completed"
                and message.get("params", {}).get("threadId") == self.thread_id
            )
            or (message.get("id") == request_id and message.get("error") is not None),
            timeout=self.turn_timeout,
        )
        if completion is None:
            print("[HARNESS] turn timeout", flush=True)
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
            if handle is not None:
                handle.flush()
                handle.close()
        if self._semantic_snapshots_file is not None:
            self._semantic_snapshots_file.flush()
            self._semantic_snapshots_file.close()
            self._semantic_snapshots_file = None

    def _next_id(self) -> int:
        value = self._request_id
        self._request_id += 1
        return value

    def _send(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("app-server stdin is unavailable")
        self.process.stdin.write(json_line(message) + "\n")
        self.process.stdin.flush()

    def _request(
        self,
        message: dict[str, Any],
        predicate: Callable[[dict[str, Any]], bool],
        *,
        timeout: int,
    ) -> dict[str, Any] | None:
        self._send(message)
        return self._wait_for(predicate, timeout)

    def _wait_for(
        self,
        predicate: Callable[[dict[str, Any]], bool],
        timeout: int,
    ) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
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
            if self._events_file is not None:
                observed_at = datetime.utcnow().isoformat()
                self._events_file.write(
                    json_line({"observed_at": observed_at, "message": message}) + "\n"
                )
                self._events_file.flush()
                semantic_updates = self.semantic_state.consume_raw_event(
                    {"observed_at": observed_at, "message": message},
                    raw_event_reference={"path": str(self.events_path)},
                )
                for snapshot in semantic_updates:
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
            self._handle_message(message)
            if predicate(message):
                return message
        return None

    def _handle_message(self, message: dict[str, Any]) -> None:
        method = message.get("method")
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
                    print(f"\n[ASSISTANT]\n{text}", flush=True)
            elif item.get("type") == "dynamicToolCall":
                print(_format_dynamic_tool_result(item), flush=True)

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
        dispatch = self.adapter.dispatch(
            params,
            objective="H3 interactive Harness bridge manual turn",
        )
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
                "result": dispatch.to_app_server_response(),
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
    base_url = f"http://127.0.0.1:{DEFAULT_PORT}"
    stamp = utc_stamp()
    result_dir = args.result_root / f"interactive-{context_window}-{stamp}"
    codex_home = args.codex_home_root / f"interactive-{context_window}-{stamp}"
    workspace = args.workspace_root / f"interactive-{context_window}-{stamp}"
    result_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    write_config(codex_home, base_url, context_window)

    vllm_process: subprocess.Popen[Any] | None = None
    app: InteractiveAppServer | None = None
    try:
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
        )
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
        )
        app.start()
        print(f"[READY] source-built Codex app-server thread={app.thread_id}", flush=True)
        print(f"[ARTIFACTS] {result_dir}", flush=True)
        print("Type exit or quit to stop 8002 and app-server.\n", flush=True)
        while True:
            try:
                user_input = read_user_input("[USER] ").strip()
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
        returncode = stop_process(vllm_process)
        print(f"[STOP] app-server stopped; vLLM returncode={returncode}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive UAEA H3 Harness bridge REPL on diagnostic 32K vLLM."
    )
    parser.add_argument("--context", type=int, default=DEFAULT_CONTEXT_WINDOW, choices=(32768,))
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--codex-bin", type=Path, default=DEFAULT_CODEX_BIN)
    parser.add_argument("--codex-home-root", type=Path, default=DEFAULT_CODEX_HOME_ROOT)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE_ROOT)
    parser.add_argument("--vllm-root", type=Path, default=DEFAULT_VLLM_ROOT)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument(
        "--gpu-memory-utilization",
        type=float,
        default=0.75,
        help="H3-A2 validated value for 32K manual interaction.",
    )
    parser.add_argument("--health-timeout", type=int, default=DEFAULT_HEALTH_TIMEOUT)
    parser.add_argument("--turn-timeout", type=int, default=DEFAULT_TURN_TIMEOUT)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
