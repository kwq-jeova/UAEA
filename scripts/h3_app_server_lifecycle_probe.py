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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from h3_context_characterization import (  # noqa: E402
    DEFAULT_CODEX_BIN,
    DEFAULT_CODEX_HOME_ROOT,
    DEFAULT_HEALTH_TIMEOUT,
    DEFAULT_MODEL,
    DEFAULT_MODEL_ROOT,
    DEFAULT_PORT,
    DEFAULT_RESULT_ROOT,
    DEFAULT_VLLM_ROOT,
    ensure_endpoint_not_serving,
    start_vllm,
    stop_process,
    wait_for_health,
)
from harness.trajectory_writer import HarnessTrajectoryWriter  # noqa: E402


DEFAULT_CONTEXT_WINDOW = 32768
DEFAULT_GPU_MEMORY_UTILIZATION = 0.75
DEFAULT_TURN_TIMEOUT = 300


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_line(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def write_lifecycle_config(home: Path, base_url: str, context_window: int) -> None:
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


class LifecycleAppServer:
    def __init__(
        self,
        *,
        codex: Path,
        codex_home: Path,
        workspace: Path,
        base_url: str,
        events_path: Path,
        stderr_path: Path,
        trajectory_writer: HarnessTrajectoryWriter | None,
        turn_timeout: int,
    ) -> None:
        self.codex = codex
        self.codex_home = codex_home
        self.workspace = workspace
        self.base_url = base_url.rstrip("/")
        self.events_path = events_path
        self.stderr_path = stderr_path
        self.trajectory_writer = trajectory_writer
        self.turn_timeout = turn_timeout
        self.process: subprocess.Popen[str] | None = None
        self.events: list[dict[str, Any]] = []
        self._queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self._request_id = 1
        self._events_file: Any = None
        self._stderr_file: Any = None

    def start(self) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self._events_file = self.events_path.open("w", encoding="utf-8")
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
        response = self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "uaea-h3-app-server-lifecycle-probe",
                    "title": "UAEA H3 App Server Lifecycle Probe",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
            timeout=60,
        )
        if response.get("error") is not None:
            raise RuntimeError(f"initialize failed: {response}")

    def start_thread(self) -> str:
        response = self.request(
            "thread/start",
            {
                "model": DEFAULT_MODEL,
                "modelProvider": "uaea_local_vllm",
                "cwd": str(self.workspace),
                "ephemeral": True,
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "personality": "none",
                "experimentalRawEvents": True,
            },
            timeout=60,
        )
        if response.get("error") is not None:
            raise RuntimeError(f"thread/start failed: {response}")
        return str(response["result"]["thread"]["id"])

    def run_turn(
        self,
        *,
        thread_id: str,
        prompt: str,
        additional_context: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        start_index = len(self.events)
        request_id = self._next_id()
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "turn/start",
            "params": {
                "threadId": thread_id,
                "input": [{"type": "text", "text": prompt}],
                "effort": "none",
                "model": DEFAULT_MODEL,
            },
        }
        if additional_context:
            payload["params"]["additionalContext"] = additional_context
        self._send(payload)
        completion = self._wait_for(
            lambda message: (
                message.get("method") == "turn/completed"
                and message.get("params", {}).get("threadId") == thread_id
            )
            or (message.get("id") == request_id and message.get("error") is not None),
            timeout or self.turn_timeout,
        )
        events = self.events[start_index:]
        return {
            "completion": completion,
            "events": events,
            "summary": summarize_events(events),
        }

    def request(self, method: str, params: dict[str, Any], *, timeout: int = 30) -> dict[str, Any]:
        request_id = self._next_id()
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        response = self._wait_for(lambda message: message.get("id") == request_id, timeout)
        if response is None:
            raise RuntimeError(f"{method} timeout")
        return response

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
        for handle in (self._events_file, self._stderr_file):
            if handle is not None:
                handle.flush()
                handle.close()
        if self.trajectory_writer is not None:
            self.trajectory_writer.close()

    def _next_id(self) -> int:
        value = self._request_id
        self._request_id += 1
        return value

    def _send(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("app-server stdin unavailable")
        self.process.stdin.write(json_line(message) + "\n")
        self.process.stdin.flush()
        if self.trajectory_writer is not None and message.get("method") == "turn/start":
            self.trajectory_writer.write_raw_event(
                {
                    "observed_at": utc_now(),
                    "observed_monotonic": time.monotonic(),
                    "label": "stdin",
                    "message": message,
                },
                raw_event_reference={"stream": "stdin"},
            )

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
            event: dict[str, Any] = {
                "observed_at": utc_now(),
                "observed_monotonic": time.monotonic(),
                "label": label,
                "line": line,
            }
            if label == "stderr":
                if self._stderr_file is not None:
                    self._stderr_file.write(line + "\n")
                    self._stderr_file.flush()
                self.events.append(event)
                if self.trajectory_writer is not None:
                    self.trajectory_writer.write_raw_event(
                        event,
                        raw_event_reference={"stream": "stderr"},
                    )
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            event["message"] = message
            self.events.append(event)
            if self._events_file is not None:
                self._events_file.write(json_line(event) + "\n")
                self._events_file.flush()
            if self.trajectory_writer is not None:
                self.trajectory_writer.write_raw_event(
                    event,
                    raw_event_reference={"stream": "stdout", "path": str(self.events_path)},
                )
            if predicate(message):
                return message
        return None

    @staticmethod
    def _read_stream(stream: Any, label: str, output: queue.Queue) -> None:
        for line in iter(stream.readline, ""):
            output.put((label, line.rstrip("\r\n")))
        output.put((label, None))


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    methods: list[str] = []
    item_types: list[str] = []
    agent_texts: list[str] = []
    user_texts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    command_items: list[dict[str, Any]] = []
    token_updates: list[dict[str, Any]] = []
    compaction_items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    ids: dict[str, set[str]] = {"thread": set(), "turn": set(), "item": set(), "call": set()}

    for event in events:
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        method = str(message.get("method") or "")
        if method:
            methods.append(method)
        params = message.get("params") or {}
        if isinstance(params, dict):
            if params.get("threadId"):
                ids["thread"].add(str(params["threadId"]))
            if params.get("turnId"):
                ids["turn"].add(str(params["turnId"]))
            if isinstance(params.get("turn"), dict) and params["turn"].get("id"):
                ids["turn"].add(str(params["turn"]["id"]))
            if params.get("callId"):
                ids["call"].add(str(params["callId"]))
            if method == "thread/tokenUsage/updated":
                token_updates.append(params)
            if method == "item/tool/call":
                tool_calls.append(params)
            item = params.get("item")
            if isinstance(item, dict):
                item_type = str(item.get("type") or "")
                if item_type:
                    item_types.append(item_type)
                if item.get("id"):
                    ids["item"].add(str(item["id"]))
                if item_type == "agentMessage" and item.get("text"):
                    agent_texts.append(str(item["text"]))
                if item_type == "userMessage":
                    for content in item.get("content") or []:
                        if isinstance(content, dict) and content.get("text"):
                            user_texts.append(str(content["text"]))
                if item_type == "dynamicToolCall":
                    ids["call"].add(str(item.get("id") or ""))
                if item_type == "commandExecution":
                    command_items.append(item)
                if item_type == "contextCompaction":
                    compaction_items.append(item)
            turn = params.get("turn")
            if isinstance(turn, dict) and turn.get("error"):
                errors.append(turn["error"])
        if message.get("error"):
            errors.append(message["error"])

    return {
        "methods": methods,
        "item_types": item_types,
        "agent_texts": agent_texts,
        "user_texts": user_texts,
        "tool_calls": tool_calls,
        "command_items": command_items,
        "token_updates": token_updates,
        "compaction_items": compaction_items,
        "errors": errors,
        "ids": {name: sorted(value) for name, value in ids.items()},
        "event_count": len(events),
    }


def run_probe(args: argparse.Namespace) -> int:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    result_dir = args.result_root / f"lifecycle-{args.context}-{stamp}"
    result_dir.mkdir(parents=True, exist_ok=True)
    codex_home = args.codex_home_root / f"lifecycle-{args.context}-{stamp}"
    workspace = PROJECT_ROOT
    base_url = f"http://127.0.0.1:{DEFAULT_PORT}"
    write_lifecycle_config(codex_home, base_url, args.context)

    vllm_process: subprocess.Popen[Any] | None = None
    app: LifecycleAppServer | None = None
    trajectory_writer: HarnessTrajectoryWriter | None = None
    failure = ""
    report: dict[str, Any] = {
        "phase": "H3 App Server Lifecycle Audit",
        "started_at": utc_now(),
        "configured": {
            "context": args.context,
            "gpu_memory_utilization": args.gpu_memory_utilization,
            "endpoint": f"{base_url}/v1",
        },
    }
    try:
        ensure_endpoint_not_serving(base_url)
        vllm_process = start_vllm(
            args.context,
            base_url,
            result_dir / "vllm.log",
            args.vllm_root,
            args.model_root,
            args.gpu_memory_utilization,
        )
        health_seconds = wait_for_health(base_url, vllm_process, args.health_timeout)
        trajectory_writer = HarnessTrajectoryWriter(
            result_dir / "normalized-trajectories",
            run_id=f"lifecycle-{args.context}-{stamp}",
            split_by_thread=True,
        )
        app = LifecycleAppServer(
            codex=args.codex_bin,
            codex_home=codex_home,
            workspace=workspace,
            base_url=base_url,
            events_path=result_dir / "app-server-events.jsonl",
            stderr_path=result_dir / "app-server-stderr.log",
            trajectory_writer=trajectory_writer,
            turn_timeout=args.turn_timeout,
        )
        app.start()
        thread_id = app.start_thread()

        injection_marker = "UAEA_PRE_CONTEXT_MARKER_20260915"
        injected_goal = (
            "Goal state: prove pre-context injection is visible before model reasoning. "
            f"Marker: {injection_marker}."
        )
        pre_context_turn = app.run_turn(
            thread_id=thread_id,
            prompt=(
                "Reply with exactly the marker from the application context. "
                "Do not invent any other marker."
            ),
            additional_context={
                "uaea.lifecycle.goal_state": {
                    "kind": "application",
                    "value": injected_goal,
                },
                "uaea.lifecycle.meta_policy": {
                    "kind": "application",
                    "value": "Meta-policy: answer concisely using supplied cognitive context.",
                },
            },
        )
        pre_context_text = "\n".join(pre_context_turn["summary"]["agent_texts"])

        file_turn = app.run_turn(
            thread_id=thread_id,
            prompt=(
                "Using your native Codex workspace file capability, read README.md "
                "from the current workspace and answer with the project title and "
                "the first sentence. Do not call any dynamic tool."
            ),
        )

        report.update(
            {
                "vllm_health_seconds": health_seconds,
                "thread_id": thread_id,
                "pre_context_injection": {
                    "status": "PASS" if injection_marker in pre_context_text else "FAIL",
                    "marker": injection_marker,
                    "agent_text": pre_context_text,
                    "summary": pre_context_turn["summary"],
                },
                "model_mediated_native_file": {
                    "status": classify_native_file_turn(file_turn["summary"]),
                    "summary": file_turn["summary"],
                },
                "all_event_summary": summarize_events(app.events),
                "artifacts": {
                    "result_dir": str(result_dir),
                    "codex_home": str(codex_home),
                    "app_server_events": str(result_dir / "app-server-events.jsonl"),
                    "app_server_stderr": str(result_dir / "app-server-stderr.log"),
                    "normalized_trajectories": str(result_dir / "normalized-trajectories"),
                    "vllm_log": str(result_dir / "vllm.log"),
                },
                "trajectory_writer": (
                    trajectory_writer.stats.to_dict() if trajectory_writer is not None else {}
                ),
            }
        )
    except Exception as exc:
        failure = repr(exc)
        report["failure"] = failure
    finally:
        if app is not None:
            app.close()
        elif trajectory_writer is not None:
            trajectory_writer.close()
        report["vllm_returncode"] = stop_process(vllm_process)
        report["completed_at"] = utc_now()
        (result_dir / "result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 1 if failure else 0


def classify_native_file_turn(summary: dict[str, Any]) -> str:
    text = "\n".join(summary.get("agent_texts", []))
    item_types = set(summary.get("item_types", []))
    methods = set(summary.get("methods", []))
    command_items = summary.get("command_items", [])
    if command_items and ("# UAEA" in text or "Unified Autonomous Evolution Architecture" in text):
        return "PASS_VIA_HARNESS_COMMAND"
    if "commandExecution" in item_types:
        return "PARTIAL_COMMAND_USED"
    if any("Command" in method or "command" in method for method in methods):
        return "PARTIAL_COMMAND_EVENT"
    if "# UAEA" in text or "Unified Autonomous Evolution Architecture" in text:
        return "PARTIAL_CONTEXT_OR_NATIVE_FILE_UNATTRIBUTED"
    return "NOT_CONFIRMED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe app-server lifecycle surfaces for UAEA cognition audit."
    )
    parser.add_argument("--context", type=int, default=DEFAULT_CONTEXT_WINDOW, choices=(32768,))
    parser.add_argument("--gpu-memory-utilization", type=float, default=DEFAULT_GPU_MEMORY_UTILIZATION)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--codex-bin", type=Path, default=DEFAULT_CODEX_BIN)
    parser.add_argument("--codex-home-root", type=Path, default=DEFAULT_CODEX_HOME_ROOT)
    parser.add_argument("--vllm-root", type=Path, default=DEFAULT_VLLM_ROOT)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--health-timeout", type=int, default=DEFAULT_HEALTH_TIMEOUT)
    parser.add_argument("--turn-timeout", type=int, default=DEFAULT_TURN_TIMEOUT)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run_probe(parse_args()))
