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
from harness.semantic_authority import (
    EXECUTION_CONSTRAINT, compact_semantic_bindings, expand_semantic_binding,
    has_execution_authority,
)
from harness.semantic_promotion_audit import build_promotion_audit
from harness.semantic_state_adapter import HarnessSemanticStateAdapter, ProjectionCapacityError


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from h3_harness_interactive_repl import InteractiveAppServer  # noqa: E402


THREAD_ID = "01a129d7-a908-7303-977f-c086b030474e"
MULTI_CONSTRAINT_INPUT = "仅使用 Google 搜索 AI agent，不要使用 Bing，不要使用 DuckDuckGo，禁止 fallback。"
EXPECTED_CONSTRAINTS = [
    "web.provider=google", "web.exclude_provider=bing",
    "web.exclude_provider=duckduckgo", "web.fallback=forbidden",
]


def _expanded(payload):
    return [expand_semantic_binding(item, payload.get("semantic_binding_defaults"))
            for item in payload["semantic_bindings"]]


class ProjectionCapacityTests(unittest.TestCase):
    def test_original_multi_constraint_regression_fits_unchanged_default_budget(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn(THREAD_ID, MULTI_CONSTRAINT_INPUT)
        snapshot = adapter.snapshot(THREAD_ID)
        raw = adapter._projection_payload(adapter._state_for(THREAD_ID), relation=snapshot["turn_relation"])
        self.assertGreater(len(json.dumps(raw, ensure_ascii=False, sort_keys=True)), 2400)
        self.assertEqual(adapter.max_projection_chars, 2400)
        self.assertLessEqual(len(projection.to_context_value()), 2400)
        self.assertEqual(projection.payload["constraints"], EXPECTED_CONSTRAINTS)
        self.assertEqual(_expanded(projection.payload), raw["semantic_bindings"])
        self.assertEqual(snapshot["last_projection"], projection.payload)
        self.assertEqual(snapshot["phase1_projection_count"], 1)
        self.assertTrue(all(has_execution_authority(item) for item in _expanded(projection.payload)))

    def test_compact_transport_keeps_model_visible_authority_and_scope(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn(THREAD_ID, MULTI_CONSTRAINT_INPUT)
        before = deepcopy(projection.payload)
        context = turn_context_payload([], semantic_projection=projection.payload)
        application = context["uaea.semantic_state_projection"]
        interpretations = context["uaea.semantic_interpretations"]
        authority = json.loads(application["value"])
        self.assertEqual(application["kind"], "application")
        self.assertEqual(interpretations["kind"], "untrusted")
        self.assertEqual(authority["constraints"], EXPECTED_CONSTRAINTS)
        self.assertEqual(_expanded(authority), _expanded(projection.payload))
        self.assertNotIn("topic", authority)
        self.assertEqual(projection.payload, before)
        self.assertLessEqual(len(application["value"]) + len(interpretations["value"]), 2400)
        for item in _expanded(authority):
            self.assertEqual(item["authority_level"], EXECUTION_CONSTRAINT)
            self.assertEqual(item["scope"], "task")
            self.assertEqual(item["owner"], projection.payload["task_id"])
            self.assertEqual(item["promotion_basis"]["input_id"], item["provenance"]["input_id"])
        report = build_promotion_audit(adapter.snapshot(THREAD_ID), stage="PRE_TURN", additional_context=context)
        projected = {item["semantic_item_id"] for item in report["items"]
                     if item["in_last_projection_constraint_surface"]}
        self.assertEqual(projected, set(adapter.snapshot(THREAD_ID)["execution_authority_item_ids"]))

    def test_compaction_is_not_specific_to_one_user_string_or_scope(self):
        for text in (
            "只使用 Bing 搜索编译器，不要使用 Google，不要使用 DuckDuckGo，禁止 fallback。",
            "以后所有搜索都仅使用 Google，不要使用 Bing，不要使用 DuckDuckGo，禁止 fallback。",
        ):
            with self.subTest(text=text):
                adapter = HarnessSemanticStateAdapter()
                projection = adapter.prepare_turn(THREAD_ID, text)
                raw = adapter._projection_payload(adapter._state_for(THREAD_ID), relation=projection.payload["turn_relation"])
                self.assertLessEqual(len(projection.to_context_value()), 2400)
                self.assertEqual(_expanded(projection.payload), raw["semantic_bindings"])
                self.assertEqual(len(projection.payload["constraints"]), 4)

    def test_in_budget_projection_stays_byte_compatible(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn(THREAD_ID, "只使用 Google，不允许 fallback")
        raw = adapter._projection_payload(adapter._state_for(THREAD_ID), relation=projection.payload["turn_relation"])
        self.assertEqual(projection.payload, raw)
        self.assertNotIn("semantic_binding_defaults", projection.payload)
        self.assertEqual(projection.to_context_value(), json.dumps(raw, ensure_ascii=False, sort_keys=True))

    def test_different_sources_and_scopes_are_not_coalesced(self):
        adapter = HarnessSemanticStateAdapter(max_projection_chars=8000)
        for text in (
            "以后所有搜索都不要使用 Bing", "仅使用 Google 搜索 AI agent",
            "继续研究，不要使用 DuckDuckGo", "继续研究，禁止 fallback",
        ):
            projection = adapter.prepare_turn(THREAD_ID, text)
        before = deepcopy(projection.payload)
        bindings, shared = compact_semantic_bindings(before["semantic_bindings"])
        compact = {**before, "semantic_bindings": bindings, "semantic_binding_defaults": shared}
        self.assertNotIn("provenance", shared)
        self.assertNotIn("scope", shared)
        self.assertNotIn("owner", shared)
        self.assertEqual(_expanded(compact), before["semantic_bindings"])
        self.assertEqual(len({item["provenance"]["input_id"] for item in _expanded(compact)}), 4)
        model = json.loads(turn_context_payload([], semantic_projection=compact)["uaea.semantic_state_projection"]["value"])
        self.assertEqual(_expanded(model), before["semantic_bindings"])
        self.assertEqual(model["constraints"], before["constraints"])

    def test_shared_metadata_never_replaces_independent_promotion_checks(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn(THREAD_ID, MULTI_CONSTRAINT_INPUT)
        for mutation in ("source", "input", "basis", "value", "authority", "unknown_default"):
            with self.subTest(mutation=mutation):
                altered = deepcopy(projection.payload)
                binding = altered["semantic_bindings"][0]
                shared = altered["semantic_binding_defaults"]
                if mutation == "source":
                    shared["provenance"]["source_event_type"] = "AGENT_OUTPUT"
                elif mutation == "input":
                    shared["provenance"]["input_id"] = "different-input"
                elif mutation == "basis":
                    binding.pop("promotion_basis")
                elif mutation == "value":
                    binding["value"] = "web.provider=bing"
                    altered["constraints"].append("web.provider=bing")
                elif mutation == "authority":
                    binding["authority_level"] = "interpretation"
                else:
                    shared["promotion_basis"] = binding["promotion_basis"]
                context = turn_context_payload([], semantic_projection=altered)
                authority = json.loads(context["uaea.semantic_state_projection"]["value"])
                self.assertNotIn("web.provider=google", authority["constraints"])
                self.assertNotIn("web.provider=bing", authority["constraints"])
                self.assertTrue(all(has_execution_authority(item) for item in _expanded(authority)))

    def test_source_preferences_stay_non_authoritative_even_after_compaction(self):
        adapter = HarnessSemanticStateAdapter(max_projection_chars=3000)
        projection = adapter.prepare_turn(THREAD_ID, MULTI_CONSTRAINT_INPUT + "论坛资料也可以")
        snapshot = adapter.snapshot(THREAD_ID)
        self.assertIn("prefer:forums", snapshot["source_preferences"])
        self.assertEqual(snapshot["constraints"], EXPECTED_CONSTRAINTS)
        context = turn_context_payload([], semantic_projection=projection.payload)
        authority = json.loads(context["uaea.semantic_state_projection"]["value"])
        self.assertEqual(authority["constraints"], EXPECTED_CONSTRAINTS)
        self.assertNotIn("source_preferences", authority)
        self.assertEqual(context["uaea.semantic_interpretations"]["kind"], "untrusted")
        self.assertTrue(projection.payload["interpretations"])
        self.assertIn("semantic_binding_defaults", projection.payload)
        self.assertTrue(all(item["authority_level"] == "interpretation"
                            for item in projection.payload["interpretations"]))
        self.assertTrue(any(item["metadata"]["value"] == "prefer:forums"
                            and item["metadata"]["authority_level"] == "interpretation"
                            for item in snapshot["semantic_items"]))

    def test_capacity_exhaustion_keeps_constraints_and_no_projection_record(self):
        adapter = HarnessSemanticStateAdapter(max_projection_chars=600)
        with self.assertRaises(ProjectionCapacityError) as raised:
            adapter.prepare_turn(THREAD_ID, MULTI_CONSTRAINT_INPUT)
        self.assertGreater(raised.exception.required_chars, raised.exception.budget_chars)
        snapshot = adapter.snapshot(THREAD_ID)
        self.assertEqual(snapshot["constraints"], EXPECTED_CONSTRAINTS)
        self.assertEqual(snapshot["last_projection"], {})
        self.assertEqual(snapshot["phase1_projection_count"], 0)

    def test_projection_compression_does_not_change_action_validation(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn(THREAD_ID, MULTI_CONSTRAINT_INPUT)
        for arguments, expected in (
            ({"provider": "google", "allow_fallback": False}, True),
            ({"provider": "google"}, False),
            ({"provider": "google", "allow_fallback": True}, False),
            ({"provider": "bing", "allow_fallback": False}, False),
        ):
            decision = adapter.validate_tool_action(THREAD_ID, "web.search", arguments)
            self.assertEqual(decision["valid"], expected)
            self.assertEqual(decision["active_constraints"], projection.payload["constraints"])
            self.assertEqual(decision["effective_state_id"], projection.payload["effective_state_id"])

    def test_four_constraints_survive_next_turn_without_duplicate_authority(self):
        adapter = HarnessSemanticStateAdapter()
        first = adapter.prepare_turn(THREAD_ID, MULTI_CONSTRAINT_INPUT, turn_id="turn1")
        source_ids = {item["promotion_basis"]["input_id"] for item in _expanded(first.payload)}
        adapter.consume_raw_event({"method": "turn/completed", "params": {
            "threadId": THREAD_ID, "turn": {"id": "turn1", "status": "completed"},
        }})
        next_projection = adapter.prepare_turn(THREAD_ID, "继续寻找近期研究", turn_id="turn2")
        self.assertEqual(next_projection.payload["constraints"], EXPECTED_CONSTRAINTS)
        self.assertLessEqual(len(next_projection.to_context_value()), 2400)
        self.assertEqual({item["promotion_basis"]["input_id"] for item in _expanded(next_projection.payload)}, source_ids)
        self.assertEqual(len(adapter.snapshot(THREAD_ID)["execution_authority_item_ids"]), 4)


class InteractiveProjectionCapacityTests(unittest.TestCase):
    def _app(self):
        app = InteractiveAppServer(
            codex=Path("unused"), codex_home=Path("unused"), workspace=Path("unused"),
            base_url="http://127.0.0.1:8002/v1", adapter=Mock(),
            events_path=Path("unused/events.jsonl"), stderr_path=Path("unused/stderr.log"),
            turn_timeout=10,
        )
        app.thread_id = THREAD_ID
        app.semantic_state = HarnessSemanticStateAdapter(max_projection_chars=800)
        app._request = Mock(return_value={"params": {"turn": {"status": "completed"}}})
        app._events_file = io.StringIO()
        app._semantic_snapshots_file = io.StringIO()
        app._promotion_audit_file = io.StringIO()
        app._trajectory_writer = Mock()
        app.process = Mock()
        return app

    def test_capacity_failure_is_local_and_same_thread_can_continue(self):
        app = self._app()
        prior = app.semantic_state.prepare_turn(THREAD_ID, "AI agent research", turn_id="prior")
        app._last_turn_context = turn_context_payload([], semantic_projection=prior.payload)
        original_process = app.process
        output = io.StringIO()
        with redirect_stdout(output):
            app.run_turn(MULTI_CONSTRAINT_INPUT)
        app._request.assert_not_called()
        app.process.terminate.assert_not_called()
        self.assertIs(app.process, original_process)
        self.assertEqual(app._last_turn_context, {})
        self.assertEqual(app._promotion_audit_file.getvalue(), "")
        self.assertEqual(app._events_file.getvalue(), "")
        app._trajectory_writer.write_raw_event.assert_not_called()
        row = json.loads(app._semantic_snapshots_file.getvalue())
        self.assertEqual(row["event"], "PRE_TURN_REJECTED")
        self.assertEqual(row["turn_id"], "")
        self.assertFalse(row["projection_failure"]["app_server_requested"])
        self.assertEqual(row["snapshot"]["constraints"], EXPECTED_CONSTRAINTS)
        self.assertEqual(row["snapshot"]["last_projection"], prior.payload)
        self.assertEqual(row["input_id"], row["snapshot"]["current_input_id"])
        self.assertEqual(row["snapshot"]["completed_turn_count"], 0)
        self.assertIn("session remains open", output.getvalue())
        with redirect_stdout(io.StringIO()):
            app.run_turn("继续研究")
        app._request.assert_not_called()
        self.assertEqual(app.semantic_state.snapshot(THREAD_ID)["constraints"], EXPECTED_CONSTRAINTS)
        with redirect_stdout(io.StringIO()):
            app.run_turn("取消搜索限制，继续讨论 AI agent")
        app._request.assert_called_once()
        sent = app._request.call_args.args[0]
        self.assertEqual(sent["params"]["threadId"], THREAD_ID)
        self.assertEqual(json.loads(sent["params"]["additionalContext"]["uaea.semantic_state_projection"]["value"])["constraints"], [])
        self.assertTrue(all(any(item["metadata"]["value"] == value
                                for item in app.semantic_state.snapshot(THREAD_ID)["semantic_items"])
                            for value in EXPECTED_CONSTRAINTS))

    def test_unrelated_prepare_error_is_not_swallowed(self):
        app = self._app()
        app.semantic_state.prepare_turn = Mock(side_effect=ValueError("unrelated failure"))
        with self.assertRaisesRegex(ValueError, "unrelated failure"):
            app.run_turn("ordinary input")
        app._request.assert_not_called()

    def test_capacity_diagnostic_flushes_and_log_failure_does_not_close_session(self):
        for log_failure in (False, True):
            with self.subTest(log_failure=log_failure):
                app = self._app()
                stream = Mock(wraps=io.StringIO())
                app._semantic_snapshots_file = stream
                if log_failure:
                    stream.write.side_effect = OSError("synthetic-secret")
                output = io.StringIO()
                with redirect_stdout(output):
                    app.run_turn(MULTI_CONSTRAINT_INPUT)
                self.assertNotIn("synthetic-secret", output.getvalue())
                if not log_failure:
                    stream.flush.assert_called_once()
                app._request.assert_not_called()
                app.process.terminate.assert_not_called()
                self.assertEqual(app.semantic_state.snapshot(THREAD_ID)["constraints"], EXPECTED_CONSTRAINTS)


if __name__ == "__main__":
    unittest.main()
