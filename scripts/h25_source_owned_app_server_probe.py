from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


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


DEFAULT_CODEX_BIN = (
    "/mnt/d/UAEA-runtime/codex/"
    "source-rust-v0.154.0-wsl-x86_64/codex"
)
DEFAULT_CODEX_HOME = "/mnt/d/UAEA-runtime/codex-home-h25"
DEFAULT_WORKSPACE = "/mnt/d/UAEA-runtime/codex-workspace-h25"
DEFAULT_BASE_URL = "http://127.0.0.1:8002"


def build_uaea_adapter() -> HarnessDynamicToolAdapter:
    root = Path(tempfile.mkdtemp(prefix="uaea-h25-adapter-"))
    sandbox_root = root / "sandbox"
    sandbox_root.mkdir()
    registry = ToolRegistry(Sandbox(root, sandbox_root), LedgerStub(root / "traces"))

    def echo(arguments, objective):
        return ToolResult(
            True,
            "mock external operation completed",
            {
                "received": dict(arguments),
                "objective": objective,
                "external_ref": "mock://external/h25",
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
            future_phase="harness-test",
        ),
        echo,
    )
    return HarnessDynamicToolAdapter(
        registry,
        [
            DynamicToolBinding.from_registry(
                registry,
                "mock.external_operation",
                description="Run the deterministic external fixture.",
                input_schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
            )
        ],
    )


def read_stream(stream, output_queue, label):
    for line in iter(stream.readline, ""):
        output_queue.put((label, line.rstrip("\r\n")))
    output_queue.put((label, None))


def send(process, message):
    line = json.dumps(message, separators=(",", ":"))
    process.stdin.write(line + "\n")
    process.stdin.flush()
    print("SEND", line, flush=True)


def main() -> int:
    codex = Path(os.environ.get("H25_CODEX_BIN", DEFAULT_CODEX_BIN)).expanduser()
    codex_home = Path(os.environ.get("H25_CODEX_HOME", DEFAULT_CODEX_HOME))
    workspace = Path(os.environ.get("H25_WORKSPACE", DEFAULT_WORKSPACE))
    base_url = os.environ.get("H25_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3].rstrip("/")

    if not codex.is_absolute() or not codex.is_file():
        raise RuntimeError(f"Source-owned Codex binary not found: {codex}")
    if not codex_home.is_dir():
        raise RuntimeError(f"Dedicated CODEX_HOME not found: {codex_home}")
    if not workspace.is_dir():
        raise RuntimeError(f"Dedicated workspace not found: {workspace}")

    version = subprocess.run(
        [str(codex), "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout.strip()
    print("SOURCE_CODEX_BIN", codex, flush=True)
    print("SOURCE_CODEX_VERSION", version, flush=True)
    print("CODEX_HOME", codex_home, flush=True)
    print("WORKSPACE", workspace, flush=True)
    print("MODEL_ENDPOINT", f"{base_url}/v1", flush=True)

    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "CODEX_API_KEY",
        "CHATGPT_API_KEY",
    ):
        env.pop(name, None)

    process = subprocess.Popen(
        [
            str(codex),
            "app-server",
            "--stdio",
            "-c",
            f'model_providers.uaea_local_vllm.base_url="{base_url}/v1"',
        ],
        cwd=str(workspace),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    events = queue.Queue()
    for stream, label in (
        (process.stdout, "stdout"),
        (process.stderr, "stderr"),
    ):
        threading.Thread(
            target=read_stream,
            args=(stream, events, label),
            daemon=True,
        ).start()

    adapter = build_uaea_adapter()
    handled_call_ids: set[str] = set()

    def wait_for(predicate, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                label, line = events.get(timeout=0.25)
            except queue.Empty:
                if process.poll() is not None:
                    return None
                continue
            if line is None:
                continue
            if label == "stderr":
                print("STDERR", line, flush=True)
                continue
            print("RECV", line, flush=True)
            message = json.loads(line)
            if message.get("method") == "item/tool/call":
                params = message["params"]
                call_id = str(params.get("callId") or "")
                if call_id not in handled_call_ids:
                    handled_call_ids.add(call_id)
                    dispatch = adapter.dispatch(
                        params,
                        objective="Harness H2.5 source-owned runtime probe",
                    )
                    print(
                        "UAEA_TRACE",
                        json.dumps(
                            dispatch.to_trace_metadata(),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        flush=True,
                    )
                    send(
                        process,
                        {
                            "jsonrpc": "2.0",
                            "id": message["id"],
                            "result": dispatch.to_app_server_response(),
                        },
                    )
            if predicate(message):
                return message
        return None

    try:
        send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "uaea-h25-source-owned-probe",
                        "title": "UAEA H2.5",
                        "version": "0.1.0",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            },
        )
        if wait_for(lambda message: message.get("id") == 1, 30) is None:
            raise RuntimeError("initialize timeout")

        send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "thread/start",
                "params": {
                    "model": "qwen25-14b-awq",
                    "modelProvider": "uaea_local_vllm",
                    "cwd": str(workspace),
                    "ephemeral": True,
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "personality": "none",
                    "experimentalRawEvents": True,
                    "dynamicTools": adapter.dynamic_tools(),
                },
            },
        )
        thread_message = wait_for(lambda message: message.get("id") == 2, 30)
        if thread_message is None:
            raise RuntimeError("thread/start timeout")
        thread_id = thread_message["result"]["thread"]["id"]
        print("THREAD_ID", thread_id, flush=True)

        send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "turn/start",
                "params": {
                    "threadId": thread_id,
                    "input": [
                        {
                            "type": "text",
                            "text": (
                                "Call the mock_external_operation tool exactly once "
                                "with text hello, then report the returned result in "
                                "one short sentence."
                            ),
                        }
                    ],
                    "effort": "none",
                    "model": "qwen25-14b-awq",
                },
            },
        )
        completed = wait_for(
            lambda message: (
                message.get("method") == "turn/completed"
                and message.get("params", {}).get("threadId") == thread_id
            )
            or (message.get("id") == 3 and message.get("error") is not None),
            180,
        )
        if completed is None:
            raise RuntimeError("turn timeout or app-server exit")
        print(
            "PROBE_COMPLETED",
            json.dumps(completed, separators=(",", ":")),
            flush=True,
        )
        return 0
    finally:
        if process.stdin is not None:
            process.stdin.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        print("EXIT_CODE", process.returncode, flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("PROBE_ERROR", repr(error), flush=True)
        raise SystemExit(1)
