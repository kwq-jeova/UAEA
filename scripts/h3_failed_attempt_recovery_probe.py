from __future__ import annotations

import argparse
import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import patch

from h3_harness_interactive_repl import InteractiveAppServer, build_interactive_adapter
from h3_context_characterization import (
    DEFAULT_CODEX_BIN, DEFAULT_CODEX_HOME_ROOT, DEFAULT_MODEL_ROOT,
    DEFAULT_RESULT_ROOT, DEFAULT_VLLM_ROOT, DEFAULT_WORKSPACE_ROOT,
    ensure_endpoint_not_serving, start_vllm, stop_process, wait_for_health, write_config,
)
from h3_harness_interactive_repl import utc_stamp
from harness.trajectory_reader import read_trajectory_jsonl, validate_trajectory_records
from phase2.web_environment import load_web_environment


MALFORMED = '{"query":"AI agent","max_results": BROKEN_ATTEMPT}'
BAD_CALL = "call_recovery_malformed"
FILE_CALL = "call_recovery_file"


def sse(item: dict[str, Any], response_id: str) -> bytes:
    events = [
        {"type": "response.created", "response": {"id": response_id}},
        {"type": "response.output_item.done", "item": item},
        {"type": "response.completed", "response": {
            "id": response_id, "usage": {
                "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            },
        }},
    ]
    return "".join("data: " + json.dumps(e, ensure_ascii=False) + "\n\n" for e in events).encode()


def last_user_text(items: list[dict[str, Any]]) -> str:
    for item in reversed(items):
        if item.get("role") == "user":
            content = item.get("content", "")
            return content if isinstance(content, str) else "\n".join(
                str(part.get("text") or "") for part in content if isinstance(part, dict)
            )
    return ""


def run(args: argparse.Namespace) -> int:
    load_web_environment(report=False)
    stamp = utc_stamp()
    root = args.result_root / f"failed-attempt-recovery-{stamp}"
    home = DEFAULT_CODEX_HOME_ROOT / root.name
    workspace = DEFAULT_WORKSPACE_ROOT / root.name
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    adapter = build_interactive_adapter(root / "adapter")
    file_tool = next(b.tool_name for b in adapter.bindings if b.capability == "document.read_section")
    requests: list[dict[str, Any]] = []
    bad_http_count = 0
    file_execution_count = 0
    web_http_count = 0
    def reject_web_http(*args: Any, **kwargs: Any) -> Any:
        nonlocal web_http_count
        web_http_count += 1
        raise AssertionError("Recovery probe must not perform a Web HTTP request")

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            nonlocal bad_http_count
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            for item in payload.get("input", []):
                if item.get("type") == "function_call":
                    try:
                        json.loads(item["arguments"])
                    except ValueError:
                        bad_http_count += 1
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"error":{"message":"malformed history","type":"BadRequestError"}}')
                        return
            requests.append(payload)
            text = last_user_text(payload.get("input", []))
            if "RECOVERY_BAD" in text and not any(
                "uaea.terminal_attempt_fact" in json.dumps(i) for i in payload.get("input", [])
            ):
                item = {"type": "function_call", "id": "recovery-malformed-item",
                        "call_id": BAD_CALL, "name": "web_search", "arguments": MALFORMED}
            elif "RECOVERY_FILE" in text and not any(
                i.get("type") == "function_call_output" and i.get("call_id") == FILE_CALL
                for i in payload.get("input", [])
            ):
                item = {"type": "function_call", "id": "recovery-file-item",
                        "call_id": FILE_CALL, "name": file_tool,
                        "arguments": json.dumps({"path": "README.md", "section_index": 1})}
            elif args.live_vllm and ("RECOVERY_CHAT" in text or "RECOVERY_RELOAD" in text):
                # Controlled bad output; real Qwen handles subsequent chat/reload turns.
                connection = http.client.HTTPConnection("127.0.0.1", 8002, timeout=120)
                try:
                    payload["max_output_tokens"] = 128
                    connection.request("POST", "/v1/responses", json.dumps(payload), {"Content-Type": "application/json"})
                    response = connection.getresponse()
                    self.send_response(response.status)
                    self.send_header("Content-Type", response.getheader("Content-Type", "text/event-stream"))
                    self.end_headers()
                    while chunk := response.read1(65536):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                finally:
                    connection.close()
                return
            else:
                item = {"type": "message", "id": f"recovery-message-{len(requests)}",
                        "role": "assistant", "content": [{"type": "output_text", "text": "RECOVERY_OK"}]}
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(sse(item, f"recovery-response-{len(requests)}"))

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    upstream_url = f"http://127.0.0.1:{upstream.server_port}"
    write_config(home, upstream_url, 32768)
    vllm = None
    app = None
    web_guard = patch("phase2.web_adapter.WebAdapter._http_get", side_effect=reject_web_http)
    web_guard.start()
    try:
        if args.live_vllm:
            ensure_endpoint_not_serving("http://127.0.0.1:8002")
            vllm = start_vllm(32768, "http://127.0.0.1:8002", root / "vllm.log",
                              DEFAULT_VLLM_ROOT, DEFAULT_MODEL_ROOT, 0.75)
            wait_for_health("http://127.0.0.1:8002", vllm, 600)
        app = InteractiveAppServer(
            codex=DEFAULT_CODEX_BIN, codex_home=home, workspace=workspace,
            base_url=upstream_url, adapter=adapter,
            events_path=root / "app-server-events.jsonl", stderr_path=root / "app-server-stderr.log",
            turn_timeout=180,
        )
        app.start()
        thread_id = app.thread_id
        app.run_turn("RECOVERY_BAD: exercise a rejected tool attempt.")
        app.run_turn("RECOVERY_CHAT: reply briefly that conversation can continue; do not use tools.")
        app.run_turn("RECOVERY_FILE: read README section 1 and give a brief answer.")
        app.close()
        app = InteractiveAppServer(
            codex=DEFAULT_CODEX_BIN, codex_home=home, workspace=workspace,
            base_url=upstream_url, adapter=build_interactive_adapter(root / "adapter-resume"),
            events_path=root / "resume-events.jsonl", stderr_path=root / "resume-stderr.log",
            turn_timeout=180,
        )
        app.start(resume_thread_id=thread_id)
        app.run_turn("RECOVERY_RELOAD: reply briefly after runtime restart; do not use tools.")
        app.close()
        rows = [json.loads(line) for p in (root / "app-server-events.jsonl", root / "resume-events.jsonl")
                for line in p.read_text().splitlines()]
        completions = [r["message"]["params"]["turn"] for r in rows
                       if r["message"].get("method") == "turn/completed"]
        tool_calls = [r["message"]["params"] for r in rows
                      if r["message"].get("method") == "item/tool/call"]
        file_execution_count = len([r for r in rows if r["message"].get("method") == "item/completed"
                                    and r["message"]["params"].get("item", {}).get("id") == FILE_CALL
                                    and r["message"]["params"]["item"].get("success") is True])
        trajectory_checks = []
        for p in (root / "normalized-trajectories").glob("*.trajectory.jsonl"):
            parsed = read_trajectory_jsonl(p)
            trajectory_checks.append(validate_trajectory_records(parsed.records).ok)
        rollout_texts = [p.read_text() for p in (home / "sessions").rglob("*.jsonl")]
        report = {
            "schema": "uaea.failed_attempt_recovery_probe.v1",
            "mode": "real_harness_with_qwen_chat" if args.live_vllm else "real_harness_protocol_fixture",
            "thread_id": thread_id, "resume_thread_id": app.thread_id,
            "same_thread": app.thread_id == thread_id,
            "turn_statuses": [t["status"] for t in completions],
            "malformed_call_dispatched_to_uaea": any(c["callId"] == BAD_CALL for c in tool_calls),
            "web_http_calls": web_http_count,
            "valid_file_execution_count": file_execution_count,
            "provider_history_400_count": bad_http_count,
            "raw_malformed_preserved": any(MALFORMED in json.dumps(r, ensure_ascii=False).replace('\\"', '"') for r in rows),
            "persisted_rollout_keeps_malformed": any("BROKEN_ATTEMPT" in t for t in rollout_texts),
            "trajectory_validation": trajectory_checks,
            "provider_request_count": len(requests),
        }
        passed = (
            report["same_thread"] and len(completions) == 4
            and all(t["status"] == "completed" for t in completions)
            and not report["malformed_call_dispatched_to_uaea"] and web_http_count == 0
            and file_execution_count == 1 and bad_http_count == 0
            and report["raw_malformed_preserved"] and report["persisted_rollout_keeps_malformed"]
            and trajectory_checks and all(trajectory_checks)
        )
        report["status"] = "PASS" if passed else "FAIL"
        (root / "recovery-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"artifact": str(root), **report}, ensure_ascii=True), flush=True)
        return 0 if passed else 1
    finally:
        if app is not None:
            app.close()
        upstream.shutdown()
        upstream.server_close()
        thread.join(timeout=5)
        stop_process(vllm)
        web_guard.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Failed-attempt isolation on pinned local Harness.")
    parser.add_argument("--live-vllm", action="store_true")
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    raise SystemExit(run(parser.parse_args()))
