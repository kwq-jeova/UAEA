from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

from harness.io_contract import turn_context_payload
from harness.semantic_promotion_audit import build_promotion_audit
from harness.semantic_state_adapter import HarnessSemanticStateAdapter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT))
from h3_harness_interactive_repl import InteractiveAppServer  # noqa: E402


def _report(adapter, stage="PRE_TURN"):
    snapshot = adapter.snapshot("thread")
    context = turn_context_payload([], semantic_projection=snapshot["last_projection"])
    return build_promotion_audit(snapshot, stage=stage, additional_context=context)


def _item(report, adapter, value):
    record = next(item for item in adapter.snapshot("thread")["semantic_items"]
                  if item["metadata"]["value"] == value and item["status"] == "active")
    return next(item for item in report["items"] if item["semantic_item_id"] == record["object_id"])


class SemanticPromotionShadowAuditTests(unittest.TestCase):
    def test_topic_does_not_gain_auditor_authority(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "研究编译器的优化方向", turn_id="t1")
        report = _report(adapter)
        topic = next(item for item in report["items"] if item["kind"] == "topic")
        self.assertFalse(topic["in_current_constraint_surface"])
        self.assertEqual(report["limits"]["authority_warrant"], "NOT_EVALUATED")
        self.assertFalse(report["limits"]["grants_authority"])

    def test_historical_soft_promotion_is_observed_not_rewritten(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "研究商业化方向，可以看看商业发布论坛", turn_id="t1")
        before = deepcopy(adapter.snapshot("thread"))
        historical = deepcopy(before)
        historical["constraints"] = ["exclude:commercial_promotional"]
        historical["last_projection"]["constraints"] = historical["constraints"]
        item_id = next(item["object_id"] for item in historical["semantic_items"]
                       if item["metadata"]["value"] == "exclude:commercial_promotional")
        historical["last_projection"]["semantic_bindings"] = [{"item_id": item_id}]
        report = build_promotion_audit(historical, stage="HISTORICAL_SNAPSHOT", additional_context={
            "uaea.semantic_state_projection": {"kind": "application",
                                               "value": json.dumps(historical["last_projection"])},
        })
        item = _item(report, adapter, "exclude:commercial_promotional")
        self.assertEqual(item["declared_strength"], "soft")
        self.assertTrue(item["in_current_constraint_surface"])
        self.assertTrue(item["in_last_projection_constraint_surface"])
        self.assertIn("SOFT_ITEM_IN_CONSTRAINT_SURFACE", item["notices"])
        self.assertEqual(item["promotion_basis"], "NOT_RECORDED")
        self.assertEqual(adapter.snapshot("thread"), before)

    def test_explicit_directive_and_authorization_decision_remain_unchanged(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn("thread", "只使用 Google，不允许 fallback", turn_id="t1")
        before = deepcopy(projection.payload)
        accepted = adapter.validate_tool_action(
            "thread", "web.search", {"provider": "google", "allow_fallback": False},
            turn_id="t1", call_id="legal",
        )
        rejected = adapter.validate_tool_action(
            "thread", "web.search", {"provider": "google", "allow_fallback": True},
            turn_id="t1", call_id="rejected",
        )
        report = _report(adapter)
        self.assertTrue(accepted["valid"])
        self.assertFalse(rejected["valid"])
        self.assertEqual([True, False], [item["valid"] for item in report["observed_validation_decisions"]])
        self.assertEqual(report["observed_validation_decisions"][-1]["authorization_state"], "denied")
        self.assertEqual(report["observed_validation_decisions"][0]["validation_boundary"],
                         "semantic_state_action_validation")
        self.assertEqual(report["observed_validation_decisions"][0]["authorization_subject"],
                         "fallback_permission")
        self.assertTrue(report["limits"]["validation_acceptance_is_not_execution_proof"])
        self.assertEqual(before, projection.payload)
        self.assertEqual(_item(report, adapter, "web.provider=google")["promotion_basis"], "RECORDED")
        self.assertNotIn("PROMOTION_BASIS_NOT_RECORDED", _item(report, adapter, "web.provider=google")["notices"])

    def test_native_identity_is_retained_and_pre_turn_does_not_borrow_previous_turn(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "只关注论文", turn_id="t1")
        adapter.consume_raw_event({"message": {"method": "item/completed", "params": {
            "threadId": "thread", "turnId": "t1", "item": {
                "id": "user1", "type": "userMessage", "content": [{"type": "text", "text": "只关注论文"}],
            },
        }}}, raw_event_reference={"path": "events.jsonl", "line": 1})
        adapter.prepare_turn("thread", "继续研究")
        report = _report(adapter)
        source = _item(report, adapter, "prefer:academic_papers")["source"]
        self.assertEqual(source["identity"]["turn_id"], "t1")
        self.assertEqual(source["identity"]["item_id"], "user1")
        self.assertEqual(source["raw_event_reference"], {
            "path": "events.jsonl", "line": 1, "method": "item/completed",
        })
        self.assertEqual(report["turn_id"], "")
        self.assertEqual(report["prior_turn_id"], "t1")
        self.assertTrue(report["input_id"].startswith("input:"))

    def test_superseded_identical_value_is_not_current_membership(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "只使用 Google", turn_id="t1")
        adapter.prepare_turn("thread", "继续，只使用 Google", turn_id="t2")
        report = _report(adapter)
        old = next(item for item in report["items"] if item["lifecycle_status"] == "superseded")
        self.assertTrue(old["value_in_current_constraints"])
        self.assertFalse(old["effective_member"])
        self.assertFalse(old["in_current_constraint_surface"])
        self.assertFalse(old["in_last_projection_constraint_surface"])
        self.assertTrue(old["superseded_by"])

    def test_terminal_expiration_is_not_confused_with_previous_projection(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "本轮只使用 Google", turn_id="t1")
        adapter.consume_raw_event({"message": {"method": "turn/completed", "params": {
            "threadId": "thread", "turn": {"id": "t1", "status": "completed"},
        }}})
        report = _report(adapter, "POST_TURN")
        expired = next(item for item in report["items"] if item["lifecycle_status"] == "expired")
        self.assertFalse(expired["effective_member"])
        self.assertFalse(expired["in_current_constraint_surface"])
        self.assertTrue(expired["in_last_projection_constraint_surface"])
        self.assertFalse(report["projection"]["is_current_effective_state"])

    def test_old_snapshot_missing_membership_and_transport_are_unknown(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "只使用 Google", turn_id="t1")
        snapshot = adapter.snapshot("thread")
        snapshot.pop("effective_semantic_item_ids")
        report = build_promotion_audit(snapshot, stage="HISTORICAL_SNAPSHOT")
        self.assertFalse(report["effective_membership_known"])
        self.assertEqual(report["projection"]["transport_kind"], "UNKNOWN")
        item = next(item for item in report["items"] if item["kind"] == "capability_constraint")
        self.assertIsNone(item["effective_member"])
        self.assertIsNone(item["in_current_constraint_surface"])

    def test_untrusted_transport_is_not_reported_as_application(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "只关注论坛", turn_id="t1")
        snapshot = adapter.snapshot("thread")
        context = {"uaea.semantic_state_projection": {
            "kind": "untrusted", "value": json.dumps(snapshot["last_projection"]),
        }}
        report = build_promotion_audit(snapshot, stage="PRE_TURN", additional_context=context)
        self.assertEqual(report["projection"]["transport_kind"], "untrusted")
        self.assertFalse(any("CONSTRAINT_IN_APPLICATION_CONTEXT" in item["notices"] for item in report["items"]))

    def test_raw_text_arguments_and_credentials_are_not_copied(self):
        secret = "synthetic-secret-do-not-log"
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "只关注论坛", turn_id="t1")
        snapshot = adapter.snapshot("thread")
        snapshot["last_user_input"] = secret
        snapshot["last_agent_output"] = secret
        snapshot["semantic_items"][0]["metadata"]["value"] = secret
        snapshot["semantic_items"][0]["metadata"]["provenance"]["source_text_excerpt"] = secret
        snapshot["semantic_items"][0]["metadata"]["provenance"]["SERPAPI_KEY"] = secret
        snapshot["action_decisions"] = [{"proposed_action": {"arguments": {"query": secret}}}]
        before = deepcopy(snapshot)
        report = build_promotion_audit(snapshot, stage="PRE_TURN")
        self.assertNotIn(secret, json.dumps(report))
        self.assertEqual(snapshot, before)

    def test_threads_remain_isolated_and_goal_is_not_created(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "只使用 Google，不允许 fallback", turn_id="t1")
        adapter.prepare_turn("other", "研究编译器", turn_id="t2")
        report = build_promotion_audit(adapter.snapshot("other"), stage="PRE_TURN")
        self.assertFalse(any(item["in_current_constraint_surface"] for item in report["items"]))
        self.assertIsNone(adapter.snapshot("other")["phase1_runtime_snapshot"]["active_goal"])


