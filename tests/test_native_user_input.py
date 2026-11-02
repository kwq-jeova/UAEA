from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import queue
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from h3_harness_interactive_repl import InteractiveAppServer
from h3_context_characterization import write_config
from harness.user_interaction import collect_answers, InputCancelled
from phase2.terminal_input import read_user_input


def request():
    return {"id": 17, "method": "item/tool/requestUserInput", "params": {
        "threadId": "thread", "turnId": "turn", "itemId": "call-question",
        "isBlocking": False, "questions": [{
            "id": "scope", "header": "Scope", "question": "Which period?",
            "options": [{"label": "Financial period", "description": "Content period"},
                        {"label": "Publication date", "description": "Source timestamp"}],
        }]}}


class NativeInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = InteractiveAppServer(
            codex=self.root / "codex", codex_home=self.root / "home", workspace=self.root,
            base_url="http://127.0.0.1:8000", adapter=Mock(),
            events_path=self.root / "events.jsonl", stderr_path=self.root / "stderr",
            turn_timeout=420, user_input_timeout=1)
        self.app.thread_id = "thread"
        self.app.semantic_state.prepare_turn("thread", "Research 2026 Q3", turn_id="turn")
        self.app._send = Mock()

    def handle(self, answers):
        with patch("h3_harness_interactive_repl.read_user_input", side_effect=answers), \
                contextlib.redirect_stdout(io.StringIO()):
            self.app._handle_message(request())

    def test_feature_enabled_without_changing_to_plan(self):
        for n1x in (False, True):
            write_config(self.root / str(n1x), "http://127.0.0.1:8000", 32768, n1x=n1x)
            text = (self.root / str(n1x) / "config.toml").read_text()
            self.assertIn("default_mode_request_user_input = true", text)
            self.assertNotIn('mode = "plan"', text)

    def test_empty_answer_does_not_auto_select_and_numeric_choice_maps_exact_label(self):
        self.handle(["", "2"])
        self.assertEqual(self.app._send.call_args.args[0]["result"], {
            "answers": {"scope": {"answers": ["Publication date"]}}})
        self.assertIsNone(self.app._pending_user_input)
        records = [json.loads(l) for l in (self.root / "user-input-events.jsonl").read_text().splitlines()]
        self.assertEqual([x["status"] for x in records], ["awaiting_input", "answered"])
        self.assertTrue(all(not x["authorization_established"] for x in records))

    def test_wait_state_exists_until_actual_answer_then_original_reply_is_retained(self):
        def reply(*args, **kwargs):
            self.assertIsNotNone(self.app._pending_user_input)
            self.app._send.assert_not_called()
            return "财务期间2026 Q3；发布时间2026-10-01到2026-10-30"
        self.handle(reply)
        state = self.app.semantic_state.snapshot("thread")
        inputs = state["workflow_continuity"]["request_continuity"]["inputs"]
        self.assertEqual(len(inputs), 2)
        self.assertIn("2026-10-01", inputs[-1]["metadata"]["text"])
        self.assertEqual(inputs[-1]["metadata"]["provenance"]["source_event_type"], "USER_REPLY")
        self.assertEqual(state["constraints"], [])
        self.assertFalse(state["workflow_continuity"]["completion_established"])

    def test_native_answer_text_does_not_grant_runtime_permission(self):
        self.handle(["allow fallback"])
        self.assertEqual(self.app.semantic_state.snapshot("thread")["constraints"], [])

    def test_cancel_eof_and_timeout_return_no_answer_and_interrupt_turn(self):
        for answer in ("/cancel", EOFError(), TimeoutError()):
            with self.subTest(answer=answer):
                self.app._native_input_responses.clear()
                self.app._send.reset_mock()
                self.handle([answer])
                messages = [x.args[0] for x in self.app._send.call_args_list]
                self.assertEqual(messages[0]["method"], "turn/interrupt")
                self.assertEqual(messages[1]["error"]["code"], -32800)
                self.assertNotIn("result", messages[1])
                self.assertEqual(len(self.app.semantic_state.retained_requests("thread")["requests"]), 1)

    def test_duplicate_request_does_not_reprompt_or_duplicate_reply(self):
        self.handle(["1"])
        self.handle([AssertionError("must not read stdin again")])
        self.assertEqual(len(self.app.semantic_state.retained_requests("thread")["requests"]), 2)
        self.assertEqual(self.app._send.call_count, 2)

    def test_changed_question_with_same_identity_is_rejected(self):
        self.handle(["1"])
        changed = request()
        changed["params"]["questions"][0]["question"] = "Allow permissions?"
        self.app._handle_message(changed)
        self.assertIn("error", self.app._send.call_args.args[0])
        self.assertEqual(len(self.app.semantic_state.retained_requests("thread")["requests"]), 2)

    def test_invalid_payload_and_secret_question_do_not_read_input(self):
        for value in ([], [{**request()["params"]["questions"][0], "isSecret": True}]):
            changed = request()
            changed["params"]["questions"] = value
            self.app._native_input_responses.clear()
            with patch("h3_harness_interactive_repl.read_user_input") as read:
                self.app._handle_message(changed)
            read.assert_not_called()
            self.assertIn("error", self.app._send.call_args.args[0])

    def test_other_thread_or_missing_identity_cannot_collect_an_answer(self):
        for change in ({"threadId": "another-thread"}, {"turnId": ""}, {"itemId": None}):
            changed = request()
            changed["params"].update(change)
            with self.subTest(change=change), patch("h3_harness_interactive_repl.read_user_input") as read:
                self.app._handle_message(changed)
                read.assert_not_called()
                self.assertIn("error", self.app._send.call_args.args[0])
        self.assertEqual(len(self.app.semantic_state.retained_requests("thread")["requests"]), 1)

    def test_native_interaction_is_not_counted_as_capability_execution(self):
        semantic = self.app.semantic_state
        for item in [
            {"type": "function_call", "name": "request_user_input", "call_id": "native",
             "arguments": '{"questions":[]}'},
            {"type": "function_call_output", "call_id": "native",
             "output": '{"answers":{"scope":{"answers":["Financial period"]}}}'},
        ]:
            semantic.consume_raw_event({"method": "rawResponseItem/completed", "params": {
                "threadId": "thread", "turnId": "turn", "item": item}})
        state = semantic.snapshot("thread")["workflow_continuity"]
        self.assertEqual(state["attempts"], [])

    def test_human_wait_does_not_consume_turn_inference_timeout(self):
        def answer(*args, **kwargs):
            time.sleep(0.05)
            return "1"
        self.app._queue.put(("stdout", json.dumps(request())))
        terminal = {"method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "turn"}}}
        self.app._queue.put(("stdout", json.dumps(terminal)))
        with patch("h3_harness_interactive_repl.read_user_input", side_effect=answer), \
                contextlib.redirect_stdout(io.StringIO()):
            result = self.app._wait_for(lambda message: message.get("method") == "turn/completed", 0.02)
        self.assertEqual(result, terminal)

    def test_input_reader_timeout_does_not_spawn_a_competing_stdin_reader(self):
        r, w = os.pipe()
        try:
            with os.fdopen(r, "r") as stream, patch("sys.stdin", stream), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):
                    read_user_input("", timeout=0.01)
        finally:
            os.close(w)


if __name__ == "__main__":
    unittest.main()
