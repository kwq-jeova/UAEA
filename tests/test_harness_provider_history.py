from __future__ import annotations

import copy
import http.client
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

from harness.provider_history import project_provider_history
from harness.recovery_observation import recovery_observation
from harness.responses_bridge import ProviderHistoryBridge
from harness.trajectory_reader import read_trajectory_jsonl, validate_trajectory_records
from harness.trajectory_writer import HarnessTrajectoryWriter


def call(arguments='{"query":"research"}', call_id="call-1"):
    return {"type": "function_call", "id": "item-1", "call_id": call_id,
            "name": "web_search", "arguments": arguments}


def output(payload, call_id="call-1"):
    return {"type": "function_call_output", "id": "result-1", "call_id": call_id,
            "output": json.dumps(payload) if isinstance(payload, dict) else payload}


class ProviderHistoryProjectionTests(unittest.TestCase):
    def test_rejection_preserves_constraints_authorization_and_recovery(self):
        raw = {"ok": False, "status": "validation_failed", "data": {
            "capability": "web.search", "execution_status": "validation_failed",
            "reason": "semantic_constraint_conflict", "error_kind": "semantic_validation",
            "requested_provider": "google", "actual_provider": None,
            "active_constraints": ["web.provider=google", "source.type=academic"],
            "effective_state_id": "state-1", "retryable": True,
            "retry_instruction": "Satisfy the surviving constraints without granting yourself permission.",
            "authorization": {"state": "unknown", "model_proposal": True, "source_items": []},
        }}
        projection = self.assert_isolated(raw, "REJECTED")
        fact = json.loads(projection.request["input"][1]["content"][0]["text"].split("\n", 1)[1])
        observation = fact["observation"]
        self.assertEqual(observation["active_constraints"], raw["data"]["active_constraints"])
        self.assertEqual(observation["retry_instruction"], raw["data"]["retry_instruction"])
        recovery = observation["recovery"]
        self.assertEqual(recovery["authorization"]["state"], "unknown")
        self.assertTrue(recovery["retryable"])
        self.assertEqual(recovery["effective_state_id"], "state-1")
        retry = recovery["legal_next_steps"][0]
        self.assertEqual(retry["argument_updates"], {"provider": "google", "allow_fallback": False})
        self.assertTrue(recovery["requires_current_policy_validation"])
        self.assertFalse(recovery["interaction_failure_grants_authorization"])

    def test_default_mode_interaction_failure_requires_waiting_not_default_permission(self):
        item = call('{"questions":[]}', "question")
        item["name"] = "request_user_input"
        raw = {"input": [item, output("request_user_input is unavailable in Default mode", "question")]}
        projection = project_provider_history(raw)
        self.assertTrue(all(row["type"] == "message" for row in projection.request["input"]))
        fact = json.loads(projection.request["input"][1]["content"][0]["text"].split("\n", 1)[1])
        recovery = fact["observation"]["recovery"]
        self.assertEqual(recovery["reason"], "interaction_unavailable")
        self.assertEqual(recovery["authorization"]["state"], "unknown")
        self.assertFalse(recovery["retryable"])
        self.assertEqual(recovery["legal_next_steps"], [
            {"action": "ask_user_in_conversation", "wait_for_user_reply": True},
        ])

    def test_missing_context_is_unknown_not_empty_policy_or_permission(self):
        recovery = recovery_observation({"execution_status": "validation_failed", "retryable": True,
                                         "capability": "web.search", "requested_provider": "google"})
        self.assertFalse(recovery["constraints_known"])
        self.assertEqual(recovery["authorization"]["state"], "unknown")
        self.assertFalse(recovery["legal_next_steps"][0]["argument_updates"]["allow_fallback"])

    def test_denied_permission_never_offers_fallback_true(self):
        recovery = recovery_observation({"execution_status": "validation_failed", "retryable": True,
            "capability": "web.search", "active_constraints": ["web.provider=google", "web.fallback=forbidden"],
            "authorization": {"state": "denied", "model_proposal": True},
        })
        self.assertEqual(len(recovery["legal_next_steps"]), 1)
        self.assertFalse(recovery["legal_next_steps"][0]["argument_updates"]["allow_fallback"])
        self.assertEqual(recovery["active_constraints"], ["web.provider=google", "web.fallback=forbidden"])

    def test_granted_permission_keeps_source_turn_and_is_not_future_authority(self):
        recovery = recovery_observation({"execution_status": "validation_failed", "retryable": True,
            "capability": "web.search", "active_constraints": ["web.provider=google"],
            "authorization": {"state": "granted", "source_items": [{"object_id": "policy-1",
                "metadata": {"provenance": {"turn_id": "user-turn"}, "unused": "not projected"}}]},
        })
        self.assertEqual(recovery["authorization"]["source_items"], [
            {"item_id": "policy-1", "source_turn_id": "user-turn"},
        ])
        self.assertTrue(recovery["legal_next_steps"][1]["argument_updates"]["allow_fallback"])
        self.assertEqual(recovery["policy_time"], "at_attempt")
        self.assertTrue(recovery["requires_current_policy_validation"])

    def test_non_retryable_failure_does_not_offer_automatic_retry(self):
        recovery = recovery_observation({"execution_status": "validation_failed", "retryable": False,
                                         "capability": "web.search"})
        self.assertFalse(recovery["retryable"])
        self.assertEqual(recovery["legal_next_steps"], [])

    def test_conflicting_constraints_are_not_silently_relaxed(self):
        recovery = recovery_observation({"execution_status": "validation_failed", "retryable": True,
            "capability": "web.search", "active_constraints": ["web.provider=google", "web.exclude_provider=google"],
        })
        self.assertEqual(recovery["legal_next_steps"], [
            {"action": "ask_user_to_resolve_constraints", "wait_for_user_reply": True},
        ])

    def assert_isolated(self, payload, state):
        original = {"model": "qwen25-14b-awq", "input": [call(), output(payload)], "tools": [{"name": "web_search"}]}
        frozen = copy.deepcopy(original)
        projection = project_provider_history(original)
        self.assertEqual(original, frozen)
        self.assertEqual(len(projection.request["input"]), 2)
        self.assertTrue(all(item["type"] == "message" for item in projection.request["input"]))
        self.assertTrue(all(item["role"] == "assistant" for item in projection.request["input"]))
        self.assertEqual({d["state"] for d in projection.decisions}, {state})
        self.assertTrue(all(d["terminal"] and not d["replayable"] for d in projection.decisions))
        self.assertEqual(projection.request["tools"], frozen["tools"])
        return projection

    def test_malformed_arguments_are_terminal_rejected_without_output(self):
        malformed = '{"query":"AI agent","max_results": prose instead of a number'
        request = {"input": [call(malformed)]}
        projection = project_provider_history(request)
        self.assertEqual(projection.decisions[0]["state"], "REJECTED")
        self.assertEqual(projection.decisions[0]["reason"], "malformed_arguments")
        self.assertNotIn("prose instead", json.dumps(projection.request))
        self.assertEqual(request["input"][0]["arguments"], malformed)

    def test_invalid_argument_types_are_rejected(self):
        for arguments in (None, "null", "[]", '"text"', "NaN", "true", '{"query":NaN}'):
            with self.subTest(arguments=arguments):
                projection = project_provider_history({"input": [call(arguments)]})
                self.assertEqual(projection.decisions[0]["state"], "REJECTED")

    def test_schema_validation_failure_is_not_replayable(self):
        self.assert_isolated({"ok": False, "status": "validation_failed", "data": {
            "reason": "invalid_action", "execution_succeeded": False,
        }}, "REJECTED")

    def test_unauthorized_proposal_remains_rejected_not_user_authorization(self):
        projection = self.assert_isolated({"ok": False, "status": "validation_failed", "data": {
            "reason": "semantic_constraint_conflict", "error_kind": "semantic_validation",
            "authorization": {"state": "unknown", "model_proposal": True},
        }}, "REJECTED")
        self.assertNotIn('"state": "granted"', json.dumps(projection.request))

    def test_failed_execution_retains_requested_actual_distinction(self):
        projection = self.assert_isolated({"ok": False, "data": {
            "execution_status": "network_failure", "requested_provider": "google",
            "actual_provider": None, "execution_succeeded": False,
        }}, "FAILED")
        text = projection.request["input"][1]["content"][0]["text"]
        self.assertIn('"actual_provider": null', text)
        self.assertIn('"execution_succeeded": false', text)

    def test_timeout_crash_and_partial_execution_are_failed(self):
        for status in ("timeout", "failed", "partial", "incomplete"):
            with self.subTest(status=status):
                self.assert_isolated({"ok": False, "status": status}, "FAILED")

    def test_cancelled_execution_is_terminal(self):
        for payload in ("aborted", "Tool execution aborted",
                        "dynamic tool call was cancelled before receiving a response",
                        {"ok": False, "status": "cancelled"}):
            with self.subTest(payload=payload):
                self.assert_isolated(payload, "CANCELLED")

    def test_successful_calls_and_results_are_unchanged(self):
        request = {"input": [call(), output({"ok": True, "status": "success"})]}
        projection = project_provider_history(request)
        self.assertEqual(projection.request, request)
        self.assertEqual(projection.decisions, ())

    def test_low_relevance_success_is_not_execution_failure(self):
        request = {"input": [call(), output({"ok": True, "data": {
            "execution_status": "success", "evidence_status": "low_relevance",
        }})]}
        self.assertEqual(project_provider_history(request).request, request)

    def test_normal_user_and_custom_freeform_calls_are_not_json_validated(self):
        request = {"input": [
            {"role": "user", "content": "hello"},
            {"type": "custom_tool_call", "name": "apply_patch", "input": "not JSON"},
        ]}
        self.assertEqual(project_provider_history(request).request, request)

    def test_call_ids_do_not_contaminate_unrelated_successful_pairs(self):
        items = [call("broken", "bad"), output("aborted", "bad"), call(call_id="good"),
                 output({"ok": True}, "good"), {"role": "user", "content": "continue"}]
        projection = project_provider_history({"input": items})
        self.assertEqual(projection.request["input"][2:], items[2:])
        self.assertEqual({d["call_id"] for d in projection.decisions}, {"bad"})

    def test_projection_is_idempotent(self):
        first = project_provider_history({"input": [call("invalid"), output("aborted")]})
        second = project_provider_history(first.request)
        self.assertEqual(first.request, second.request)
        self.assertEqual(second.decisions, ())

    def test_reloading_same_raw_history_recreates_same_projection(self):
        request = {"input": [call("invalid"), output("aborted")]}
        first = project_provider_history(request)
        reloaded = json.loads(json.dumps(request))
        self.assertEqual(first, project_provider_history(reloaded))

    def test_previous_input_messages_supported(self):
        projection = project_provider_history({"input": "hi", "previous_input_messages": [call("broken")]})
        self.assertEqual(projection.request["input"], "hi")
        self.assertEqual(projection.decisions[0]["field"], "previous_input_messages")

    def test_native_turn_identity_retained_in_decision(self):
        item = call("invalid")
        item["internal_chat_message_metadata_passthrough"] = {"turn_id": "turn-1"}
        self.assertEqual(project_provider_history({"input": [item]}).decisions[0]["turn_id"], "turn-1")

    def test_content_item_tool_output_supported(self):
        item = output([{"type": "input_text", "text": '{"ok":false,"status":"failed"}'}])
        projection = project_provider_history({"input": [call(), item]})
        self.assertEqual(projection.decisions[0]["state"], "FAILED")

    def test_canonical_trajectory_keeps_original_payload_and_failure(self):
        malformed = '{"query":BROKEN}'
        with tempfile.TemporaryDirectory() as tmp:
            with HarnessTrajectoryWriter(tmp, run_id="fact") as writer:
                raw = {"method": "rawResponseItem/completed", "params": {
                    "threadId": "thread", "turnId": "turn", "item": call(malformed),
                }}
                writer.write_raw_event(raw)
                writer.write_raw_event({"method": "rawResponseItem/completed", "params": {
                    "threadId": "thread", "turnId": "turn", "item": output("failed to parse function arguments: error"),
                }})
                writer.write_raw_event({"method": "turn/completed", "params": {
                    "threadId": "thread", "turn": {"id": "turn", "status": "failed"},
                }})
                project_provider_history({"input": [call(malformed), output("aborted")]})
            records = read_trajectory_jsonl(Path(tmp) / "fact.trajectory.jsonl")
            self.assertTrue(validate_trajectory_records(records.records).ok)
            self.assertIn(malformed, json.dumps(records.records[0].raw_event, ensure_ascii=False).replace('\\"', '"'))
            self.assertTrue(any(r.event_type == "TOOL_RESULT" for r in records.records))