class InteractivePromotionAuditTests(unittest.TestCase):
    def _app(self):
        app = InteractiveAppServer(
            codex=Path("unused"), codex_home=Path("unused"), workspace=Path("unused"),
            base_url="http://127.0.0.1:8002/v1", adapter=Mock(),
            events_path=Path("unused/events.jsonl"), stderr_path=Path("unused/stderr.log"),
            turn_timeout=10,
        )
        app.thread_id = "thread"
        app._request = Mock(return_value={"params": {"turn": {"status": "completed"}}})
        return app

    def test_journal_append_flush_and_model_request_are_independent(self):
        app = self._app()
        app._promotion_audit_file = io.StringIO()
        with redirect_stdout(io.StringIO()):
            app.run_turn("研究商业化方向，可以看看商业发布论坛")
        sent = app._request.call_args.args[0]
        expected = turn_context_payload([], semantic_projection=app.semantic_state.snapshot("thread")["last_projection"])
        self.assertEqual(sent["params"]["additionalContext"], expected)
        self.assertNotIn("uaea.semantic_promotion_shadow_audit", sent["params"]["additionalContext"])
        app._write_promotion_audit("POST_ACTION_VALIDATION")
        rows = [json.loads(row) for row in app._promotion_audit_file.getvalue().splitlines()]
        self.assertEqual([1, 2], [row["audit_sequence"] for row in rows])
        self.assertEqual(["PRE_TURN", "POST_ACTION_VALIDATION"], [row["stage"] for row in rows])
        self.assertFalse(rows[0]["snapshot_reference"]["persisted_at_this_stage"])

    def test_journal_failure_does_not_block_turn_or_print_exception_contents(self):
        app = self._app()
        app._promotion_audit_file = Mock()
        app._promotion_audit_file.write.side_effect = OSError("synthetic-secret")
        output = io.StringIO()
        with redirect_stdout(output):
            app.run_turn("只使用 Google，不允许 fallback")
        app._request.assert_called_once()
        self.assertIn("shadow record failed: OSError", output.getvalue())
        self.assertNotIn("synthetic-secret", output.getvalue())

    def test_post_turn_hook_keeps_expiration_and_original_snapshot(self):
        app = self._app()
        app._promotion_audit_file = io.StringIO()
        app._events_file = io.StringIO()
        app._semantic_snapshots_file = io.StringIO()
        projection = app.semantic_state.prepare_turn("thread", "本轮只关注论文", turn_id="t1")
        app._last_turn_context = turn_context_payload([], semantic_projection=projection.payload)
        completed = {"method": "turn/completed", "params": {
            "threadId": "thread", "turn": {"id": "t1", "status": "completed"},
        }}
        app._queue.put(("stdout", json.dumps(completed)))
        self.assertEqual(app._wait_for(lambda message: message == completed, 1), completed)
        report = json.loads(app._promotion_audit_file.getvalue())
        self.assertEqual(report["stage"], "POST_TURN")
        self.assertEqual(report["turn_id"], "t1")
        self.assertTrue(report["snapshot_reference"]["persisted_at_this_stage"])
        original = json.loads(app._semantic_snapshots_file.getvalue())["snapshot"]
        self.assertEqual(original, app.semantic_state.snapshot("thread"))
        expired = next(item for item in report["items"] if item["lifecycle_status"] == "expired")
        self.assertFalse(expired["in_current_constraint_surface"])

    def test_tool_observation_is_retained_without_a_post_turn_snapshot(self):
        app = self._app()
        app._promotion_audit_file = io.StringIO()
        app._events_file = io.StringIO()
        app._semantic_snapshots_file = io.StringIO()
        app._trajectory_writer = Mock(run_id="test-run")
        projection = app.semantic_state.prepare_turn("thread", "本轮只关注论文", turn_id="t1")
        app._last_turn_context = turn_context_payload([], semantic_projection=projection.payload)
        completed = {"method": "item/completed", "params": {
            "threadId": "thread", "turnId": "t1", "item": {
                "id": "call1", "type": "dynamicToolCall", "tool": "web_search",
                "arguments": {"query": "compiler research"}, "status": "failed",
                "success": False, "contentItems": [{"type": "inputText", "text": json.dumps({
                    "ok": False, "message": "Attempt rejected", "data": {
                        "execution_status": "validation_failed", "http_attempted": False,
                    },
                })}],
            },
        }}
        app._queue.put(("stdout", json.dumps(completed)))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(app._wait_for(lambda message: message == completed, 1), completed)
        self.assertEqual(app._promotion_audit_file.getvalue(), "")
        self.assertEqual(app._semantic_snapshots_file.getvalue(), "")
        self.assertEqual(json.loads(app._events_file.getvalue())["message"], completed)
        recorded = app._trajectory_writer.write_raw_event.call_args.args[0]
        self.assertEqual(recorded["message"], completed)
        state = app.semantic_state.snapshot("thread")
        self.assertEqual(state["completed_turn_count"], 0)
        self.assertEqual(state["constraints"], [])
        self.assertEqual(state["source_preferences"], ["prefer:academic_papers"])
        self.assertEqual(len(state["semantic_observations"]), 1)
        observation = state["semantic_observations"][0]
        self.assertEqual(observation["execution_observation"]["status"], "failure")
        self.assertEqual(observation["provenance"]["item_id"], "call1")
        self.assertEqual(observation["provenance"]["turn_id"], "t1")

    def test_observation_then_terminal_produces_only_one_post_turn(self):
        app = self._app()
        app._promotion_audit_file = io.StringIO()
        app._events_file = io.StringIO()
        app._semantic_snapshots_file = io.StringIO()
        projection = app.semantic_state.prepare_turn("thread", "只使用 Google，不允许 fallback", turn_id="t1")
        app._last_turn_context = turn_context_payload([], semantic_projection=projection.payload)
        observation = {"method": "item/completed", "params": {
            "threadId": "thread", "turnId": "t1", "item": {
                "id": "command1", "type": "commandExecution", "command": "read README.md",
                "status": "completed", "exitCode": 1, "aggregatedOutput": "Execution failed",
            },
        }}
        terminal = {"method": "turn/completed", "params": {
            "threadId": "thread", "turn": {"id": "t1", "status": "completed"},
        }}
        for message in (observation, terminal):
            app._queue.put(("stdout", json.dumps(message)))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(app._wait_for(lambda message: message == terminal, 1), terminal)
        rows = [json.loads(line) for line in app._promotion_audit_file.getvalue().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["stage"], "POST_TURN")
        self.assertEqual(rows[0]["thread_id"], "thread")
        self.assertEqual(rows[0]["turn_id"], "t1")
        snapshots = [json.loads(line) for line in app._semantic_snapshots_file.getvalue().splitlines()]
        self.assertEqual(len(snapshots), 1)
        state = snapshots[0]["snapshot"]
        self.assertEqual(state["constraints"], ["web.provider=google", "web.fallback=forbidden"])
        self.assertEqual(state["semantic_observations"][0]["provenance"]["item_id"], "command1")
        self.assertEqual(len(app._events_file.getvalue().splitlines()), 2)

    def test_observation_cannot_be_passed_directly_as_a_terminal_snapshot(self):
        app = self._app()
        app._promotion_audit_file = io.StringIO()
        app._write_promotion_audit("POST_TURN", snapshot={
            "execution_observation": {}, "semantic_observation": {}, "provenance": {},
        })
        self.assertEqual(app._promotion_audit_file.getvalue(), "")
        self.assertEqual(app._promotion_audit_sequence, 0)

    def test_failed_and_cancelled_turns_keep_terminal_snapshot_identity(self):
        for status in ("failed", "cancelled"):
            with self.subTest(status=status):
                app = self._app()
                app._promotion_audit_file = io.StringIO()
                app._events_file = io.StringIO()
                app._semantic_snapshots_file = io.StringIO()
                projection = app.semantic_state.prepare_turn("thread", "本轮只关注论坛", turn_id="t1")
                app._last_turn_context = turn_context_payload([], semantic_projection=projection.payload)
                terminal = {"method": "turn/completed", "params": {
                    "threadId": "thread", "turn": {"id": "t1", "status": status},
                }}
                app._queue.put(("stdout", json.dumps(terminal)))
                self.assertEqual(app._wait_for(lambda message: message == terminal, 1), terminal)
                row = json.loads(app._promotion_audit_file.getvalue())
                self.assertEqual(row["thread_id"], "thread")
                self.assertEqual(row["turn_id"], "t1")
                self.assertEqual(row["stage"], "POST_TURN")
                state = json.loads(app._semantic_snapshots_file.getvalue())["snapshot"]
                self.assertEqual(state["last_terminal_state"], status)
                self.assertEqual(state["completed_turn_count"], 1)
                self.assertEqual(state["constraints"], [])

    def test_action_hook_does_not_modify_tool_response(self):
        app = self._app()
        app._promotion_audit_file = io.StringIO()
        app.semantic_state.prepare_turn("thread", "只使用 Google，不允许 fallback", turn_id="t1")
        response = {"success": False, "contentItems": [{"type": "inputText", "text": "rejected"}]}
        dispatch = Mock()
        dispatch.to_app_server_response.return_value = deepcopy(response)
        dispatch.to_trace_metadata.return_value = {
            "action_request": {"capability": "web.search", "request_id": "call"},
            "execution_observation": {"status": "failure"},
        }
        app.adapter.dispatch.return_value = dispatch
        app._send = Mock()
        with redirect_stdout(io.StringIO()):
            app._handle_tool_call({"id": 2, "params": {
                "callId": "call", "tool": "web_search", "arguments": {},
            }})
        self.assertEqual(app._send.call_args.args[0]["result"], response)
        self.assertEqual(json.loads(app._promotion_audit_file.getvalue())["stage"], "POST_ACTION_VALIDATION")


if __name__ == "__main__":
    unittest.main()
