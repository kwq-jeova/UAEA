from __future__ import annotations

import argparse
import json
import os
import queue
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
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
from runtime.capability import CapabilityMetadata, ToolResult  # noqa: E402
from runtime.ledger import LedgerStub  # noqa: E402
from runtime.sandbox import Sandbox  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402


DEFAULT_RESULT_ROOT = Path("/mnt/d/UAEA-runtime/h3-results")
DEFAULT_CODEX_BIN = Path(
    "/mnt/d/UAEA-runtime/codex/source-rust-v0.154.0-wsl-x86_64/codex"
)
DEFAULT_CODEX_HOME_ROOT = Path("/mnt/d/UAEA-runtime/codex-home-h3")
DEFAULT_WORKSPACE_ROOT = Path("/mnt/d/UAEA-runtime/codex-workspace-h3")
DEFAULT_VLLM_ROOT = Path("/opt/uaea/vllm_env")
DEFAULT_MODEL_ROOT = Path("/opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ")
DEFAULT_MODEL = "qwen25-14b-awq"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8002
DEFAULT_GPU_MEMORY_UTILIZATION = 0.7
DEFAULT_HEALTH_TIMEOUT = 600
DEFAULT_TURN_TIMEOUT = 300


@dataclass(frozen=True)
class Workload:
    name: str
    prompt: str
    expected_tool_calls: int


WORKLOADS = (
    Workload(
        "ordinary_no_tool",
        "Answer in one short sentence: what is post-training?",
        0,
    ),
    Workload(
        "mock_single",
        (
            "Call the mock_external_operation tool exactly once with text hello, "
            "then report the returned result in one short sentence."
        ),
        1,
    ),
    Workload(
        "document_read_section",
        (
            "Call the read_section tool exactly once with path README.md and "
            "section_index 1. Then summarize the returned section in one short "
            "sentence."
        ),
        1,
    ),
    Workload(
        "mock_five_calls",
        (
            "Call mock_external_operation exactly five times, once each with "
            "text task-1, task-2, task-3, task-4, and task-5. Do not answer "
            "until all five tool calls have completed. Then report the count "
            "in one short sentence."
        ),
        5,
    ),
    Workload(
        "controlled_failure",
        (
            "Call the mock_failure tool exactly once with text failure-test, "
            "then briefly report that the tool failed and include its error."
        ),
        1,
    ),
)
WORKLOADS_BY_NAME = {workload.name: workload for workload in WORKLOADS}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_line(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def write_config(home: Path, base_url: str, context_window: int) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.toml").write_text(
        "\n".join(
            [
                'model_provider = "uaea_local_vllm"',
                f'model = "{DEFAULT_MODEL}"',
                'model_reasoning_effort = "none"',
                f"model_context_window = {context_window}",
                "project_doc_max_bytes = 0",
                "skip_host_skill_discovery = true",
                "disable_response_storage = true",
                "",
                "[features]",
                "skill_search = false",
                "plugins = false",
                "shell_tool = false",
                "unified_exec = false",
                "browser_use = false",
                "computer_use = false",
                "",
                "[model_providers.uaea_local_vllm]",
                'name = "UAEA local vLLM"',
                f'base_url = "{base_url}/v1"',
                'wire_api = "responses"',
                "requires_openai_auth = false",
                "",
            ]
        ),
        encoding="utf-8",
    )


