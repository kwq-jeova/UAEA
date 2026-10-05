from __future__ import annotations

import http.client
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from h3_failed_attempt_recovery_probe import sse
from h3_harness_interactive_repl import InteractiveAppServer, build_interactive_adapter, utc_stamp
from h3_context_characterization import (
    DEFAULT_CODEX_BIN, DEFAULT_CODEX_HOME_ROOT, DEFAULT_MODEL_ROOT, DEFAULT_RESULT_ROOT,
    DEFAULT_VLLM_ROOT, DEFAULT_WORKSPACE_ROOT, ensure_endpoint_not_serving,
    start_vllm, stop_process, wait_for_health, write_config,
)
from phase2.web_environment import load_web_environment


REJECTED_CALL = "call_probe_unauthorized_fallback"


def main() -> int:
    load_web_environment(require_key=True, require_proxy=True)
    root = DEFAULT_RESULT_ROOT / f"web-rejection-recovery-{utc_stamp()}"
    home, workspace = DEFAULT_CODEX_HOME_ROOT / root.name, DEFAULT_WORKSPACE_ROOT / root.name
    root.mkdir(parents=True, exist_ok=False)
    workspace.mkdir(parents=True, exist_ok=True)
    adapter = build_interactive_adapter(root / "adapter")
    outcomes = []
    provider_requests = 0
    provider_400 = 0

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

        def do_POST(self) -> None:
            nonlocal provider_requests, provider_400
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            provider_requests += 1
            if provider_requests == 1:
                body = sse({"type": "function_call", "name": "web_search", "call_id": REJECTED_CALL,
                    "arguments": json.dumps({"query": "AI agent research last six months",
                                             "provider": "google", "allow_fallback": True})}, "probe-rejection")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(body)
                return
            # Only the rejected proposal is injected; Qwen owns every subsequent action.
            payload["max_output_tokens"] = 384
            connection = http.client.HTTPConnection("127.0.0.1", 8002, timeout=180)
            try:
                connection.request("POST", "/v1/responses", json.dumps(payload), {"Content-Type": "application/json"})
                response = connection.getresponse()
                provider_400 += int(response.status == 400)
                self.send_response(response.status)
                self.send_header("Content-Type", response.getheader("Content-Type", "text/event-stream"))
                self.end_headers()
                while chunk := response.read1(65536):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            finally:
                connection.close()

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    worker = threading.Thread(target=upstream.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{upstream.server_port}"
    write_config(home, base_url, 32768)
    execute = adapter.registry.execute_capability

    def observe_execution(capability, arguments, objective):
        result = execute(capability, arguments, objective)
        if capability == "web.search":
            outcomes.append({"proposal": dict(arguments), **{key: result.data.get(key) for key in (
                "execution_status", "execution_succeeded", "http_attempted", "requested_provider",
                "actual_provider", "acquisition_backend", "fallback_occurred", "reason",
            )}})
        return result

    app = vllm = None
    try:
        ensure_endpoint_not_serving("http://127.0.0.1:8002")
        vllm = start_vllm(32768, "http://127.0.0.1:8002", root / "vllm.log",
                          DEFAULT_VLLM_ROOT, DEFAULT_MODEL_ROOT, 0.75)
        wait_for_health("http://127.0.0.1:8002", vllm, 600)
        app = InteractiveAppServer(codex=DEFAULT_CODEX_BIN, codex_home=home, workspace=workspace,
            base_url=base_url, adapter=adapter, events_path=root / "app-server-events.jsonl",
            stderr_path=root / "app-server-stderr.log", turn_timeout=180)
        app.start()
        with patch.object(adapter.registry, "execute_capability", side_effect=observe_execution):
            app.run_turn("请你从google站点搜索 AI agent 最近六个月的研究，用英文检索，返回找到的链接。")
        app.close()
        rows = [json.loads(line)["message"] for line in app.events_path.read_text().splitlines()]
        rejected_outputs = []
        for row in rows:
            item = row.get("params", {}).get("item", {})
            if item.get("type") == "function_call_output" and item.get("call_id") == REJECTED_CALL:
                rejected_outputs.append(json.loads(item["output"]))
        completed = [row["params"]["turn"]["status"] for row in rows if row.get("method") == "turn/completed"]
        legal_http = any(o["proposal"].get("provider") == "google"
                         and o["proposal"].get("allow_fallback") is False and o["http_attempted"] is True
                         for o in outcomes)
        secret = os.environ["SERPAPI_KEY"].encode()
        secret_clean = all(secret not in p.read_bytes() for p in root.rglob("*") if p.is_file())
        rejected = bool(rejected_outputs) and all(
            o["data"].get("http_attempted") is False
            and o["data"]["recovery"]["authorization"]["state"] == "unknown" for o in rejected_outputs)
        report = {"artifact": str(root), "rejected_attempt_preserved": rejected,
            "qwen_owned_recovery": provider_requests > 1, "legal_web_http_execution": legal_http,
            "google_search_succeeded": any(o["actual_provider"] == "google" and o["execution_succeeded"] is True for o in outcomes),
            "execution_outcomes": outcomes, "turn_statuses": completed, "provider_http_400": provider_400,
            "secret_check": "PASS" if secret_clean else "FAIL"}
        passed = rejected and legal_http and completed == ["completed"] and provider_400 == 0 and secret_clean
        report["recovery_status"] = "PASS" if passed else "PARTIAL"
        (root / "recovery-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=True), flush=True)
        return 0 if passed else 1
    finally:
        if app is not None:
            app.close()
        upstream.shutdown()
        upstream.server_close()
        worker.join(timeout=5)
        stop_process(vllm)


if __name__ == "__main__":
    raise SystemExit(main())
