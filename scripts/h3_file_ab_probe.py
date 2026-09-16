from __future__ import annotations

import base64
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
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from runtime.ledger import LedgerStub  # noqa: E402
from runtime.sandbox import Sandbox  # noqa: E402
from runtime.semantic_observation import ExecutionObservation  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402


DEFAULT_RESULT_ROOT = Path("/mnt/d/UAEA-runtime/h3-results")
DEFAULT_CODEX_BIN = Path(
    "/mnt/d/UAEA-runtime/codex/source-rust-v0.154.0-wsl-x86_64/codex"
)
DEFAULT_CODEX_HOME_ROOT = Path("/mnt/d/UAEA-runtime/codex-home-h3-file-ab")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_line(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


class AppServerProbe:
    def __init__(self, codex: Path, codex_home: Path, cwd: Path) -> None:
        self.codex = codex
        self.codex_home = codex_home
        self.cwd = cwd
        self.process: subprocess.Popen[str] | None = None
        self.queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self.events: list[dict[str, Any]] = []
        self.request_id = 1

    def start(self) -> None:
        self.codex_home.mkdir(parents=True, exist_ok=True)
        (self.codex_home / "config.toml").write_text(
            "\n".join(
                [
                    'model = "qwen25-14b-awq"',
                    'model_provider = "uaea_local_vllm"',
                    "disable_response_storage = true",
                    "project_doc_max_bytes = 0",
                    "",
                    "[features]",
                    "skill_search = false",
                    "plugins = false",
                    "",
                    "[model_providers.uaea_local_vllm]",
                    'name = "UAEA local vLLM"',
                    'base_url = "http://127.0.0.1:8002/v1"',
                    'wire_api = "responses"',
                    "requires_openai_auth = false",
                    "",
                ]
            ),
            encoding="utf-8",
        )
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
            [str(self.codex), "app-server", "--stdio"],
            cwd=str(self.cwd),
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
                args=(stream, label, self.queue),
                daemon=True,
            ).start()
        initialized = self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "uaea-h3-file-ab-probe",
                    "title": "UAEA H3 File A/B Probe",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
            timeout=60,
        )
        if initialized.get("error") is not None:
            raise RuntimeError(f"initialize failed: {initialized}")

    def request(self, method: str, params: dict[str, Any], *, timeout: int = 30) -> dict[str, Any]:
        request_id = self.request_id
        self.request_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        response = self._wait_for(lambda message: message.get("id") == request_id, timeout)
        if response is None:
            raise RuntimeError(f"{method} timeout")
        return response

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

    def _send(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("app-server stdin unavailable")
        self.process.stdin.write(json_line(message) + "\n")
        self.process.stdin.flush()

    def _wait_for(
        self,
        predicate: Callable[[dict[str, Any]], bool],
        timeout: int,
    ) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                label, line = self.queue.get(timeout=0.25)
            except queue.Empty:
                if self.process is not None and self.process.poll() is not None:
                    return None
                continue
            if line is None:
                continue
            event = {"observed_at": utc_now(), "label": label, "line": line}
            if label == "stdout":
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event["message"] = message
                self.events.append(event)
                if predicate(message):
                    return message
            else:
                self.events.append(event)
        return None

    @staticmethod
    def _read_stream(stream: Any, label: str, output: queue.Queue) -> None:
        for line in iter(stream.readline, ""):
            output.put((label, line.rstrip("\r\n")))
        output.put((label, None))


def run_probe() -> int:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    result_dir = DEFAULT_RESULT_ROOT / f"file-ab-{stamp}"
    result_dir.mkdir(parents=True, exist_ok=True)
    codex_home = DEFAULT_CODEX_HOME_ROOT / f"file-ab-{stamp}"
    readme = PROJECT_ROOT / "README.md"

    app = AppServerProbe(DEFAULT_CODEX_BIN, codex_home, PROJECT_ROOT)
    harness_native: dict[str, Any] = {}
    try:
        app.start()
        started = time.monotonic()
        read_response = app.request("fs/readFile", {"path": str(readme)})
        read_elapsed = round(time.monotonic() - started, 4)
        read_result = read_response.get("result") or {}
        text = base64.b64decode(read_result.get("dataBase64", "")).decode(
            "utf-8",
            errors="replace",
        )

        started = time.monotonic()
        list_response = app.request("fs/readDirectory", {"path": str(PROJECT_ROOT)})
        list_elapsed = round(time.monotonic() - started, 4)
        entries = (list_response.get("result") or {}).get("entries") or []

        harness_native = {
            "status": "PASS",
            "read_file": {
                "ok": read_response.get("error") is None and "# UAEA" in text,
                "elapsed_seconds": read_elapsed,
                "response_keys": sorted((read_response.get("result") or {}).keys()),
                "decoded_prefix": text[:120],
                "size_chars": len(text),
            },
            "read_directory": {
                "ok": list_response.get("error") is None
                and any(entry.get("fileName") == "README.md" for entry in entries),
                "elapsed_seconds": list_elapsed,
                "entry_count": len(entries),
                "sample": entries[:10],
            },
            "event_count": len(app.events),
            "methods": [
                event.get("message", {}).get("method")
                for event in app.events
                if isinstance(event.get("message"), dict)
            ],
        }
    except Exception as exc:
        harness_native = {"status": "FAIL", "error": repr(exc)}
    finally:
        app.close()

    trace_root = result_dir / "uaea-traces"
    registry = ToolRegistry(Sandbox(PROJECT_ROOT, PROJECT_ROOT), LedgerStub(trace_root))
    started = time.monotonic()
    section_result = registry.execute_capability(
        "document.read_section",
        {"path": "README.md", "section_index": 1},
        "H3 File A/B UAEA baseline read_section",
    )
    section_elapsed = round(time.monotonic() - started, 4)
    section_observation = ExecutionObservation.from_tool_result("read_section", section_result)

    started = time.monotonic()
    list_result = registry.execute_capability(
        "fs.list",
        {"path": "."},
        "H3 File A/B UAEA baseline fs.list",
    )
    list_elapsed = round(time.monotonic() - started, 4)
    list_observation = ExecutionObservation.from_tool_result("list_files", list_result)

    uaea_baseline = {
        "status": "PASS" if section_result.ok and list_result.ok else "FAIL",
        "read_section": {
            "ok": section_result.ok,
            "elapsed_seconds": section_elapsed,
            "message": section_result.message,
            "observation": section_observation.to_event_metadata(),
            "content_prefix": str(section_result.data.get("content", ""))[:120],
        },
        "list_files": {
            "ok": list_result.ok,
            "elapsed_seconds": list_elapsed,
            "message": list_result.message,
            "observation": list_observation.to_event_metadata(),
            "entry_count": len(list_result.data.get("entries", [])),
            "sample": list_result.data.get("entries", [])[:10],
        },
        "trace_path": str(trace_root),
    }

    report = {
        "phase": "H3 File A/B",
        "started_at": utc_now(),
        "scope": "Harness-native app-server fs API vs UAEA ToolRegistry baseline",
        "note": (
            "Harness-native probe validates app-server file lifecycle directly. "
            "It does not prove model-mediated native file tool selection."
        ),
        "harness_native": harness_native,
        "uaea_baseline": uaea_baseline,
        "artifacts": {
            "result_dir": str(result_dir),
            "codex_home": str(codex_home),
            "app_server_events": str(result_dir / "app-server-events.jsonl"),
        },
    }
    (result_dir / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    (result_dir / "app-server-events.jsonl").write_text(
        "\n".join(json_line(event) for event in app.events) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if harness_native.get("status") == "PASS" and uaea_baseline["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(run_probe())