def build_adapter(adapter_root: Path) -> HarnessDynamicToolAdapter:
    sandbox_root = adapter_root / "sandbox"
    trace_root = adapter_root / "traces"
    sandbox_root.mkdir(parents=True, exist_ok=True)
    trace_root.mkdir(parents=True, exist_ok=True)
    (sandbox_root / "README.md").write_text(
        "# H3 Fixture\n\n## 1. First section\n\n"
        "This is a deterministic H3 document fixture.\n",
        encoding="utf-8",
    )

    registry = ToolRegistry(Sandbox(adapter_root, sandbox_root), LedgerStub(trace_root))

    def echo(arguments: dict[str, Any], objective: str) -> ToolResult:
        return ToolResult(
            True,
            "mock external operation completed",
            {
                "received": dict(arguments),
                "objective": objective,
                "external_ref": "mock://external/h3",
            },
        )

    def failure(arguments: dict[str, Any], objective: str) -> ToolResult:
        return ToolResult(
            False,
            "controlled H3 fixture failure",
            {
                "received": dict(arguments),
                "objective": objective,
                "error_code": "controlled_h3_failure",
            },
        )

    registry.register_capability(
        CapabilityMetadata(
            name="mock.external_operation",
            tool_name="mock_external_operation",
            version="0.1",
            permission="external",
            produces_observation=True,
            context_cost="low",
            future_phase="h3-characterization",
        ),
        echo,
    )
    registry.register_capability(
        CapabilityMetadata(
            name="mock.controlled_failure",
            tool_name="mock_failure",
            version="0.1",
            permission="external",
            produces_observation=True,
            context_cost="low",
            future_phase="h3-characterization",
        ),
        failure,
    )
    return HarnessDynamicToolAdapter(
        registry,
        [
            DynamicToolBinding.from_registry(
                registry,
                "mock.external_operation",
                description="Run the deterministic H3 external fixture.",
                input_schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
            ),
            DynamicToolBinding.from_registry(
                registry,
                "document.read_section",
                description="Read one Markdown section from the H3 fixture.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "section_index": {"type": "integer"},
                    },
                    "required": ["path", "section_index"],
                    "additionalProperties": False,
                },
            ),
            DynamicToolBinding.from_registry(
                registry,
                "mock.controlled_failure",
                description="Return a deterministic controlled failure.",
                input_schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
            ),
        ],
        max_output_chars=4000,
    )


def proc_rss_kib(pid: int | None) -> int | None:
    if not pid:
        return None
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    match = re.search(r"^VmRSS:\s+(\d+)\s+kB$", status, flags=re.MULTILINE)
    return int(match.group(1)) if match else None