class ResponsesBridgeTests(unittest.TestCase):
    def test_stream_and_status_transparent_with_safe_history_and_no_body_journal(self):
        received = []

        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                received.append(request)
                for item in request["input"]:
                    if item.get("type") == "function_call":
                        json.loads(item["arguments"])
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b'data: {"type":"response.completed"}\n\n')

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                journal = Path(tmp) / "decisions.jsonl"
                with ProviderHistoryBridge(f"http://127.0.0.1:{upstream.server_port}", journal_path=journal) as bridge:
                    port = int(bridge.base_url.rsplit(":", 1)[1])
                    connection = http.client.HTTPConnection("127.0.0.1", port)
                    request = {"input": [call('{"query": SECRET_PLACEHOLDER}'), output("aborted")], "stream": True}
                    connection.request("POST", "/v1/responses", json.dumps(request), {
                        "Content-Type": "application/json", "thread-id": "thread-1",
                    })
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b'data: {"type":"response.completed"}\n\n')
                    connection.close()
                    self.assertEqual(bridge.projected_count, 2)
                text = journal.read_text()
                self.assertNotIn("SECRET_PLACEHOLDER", text)
                self.assertNotIn('"arguments":', text)
                self.assertEqual(len(text.splitlines()), 2)
                self.assertEqual(json.loads(text.splitlines()[0])["thread_id"], "thread-1")
            self.assertTrue(all(i["type"] == "message" for i in received[0]["input"]))
        finally:
            upstream.shutdown()
            upstream.server_close()
            thread.join()

    def test_frozen_or_nonlocal_endpoints_rejected(self):
        for url in ("http://127.0.0.1:8001", "https://127.0.0.1:8002",
                    "http://example.com:8002", "http://user:key@127.0.0.1:8002"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                ProviderHistoryBridge(url, journal_path=Path("unused"))


class InteractiveToolBoundaryTests(unittest.TestCase):
    def test_projection_failure_does_not_exit_or_erase_execution_truth(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import h3_harness_interactive_repl as repl
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = Mock()
            dispatch = adapter.dispatch.return_value
            dispatch.to_app_server_response.side_effect = ValueError("contract exceeds budget")
            dispatch.tool_result.data = {"execution_status": "success", "execution_succeeded": True,
                                         "http_attempted": True, "actual_provider": "google"}
            app = repl.InteractiveAppServer(codex=root / "codex", codex_home=root / "home", workspace=root,
                base_url="http://127.0.0.1:8002", adapter=adapter,
                events_path=root / "events", stderr_path=root / "stderr", turn_timeout=10)
            with patch.object(app, "_send") as send:
                app._handle_tool_call({"id": 1, "params": {
                    "callId": "attempt", "tool": "web_search", "arguments": {},
                }})
            payload = json.loads(send.call_args.args[0]["result"]["contentItems"][0]["text"])
            self.assertEqual(payload["data"]["reason"], "result_projection_failed")
            self.assertTrue(payload["data"]["execution_succeeded"])
            self.assertFalse(payload["data"]["result_available"])
            self.assertFalse(payload["data"]["retryable"])
            self.assertFalse(send.call_args.args[0]["result"]["success"])
            projected = project_provider_history({"input": [call(), output(payload)]})
            fact = json.loads(projected.request["input"][1]["content"][0]["text"].split("\n", 1)[1])
            self.assertTrue(fact["observation"]["execution_succeeded"])
            self.assertEqual(fact["observation"]["failure_stage"], "result_projection")

    def test_restarting_same_artifact_directory_creates_distinct_trajectory_runs(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import h3_harness_interactive_repl as repl
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = repl.InteractiveAppServer(
                codex=root / "codex", codex_home=root / "home", workspace=root,
                base_url="http://127.0.0.1:8002", adapter=Mock(),
                events_path=root / "events.jsonl", stderr_path=root / "stderr", turn_timeout=10,
            )
            replies = [{"result": {}}, {"result": {"thread": {"id": "thread"}}}] * 2
            with patch.object(repl.subprocess, "Popen"), \
                    patch.object(repl, "ProviderHistoryBridge"), \
                    patch.object(repl.threading, "Thread"), \
                    patch.object(app, "_request", side_effect=replies):
                try:
                    app.start()
                    first = app._trajectory_writer.canonical_path
                    app.close()
                    app.start(resume_thread_id="thread")
                    second = app._trajectory_writer.canonical_path
                    self.assertNotEqual(first, second)
                finally:
                    app.close()

    def test_uncaught_adapter_failure_returns_terminal_tool_result(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import h3_harness_interactive_repl as repl
        for error, status in ((ValueError("invalid"), "validation_failed"),
                              (TimeoutError("timeout"), "failed"), (RuntimeError("crash"), "failed")):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                adapter = Mock()
                adapter.dispatch.side_effect = error
                app = repl.InteractiveAppServer(
                    codex=root / "codex", codex_home=root / "home", workspace=root,
                    base_url="http://127.0.0.1:8002", adapter=adapter,
                    events_path=root / "events", stderr_path=root / "stderr", turn_timeout=10,
                )
                with patch.object(app, "_send") as send:
                    app._handle_tool_call({"id": 1, "params": {
                        "callId": "attempt", "tool": "web_search", "arguments": {},
                    }})
                response = send.call_args.args[0]["result"]
                self.assertFalse(response["success"])
                payload = json.loads(response["contentItems"][0]["text"])
                self.assertEqual(payload["status"], status)
                self.assertFalse(payload["data"]["execution_succeeded"])


if __name__ == "__main__":
    unittest.main()