def gpu_snapshot() -> dict[str, Any] | None:
    nvidia_smi = shutil.which("nvidia-smi") or "/usr/lib/wsl/lib/nvidia-smi"
    command = [
        nvidia_smi,
        "--query-gpu=name,memory.total,memory.used,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(
            command,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None
    if not output:
        return None
    values = [value.strip() for value in output.splitlines()[0].split(",")]
    if len(values) != 4:
        return {"raw": output}
    try:
        return {
            "name": values[0],
            "memory_total_mib": int(float(values[1])),
            "memory_used_mib": int(float(values[2])),
            "utilization_gpu_percent": float(values[3]),
        }
    except ValueError:
        return {"raw": output}


class MetricsSampler:
    def __init__(self, vllm_pid: int) -> None:
        self.vllm_pid = vllm_pid
        self.codex_pid: int | None = None
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def set_codex_pid(self, pid: int | None) -> None:
        self.codex_pid = pid

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            sample = {
                "observed_at": utc_now(),
                "gpu": gpu_snapshot(),
                "vllm_rss_kib": proc_rss_kib(self.vllm_pid),
                "codex_rss_kib": proc_rss_kib(self.codex_pid),
                "runner_rss_kib": proc_rss_kib(os.getpid()),
            }
            self.samples.append(sample)
            self._stop.wait(1.0)

    def summary(self) -> dict[str, Any]:
        gpu_samples = [
            sample["gpu"]
            for sample in self.samples
            if isinstance(sample.get("gpu"), dict)
            and sample["gpu"].get("memory_used_mib") is not None
        ]
        vllm_rss = [
            sample["vllm_rss_kib"]
            for sample in self.samples
            if sample.get("vllm_rss_kib") is not None
        ]
        codex_rss = [
            sample["codex_rss_kib"]
            for sample in self.samples
            if sample.get("codex_rss_kib") is not None
        ]
        return {
            "sample_count": len(self.samples),
            "gpu_before_or_first": gpu_samples[0] if gpu_samples else None,
            "gpu_peak_memory_used_mib": (
                max(item["memory_used_mib"] for item in gpu_samples)
                if gpu_samples
                else None
            ),
            "gpu_after_or_last": gpu_samples[-1] if gpu_samples else None,
            "vllm_peak_rss_kib": max(vllm_rss) if vllm_rss else None,
            "codex_peak_rss_kib": max(codex_rss) if codex_rss else None,
            "last_sample": self.samples[-1] if self.samples else None,
        }


class AppServerClient:
    def __init__(
        self,
        codex: Path,
        codex_home: Path,
        workspace: Path,
        base_url: str,
        adapter: HarnessDynamicToolAdapter,
        raw_events_path: Path,
        stderr_path: Path,
        turn_timeout: int,
    ) -> None:
        self.codex = codex
        self.codex_home = codex_home
        self.workspace = workspace
        self.base_url = base_url.rstrip("/")
        self.adapter = adapter
        self.raw_events_path = raw_events_path
        self.stderr_path = stderr_path
        self.turn_timeout = turn_timeout
        self.process: subprocess.Popen[str] | None = None
        self.events: list[dict[str, Any]] = []
        self.dispatches: list[dict[str, Any]] = []
        self._queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self._reader_threads: list[threading.Thread] = []
        self._handled_call_ids: set[str] = set()
        self._request_id = 1
        self._raw_events_file: Any = None
        self._stderr_file: Any = None
        self.current_workload: str | None = None

    def start(self) -> dict[str, Any]:
        self.raw_events_path.parent.mkdir(parents=True, exist_ok=True)
        self._raw_events_file = self.raw_events_path.open("w", encoding="utf-8")
        self._stderr_file = self.stderr_path.open("w", encoding="utf-8")
        env = os.environ.copy()
        env["CODEX_HOME"] = str(self.codex_home)
        for name in (
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "CODEX_API_KEY",
            "CHATGPT_API_KEY",
        ):
            env.pop(name, None)
        started = time.monotonic()
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
            thread = threading.Thread(
                target=self._read_stream,
                args=(stream, label, self._queue),
                daemon=True,
            )
            thread.start()
            self._reader_threads.append(thread)
        response = self._request(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "uaea-h3-context-characterization",
                        "title": "UAEA H3-A",
                        "version": "0.1.0",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            },
            lambda message: message.get("id") == 1,
            timeout=60,
        )
        if response is None:
            raise RuntimeError("app-server initialize timeout")
        return {
            "startup_seconds": round(time.monotonic() - started, 3),
            "initialize_response": response,
            "pid": self.process.pid,
        }

    def run_workload(self, workload: Workload) -> dict[str, Any]:
        if self.process is None:
            raise RuntimeError("app-server is not running")
        self.current_workload = workload.name
        started = time.monotonic()
        start_event_index = len(self.events)
        thread_request_id = self._next_id()
        thread_response = self._request(
            {
                "jsonrpc": "2.0",
                "id": thread_request_id,
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
                    "dynamicTools": self.adapter.dynamic_tools(),
                },
            },
            lambda message: message.get("id") == thread_request_id,
            timeout=60,
        )
        if thread_response is None:
            return self._failed_workload(
                workload,
                started,
                start_event_index,
                "thread/start timeout",
            )
        if thread_response.get("error") is not None:
            return self._failed_workload(
                workload,
                started,
                start_event_index,
                f"thread/start error: {thread_response['error']}",
            )
        thread_id = thread_response["result"]["thread"]["id"]
        turn_request_id = self._next_id()
        turn_started = time.monotonic()
        turn_response = self._request(
            {
                "jsonrpc": "2.0",
                "id": turn_request_id,
                "method": "turn/start",
                "params": {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": workload.prompt}],
                    "effort": "none",
                    "model": DEFAULT_MODEL,
                },
            },
            lambda message: (
                (
                    message.get("method") == "turn/completed"
                    and message.get("params", {}).get("threadId") == thread_id
                )
                or (
                    message.get("id") == turn_request_id
                    and message.get("error") is not None
                )
            ),
            timeout=self.turn_timeout,
        )
        result = self._summarize_workload(
            workload,
            thread_id,
            started,
            turn_started,
            start_event_index,
            turn_response,
        )
        self.current_workload = None
        return result

    def _failed_workload(
        self,
        workload: Workload,
        started: float,
        start_event_index: int,
        error: str,
    ) -> dict[str, Any]:
        self.current_workload = None
        return {
            "name": workload.name,
            "prompt": workload.prompt,
            "expected_tool_calls": workload.expected_tool_calls,
            "status": "failure",
            "error": error,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "events": self.events[start_event_index:],
            "tool_calls": [],
            "token_updates": [],
            "compaction_events": [],
        }

    def _summarize_workload(
        self,
        workload: Workload,
        thread_id: str,
        started: float,
        turn_started: float,
        start_event_index: int,
        completion: dict[str, Any] | None,
    ) -> dict[str, Any]:
        events = self.events[start_event_index:]
        turn_id = None
        token_updates = []
        compaction_events = []
        agent_messages = []
        raw_response_times = []
        for event in events:
            message = event["message"]
            method = message.get("method")
            params = message.get("params") or {}
            if method == "turn/started":
                turn_id = params.get("turnId") or turn_id
            if method == "thread/tokenUsage/updated":
                usage = params.get("tokenUsage") or {}
                if params.get("threadId") == thread_id:
                    token_updates.append(
                        {
                            "observed_at": event["observed_at"],
                            "turn_id": params.get("turnId"),
                            "usage": usage,
                        }
                    )
            if method in {"thread/compacted", "thread/compaction/started"}:
                if params.get("threadId") == thread_id:
                    compaction_events.append(
                        {"observed_at": event["observed_at"], "method": method, "params": params}
                    )
            if method == "item/completed":
                item = params.get("item") or {}
                item_type = item.get("type")
                if item_type in {"contextCompaction", "compaction"}:
                    compaction_events.append(
                        {"observed_at": event["observed_at"], "method": method, "item": item}
                    )
                if item_type == "agentMessage":
                    agent_messages.append(item)
            if method == "rawResponse/completed":
                raw_response_times.append(event["observed_monotonic"])
        completion_params = (completion or {}).get("params") or {}
        if completion_params.get("turnId"):
            turn_id = completion_params["turnId"]
        first_usage = token_updates[0]["usage"] if token_updates else {}
        first_last = first_usage.get("last") or {}
        model_context = first_usage.get("modelContextWindow")
        tool_calls = [
            dispatch
            for dispatch in self.dispatches
            if dispatch.get("workload") == workload.name
            and (
                not turn_id
                or dispatch.get("turn_id") == turn_id
                or dispatch.get("thread_id") == thread_id
            )
        ]
        first_compaction_index = None
        if compaction_events:
            first_compaction_index = min(
                index
                for index, event in enumerate(events)
                if event["observed_at"] == compaction_events[0]["observed_at"]
            )
        token_before_compaction = None
        if first_compaction_index is not None:
            before = [
                update
                for update in token_updates
                if any(
                    event["observed_at"] == update["observed_at"]
                    and index < first_compaction_index
                    for index, event in enumerate(events)
                )
            ]
            if before:
                token_before_compaction = before[-1]
        status = "completed"
        if completion is None:
            status = "failure"
        if completion and completion.get("error") is not None:
            status = "failure"
        expected_tool_calls = workload.expected_tool_calls
        observed_tool_calls = len(tool_calls)
        return {
            "name": workload.name,
            "prompt": workload.prompt,
            "expected_tool_calls": expected_tool_calls,
            "thread_id": thread_id,
            "turn_id": turn_id,
            "status": status,
            "task_success": (
                status == "completed"
                and observed_tool_calls == expected_tool_calls
            ),
            "completion": completion,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "first_response_seconds": (
                round(raw_response_times[0] - turn_started, 3)
                if raw_response_times
                else None
            ),
            "model_context_window": model_context,
            "initial_input_tokens": first_last.get("inputTokens"),
            "initial_token_usage": first_last,
            "initial_occupancy": (
                first_last.get("inputTokens") / model_context
                if first_last.get("inputTokens") is not None and model_context
                else None
            ),
            "token_updates": token_updates,
            "first_compaction_turn": (
                compaction_events[0].get("params", {}).get("turnId")
                if compaction_events
                else None
            ),
            "input_tokens_before_first_compaction": (
                (token_before_compaction or {}).get("usage", {})
                .get("last", {})
                .get("inputTokens")
                if token_before_compaction
                else None
            ),
            "tool_calls_before_first_compaction": (
                len(tool_calls) if compaction_events else None
            ),
            "compaction_occurred": bool(compaction_events),
            "compaction_events": compaction_events,
            "tool_calls": tool_calls,
            "observed_tool_calls": observed_tool_calls,
            "agent_messages": agent_messages,
            "raw_response_completed_count": len(raw_response_times),
            "events": events,
        }

    def close(self) -> None:
        if self.process is None:
            return
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
        for thread in self._reader_threads:
            thread.join(timeout=2)
        if self._raw_events_file is not None:
            self._raw_events_file.flush()
            self._raw_events_file.close()
        if self._stderr_file is not None:
            self._stderr_file.flush()
            self._stderr_file.close()
        self.process = None

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
            event = {
                "observed_at": utc_now(),
                "observed_monotonic": time.monotonic(),
                "label": label,
                "message": message,
            }
            self.events.append(event)
            if self._raw_events_file is not None:
                self._raw_events_file.write(json_line(event) + "\n")
                self._raw_events_file.flush()
            self._handle_dynamic_tool(message)
            if predicate(message):
                return message
        return None

    def _handle_dynamic_tool(self, message: dict[str, Any]) -> None:
        if message.get("method") != "item/tool/call":
            return
        params = message.get("params") or {}
        call_id = str(params.get("callId") or "")
        if call_id in self._handled_call_ids:
            return
        self._handled_call_ids.add(call_id)
        started = time.monotonic()
        dispatch = self.adapter.dispatch(
            params,
            objective=f"H3-A workload: {self.current_workload or 'unknown'}",
        )
        dispatch_record = {
            "workload": self.current_workload,
            "thread_id": dispatch.thread_id,
            "turn_id": dispatch.turn_id,
            "call_id": dispatch.call_id,
            "tool_name": dispatch.tool_name,
            "capability": dispatch.action_request.capability,
            "ok": dispatch.ok,
            "status": dispatch.observation.status,
            "elapsed_seconds": round(time.monotonic() - started, 4),
            "trace": dispatch.to_trace_metadata(),
        }
        self.dispatches.append(dispatch_record)
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


def wait_for_health(base_url: str, process: subprocess.Popen[Any], timeout: int) -> float:
    started = time.monotonic()
    endpoint = f"{base_url.rstrip('/')}/v1/models"
    deadline = started + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"vLLM exited with code {process.returncode} before health; "
                "inspect vllm.log"
            )
        try:
            with urllib.request.urlopen(endpoint, timeout=5) as response:
                if response.status == 200:
                    return round(time.monotonic() - started, 3)
        except (OSError, urllib.error.URLError):
            time.sleep(2)
    raise RuntimeError(f"vLLM health timeout after {timeout}s: {endpoint}")


def ensure_endpoint_not_serving(base_url: str) -> None:
    endpoint = f"{base_url.rstrip('/')}/v1/models"
    try:
        with urllib.request.urlopen(endpoint, timeout=2):
            raise RuntimeError(
                f"diagnostic endpoint is already serving: {endpoint}; "
                "refusing to reuse an existing 8002 process"
            )
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"diagnostic endpoint is already serving HTTP {exc.code}: {endpoint}"
        ) from exc
    except urllib.error.URLError:
        return


def start_vllm(
    context_window: int,
    base_url: str,
    log_path: Path,
    vllm_root: Path,
    model_root: Path,
    gpu_memory_utilization: float,
    *,
    generation_diagnostics_path: Path | None = None,
) -> subprocess.Popen[Any]:
    vllm_binary = vllm_root / "bin" / "vllm"
    if not vllm_binary.is_file():
        raise RuntimeError(f"vLLM executable not found: {vllm_binary}")
    if not (model_root / "config.json").is_file():
        raise RuntimeError(f"model config not found: {model_root}")
    env = os.environ.copy()
    env["HF_HOME"] = env.get("HF_HOME", "/opt/uaea-models/cache")
    env.pop("SERPAPI_KEY", None)
    env["CUDA_HOME"] = env.get(
        "CUDA_HOME",
        str(vllm_root / "lib" / "python3.12" / "site-packages" / "nvidia" / "cu13"),
    )
    env["PATH"] = (
        f"{vllm_root}/bin:{env['CUDA_HOME']}/bin:"
        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    )
    env["VLLM_USE_V2_MODEL_RUNNER"] = "0"
    env["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")
    command = [str(vllm_binary)]
    if generation_diagnostics_path is not None:
        command = [str(vllm_root / "bin" / "python"),
                   str(PROJECT_ROOT / "scripts" / "h3_vllm_diagnostic_launcher.py"),
                   "--diagnostic-path", str(generation_diagnostics_path)]
    process = subprocess.Popen(
        command + [
            "serve",
            str(model_root),
            "--served-model-name",
            DEFAULT_MODEL,
            "--dtype",
            "half",
            "--max-model-len",
            str(context_window),
            "--gpu-memory-utilization",
            str(gpu_memory_utilization),
            "--host",
            DEFAULT_HOST,
            "--port",
            str(DEFAULT_PORT),
            "--enable-auto-tool-choice",
            "--tool-call-parser",
            "hermes",
        ],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    process._uaea_log_file = log_file  # type: ignore[attr-defined]
    return process


def stop_process(process: subprocess.Popen[Any] | None) -> int | None:
    if process is None:
        return None
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                process.kill()
            process.wait(timeout=15)
    log_file = getattr(process, "_uaea_log_file", None)
    if log_file is not None:
        log_file.flush()
        log_file.close()
    return process.returncode


def parse_vllm_log(log_path: Path) -> dict[str, Any]:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    matches = re.findall(r"GPU KV cache size:\s*([\d,]+)\s*tokens", text)
    concurrency = re.findall(
        r"Maximum concurrency for [^:]+:\s*([\d.]+)x",
        text,
    )
    return {
        "gpu_kv_cache_size_tokens": (
            int(matches[-1].replace(",", "")) if matches else None
        ),
        "maximum_concurrency": float(concurrency[-1]) if concurrency else None,
        "oom_or_rejection": bool(
            re.search(r"\b(OutOfMemoryError|CUDA out of memory|ValueError)\b", text)
        ),
        "log_tail": text[-6000:],
    }


def summarize_profile(
    context_window: int,
    result_dir: Path,
    vllm_health_seconds: float | None,
    vllm_returncode: int | None,
    app_server_info: dict[str, Any] | None,
    workloads: list[dict[str, Any]],
    metrics: MetricsSampler | None,
    gpu_memory_utilization: float,
) -> dict[str, Any]:
    return {
        "phase": "H3-A",
        "profile": context_window,
        "started_at": utc_now(),
        "physical_boundary": {
            "gpu": "NVIDIA RTX 5090 D v2",
            "vram_gb_class": 24,
            "single_gpu": True,
            "model": "Qwen2.5-14B-Instruct-AWQ",
            "quantization": "AWQ / approximately 4-bit",
            "dtype": "half",
            "gpu_memory_utilization": gpu_memory_utilization,
            "vllm_version": "0.26.0",
            "codex_source_commit": "6b9826e3aa83b1a5947db50f4332cb9c65f1b340",
        },
        "configured": {
            "vllm_max_model_len": context_window,
            "codex_model_context_window": context_window,
            "gpu_memory_utilization": gpu_memory_utilization,
            "endpoint": f"http://127.0.0.1:{DEFAULT_PORT}/v1",
            "tool_call_parser": "hermes",
            "auto_tool_choice": True,
        },
        "vllm": {
            "health_seconds": vllm_health_seconds,
            "returncode": vllm_returncode,
            **parse_vllm_log(result_dir / "vllm.log"),
        },
        "app_server": app_server_info,
        "workloads": workloads,
        "metrics": metrics.summary() if metrics else None,
        "artifacts": {
            "raw_app_server_events": str(result_dir / "app-server-events.jsonl"),
            "app_server_stderr": str(result_dir / "app-server-stderr.log"),
            "vllm_log": str(result_dir / "vllm.log"),
        },
    }


def run_profile(args: argparse.Namespace) -> int:
    context_window = args.context
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    result_dir = args.result_root / f"context-{context_window}-{stamp}"
    result_dir.mkdir(parents=True, exist_ok=True)
    home = args.codex_home_root / f"context-{context_window}-{stamp}"
    workspace = args.workspace_root / f"context-{context_window}-{stamp}"
    workspace.mkdir(parents=True, exist_ok=True)
    base_url = f"http://127.0.0.1:{DEFAULT_PORT}"
    write_config(home, base_url, context_window)

    vllm_process: subprocess.Popen[Any] | None = None
    sampler: MetricsSampler | None = None
    app: AppServerClient | None = None
    health_seconds: float | None = None
    app_info: dict[str, Any] | None = None
    workloads: list[dict[str, Any]] = []
    selected_workloads = (
        [WORKLOADS_BY_NAME[name] for name in args.workloads]
        if args.workloads
        else list(WORKLOADS)
    )
    failure: str | None = None
    try:
        ensure_endpoint_not_serving(base_url)
        vllm_process = start_vllm(
            context_window,
            base_url,
            result_dir / "vllm.log",
            args.vllm_root,
            args.model_root,
            args.gpu_memory_utilization,
        )
        sampler = MetricsSampler(vllm_process.pid)
        sampler.start()
        health_seconds = wait_for_health(
            base_url,
            vllm_process,
            args.health_timeout,
        )
        adapter_root = result_dir / "adapter"
        adapter = build_adapter(adapter_root)
        app = AppServerClient(
            args.codex_bin,
            home,
            workspace,
            base_url,
            adapter,
            result_dir / "app-server-events.jsonl",
            result_dir / "app-server-stderr.log",
            args.turn_timeout,
        )
        app_info = app.start()
        sampler.set_codex_pid(app.process.pid if app.process else None)
        for workload in selected_workloads:
            workloads.append(app.run_workload(workload))
            print(
                json_line(
                    {
                        "profile": context_window,
                        "workload": workload.name,
                        "status": workloads[-1].get("status"),
                        "task_success": workloads[-1].get("task_success"),
                        "elapsed_seconds": workloads[-1].get("elapsed_seconds"),
                        "tool_calls": len(workloads[-1].get("tool_calls", [])),
                        "compaction": workloads[-1].get("compaction_occurred"),
                    }
                ),
                flush=True,
            )
    except Exception as exc:
        failure = repr(exc)
    finally:
        if app is not None:
            app.close()
        vllm_returncode = stop_process(vllm_process)
        if sampler is not None:
            sampler.stop()
        report = summarize_profile(
            context_window,
            result_dir,
            health_seconds,
            vllm_returncode,
            app_info,
            workloads,
            sampler,
            args.gpu_memory_utilization,
        )
        report["failure"] = failure
        report["requested_workloads"] = [workload.name for workload in selected_workloads]
        report["completed_at"] = utc_now()
        (result_dir / "result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        print(
            json_line(
                {
                    "profile": context_window,
                    "result_dir": str(result_dir),
                    "failure": failure,
                    "vllm_returncode": vllm_returncode,
                    "workloads_completed": len(workloads),
                }
            ),
            flush=True,
        )
    return 1 if failure else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one isolated UAEA H3-A context characterization profile."
    )
    parser.add_argument("--context", type=int, choices=(8192, 16384, 32768), required=True)
    parser.add_argument(
        "--workload",
        dest="workloads",
        action="append",
        choices=tuple(WORKLOADS_BY_NAME),
        help="Run only this fixed workload; repeat for multiple workloads.",
    )
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--codex-bin", type=Path, default=DEFAULT_CODEX_BIN)
    parser.add_argument("--codex-home-root", type=Path, default=DEFAULT_CODEX_HOME_ROOT)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE_ROOT)
    parser.add_argument("--vllm-root", type=Path, default=DEFAULT_VLLM_ROOT)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument(
        "--gpu-memory-utilization",
        type=float,
        default=DEFAULT_GPU_MEMORY_UTILIZATION,
    )
    parser.add_argument("--health-timeout", type=int, default=DEFAULT_HEALTH_TIMEOUT)
    parser.add_argument("--turn-timeout", type=int, default=DEFAULT_TURN_TIMEOUT)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run_profile(parse_args()))
