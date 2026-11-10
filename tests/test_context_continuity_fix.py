"""Targeted regressions: pending native Turns, terminal facts and saved-page segments."""
from contextlib import closing, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from harness.provider_history import project_provider_history
from harness.codex_dynamic_tools import HarnessToolDispatch
from phase2.web_adapter import WebAdapter
from phase2.web_capability import WebFetchCapability
from phase2.web_context import ProjectionLimits
from memory.sqlite_store import connect, counts, get_web_access_event
from runtime.action_request import ActionRequest
from runtime.semantic_observation import ExecutionObservation
from tests.test_contract_convergence import setup_host
from tests.test_harness_provider_history import call, output

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from h3_harness_interactive_repl import InteractiveAppServer, build_interactive_adapter


class PendingTurnTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        adapter, semantic, _ = setup_host(self.root / "workspace")
        self.app = InteractiveAppServer(
            codex=self.root/"unused", codex_home=self.root/"home", workspace=self.root/"workspace",
            base_url="http://127.0.0.1:8003", adapter=adapter,
            events_path=self.root/"raw.jsonl", stderr_path=self.root/"stderr", turn_timeout=.01)
        self.app.thread_id = "t"
        self.app.semantic_state = semantic
        semantic.prepare_turn("t", "Read the source; do not claim completion.", turn_id="")
        self.original_input = semantic.snapshot("t")["current_input_id"]
        self.sent = []
        self.app._send = self.sent.append
        self.log = self.app.events_path.open("w")
        self.app._events_file = self.log
        self.addCleanup(self.log.close)

    def queue(self, message):
        self.app._queue.put(("stdout", json.dumps(message)))

    def start_pending(self, ack=True):
        if ack:
            self.queue({"id":99,"result":{"turn":{"id":"active","status":"inProgress"}}})
        self.assertIsNone(self.app._request_turn(
            {"id":99,"method":"turn/start","params":{"threadId":"t"}}, timeout=.01))

    def terminal(self, turn="active", status="completed"):
        return {"method":"turn/completed","params":{"threadId":"t","turn":{"id":turn,"status":status,"items":[]}}}

    def test_new_text_is_blocked_before_semantic_mutation(self):
        self.start_pending()
        before = self.app.semantic_state.snapshot("t")
        with redirect_stdout(io.StringIO()) as printed:
            self.app.run_turn("A different request must not attach to the old turn.")
        self.assertIn("Input not sent or retained", printed.getvalue())
        self.assertEqual(self.app.semantic_state.snapshot("t"), before)
        self.assertEqual(len(self.sent), 1)

    def test_wait_finishes_original_turn_without_sending_another_start(self):
        self.start_pending()
        self.queue(self.terminal("foreign"))
        self.queue(self.terminal())
        with redirect_stdout(io.StringIO()):
            self.app.run_turn("/turn wait")
        self.assertIsNone(self.app._pending_turn)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.app.semantic_state.snapshot("t")["current_input_id"], self.original_input)
        self.assertEqual(self.app.semantic_state.snapshot("t")["completed_turn_count"], 1)

    def test_late_ack_and_matching_terminal_release_gate(self):
        self.start_pending(ack=False)
        self.queue({"id":99,"result":{"turn":{"id":"active"}}})
        self.queue(self.terminal())
        with redirect_stdout(io.StringIO()):
            self.app.run_turn("/turn wait")
        self.assertIsNone(self.app._pending_turn)

    def test_interrupt_ack_alone_does_not_release_gate(self):
        self.start_pending()
        with patch.object(self.app, "_wait_for", return_value=None), redirect_stdout(io.StringIO()):
            self.app.run_turn("/turn cancel")
        self.assertEqual(self.sent[-1]["method"], "turn/interrupt")
        self.assertEqual(self.sent[-1]["params"]["turnId"], "active")
        self.assertIsNotNone(self.app._pending_turn)
        self.assertEqual(self.app.semantic_state.snapshot("t")["completed_turn_count"], 0)

    def test_cancel_requires_observed_terminal(self):
        self.start_pending()
        def send(message):
            self.sent.append(message)
            if message.get("method") == "turn/interrupt":
                self.queue({"id":message["id"], "result":{}})
                self.queue(self.terminal(status="interrupted"))
        self.app._send = send
        with redirect_stdout(io.StringIO()):
            self.app.run_turn("/turn cancel")
        self.assertIsNone(self.app._pending_turn)
        self.assertFalse(self.app.semantic_state.snapshot("t")["workflow_continuity"]["completion_established"])

    def test_unknown_native_id_is_not_guessed_for_cancel(self):
        self.start_pending(ack=False)
        with patch.object(self.app, "_wait_for", return_value=None), redirect_stdout(io.StringIO()):
            self.app.run_turn("/turn cancel")
        self.assertEqual(len(self.sent), 1)
        self.assertIsNotNone(self.app._pending_turn)

    def test_late_goal_final_keeps_original_input_binding(self):
        self.start_pending()
        self.app.goals = Mock(mode="shadow")
        self.app.goals.observe_final.return_value = None
        completion = self.terminal()
        completion["params"]["turn"]["items"] = [{"type":"agentMessage","id":"final","text":"answer"}]
        self.queue(completion)
        with redirect_stdout(io.StringIO()):
            self.app.run_turn("/turn wait")
        self.assertEqual(self.app.goals.observe_final.call_args.kwargs["input_id"], self.original_input)
        self.assertEqual(self.app.goals.observe_final.call_args.kwargs["turn_id"], "active")


class TerminalFactTests(unittest.TestCase):
    def test_one_terminal_fact_preserves_both_raw_item_audits_and_authority(self):
        raw = {"input":[call(call_id="bad"), output({"ok":False,"data":{
            "execution_succeeded":False,"http_status":403,"reason":"http_error",
            "authorization":{"state":"unknown"}}},call_id="bad")]}
        frozen = deepcopy(raw)
        result = project_provider_history(raw)
        self.assertEqual(raw, frozen)
        self.assertEqual(len(result.request["input"]), 1)
        fact = json.loads(result.request["input"][0]["content"][0]["text"].split("\n",1)[1])
        self.assertEqual(fact["phase"], "outcome")
        self.assertEqual(fact["observation"]["authorization"]["state"], "unknown")
        self.assertEqual(len(result.decisions), 2)
        self.assertEqual({d["projection_effect"] for d in result.decisions},
                         {"terminal_fact","coalesced_terminal_reference"})
        self.assertEqual(project_provider_history(result.request).request,result.request)

    def test_distinct_call_ids_and_outcome_order_are_not_collapsed(self):
        raw={"input":[call(call_id="a"),call(call_id="b"),
                      {"role":"user","content":"keep position"},
                      output({"ok":False},call_id="a"),output({"ok":False},call_id="b")]}
        result=project_provider_history(raw)
        self.assertEqual(result.request["input"][0],raw["input"][2])
        self.assertEqual(len(result.request["input"]),3)
        self.assertEqual(len(result.decisions),4)


class SavedPageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.adapter = WebAdapter(snapshot_root=self.root/"snapshots")
        self.http = Mock(return_value={
            "body":("<html><title>Fixture</title><main><p>" +
                   "汉字 independent evidence, keep source identity. " * 180 +
                   "</p></main></html>").encode(), "content_type":"text/html", "status":200})
        self.adapter._http_get = self.http
        self.cap = WebFetchCapability(db_path=self.root/"source.sqlite", adapter=self.adapter,
            projection_limits=ProjectionLimits(max_sources=1,per_source_chars=900,total_chars=900))
        self.url="https://example.test/article"
        self.first = self.cap({"url":self.url},"fixture acquisition")
        self.source = self.first.data["source_excerpt"]

    def read(self, **kwargs):
        return self.cap({"url":self.url,"source_event_id":self.first.data["access_event_id"],**kwargs},"saved read")

    def visible(self, result, budget=5000):
        dispatch=HarnessToolDispatch("t","turn","c","web_fetch",
            ActionRequest("web.fetch",{"url":self.url},request_id="c"),result,
            ExecutionObservation.from_tool_result("web_fetch",result),max_output_chars=budget)
        wire=dispatch.to_app_server_response()["contentItems"][0]["text"]
        self.assertLessEqual(len(wire),budget)
        return json.loads(wire)

    def test_continuation_uses_exact_old_version_without_http_or_new_source(self):
        with closing(connect(self.root/"source.sqlite")) as c:
            before=counts(c)
        result=self.read(start_char=self.source["next_start_char"],max_chars=1500)
        ex=result.data["source_excerpt"]
        self.assertEqual(ex["start_char"],self.source["end_char"])
        self.assertEqual(ex["content_sha256"],self.source["content_sha256"])
        self.assertEqual(ex["extracted_text_sha256"],self.source["extracted_text_sha256"])
        self.assertEqual(ex["text_sha256"],hashlib.sha256(ex["text"].encode()).hexdigest())
        self.assertFalse(result.data["http_attempted"])
        self.assertIsNone(result.data["http_status"])
        self.assertEqual(result.data["acquisition_mode"],"retained_snapshot")
        self.http.assert_called_once()
        with closing(connect(self.root/"source.sqlite")) as c:
            self.assertEqual(counts(c),before)

    def test_cursors_follow_actual_supplied_fragment_under_output_budget(self):
        result=self.read(start_char=900,max_chars=3000)
        visible=self.visible(result)
        ex=visible["data"]["source_excerpt"]
        self.assertEqual(ex["end_char"],ex["start_char"]+len(ex["text"]))
        self.assertEqual(ex["next_start_char"],ex["end_char"])
        self.assertEqual(ex["text_sha256"],hashlib.sha256(ex["text"].encode()).hexdigest())
        self.assertLess(len(ex["text"]),3000)
        self.assertEqual(visible["data"]["acquisition_mode"],"retained_snapshot")
        following=self.read(start_char=ex["next_start_char"],max_chars=10).data["source_excerpt"]
        original=result.data["source_excerpt"]["text"]
        self.assertEqual(following["text"],original[len(ex["text"]):len(ex["text"])+10])

    def test_last_segment_and_eof_keep_unknown_full_page_completeness(self):
        total=self.source["extracted_text_chars"]
        last=self.read(start_char=total-12,max_chars=900).data["source_excerpt"]
        self.assertFalse(last["has_more"])
        self.assertIsNone(last["next_start_char"])
        self.assertEqual(last["end_char"],total)
        self.assertEqual(last["scope"],"extracted_snapshot_segment_not_full_page")
        eof=self.read(start_char=total).data["source_excerpt"]
        self.assertEqual(eof["text"],"")

    def test_invalid_cursor_and_budget_rejected_without_http(self):
        for args in [{"start_char":-1},{"start_char":True},{"start_char":"900"},
                     {"max_chars":0},{"max_chars":3001},{"max_chars":float("nan")},
                     {"start_char":self.source["extracted_text_chars"]+1}]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.read(**args)
        self.http.assert_called_once()

    def test_continuation_without_source_cannot_implicitly_refetch(self):
        with self.assertRaises(ValueError):
            self.cap({"url":self.url,"start_char":900},"bad")
        self.http.assert_called_once()

    def test_url_mismatch_or_unknown_source_cannot_read_another_artifact(self):
        for args in [{"url":"https://example.test/other","source_event_id":self.source["source_event_id"]},
                     {"url":self.url,"source_event_id":"missing"}]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.cap(args,"bad")
        self.http.assert_called_once()

    def test_changed_snapshot_is_rejected_not_refetched_or_rehashed(self):
        path=Path(self.first.data["content_ref"])
        path.write_text("changed")
        with self.assertRaisesRegex(ValueError,"hash changed"):
            self.read(start_char=1)
        self.http.assert_called_once()

    def test_snapshot_changed_during_extraction_cannot_fall_back_to_old_excerpt(self):
        from phase2.web_context import project_web_access_events
        path=Path(self.first.data["content_ref"])
        path.write_text("changed during extraction")
        with closing(connect(self.root/"source.sqlite")) as c:
            with self.assertRaisesRegex(ValueError,"hash changed"):
                project_web_access_events(c,[self.source["source_event_id"]],require_snapshot=True)
        path.unlink()
        with closing(connect(self.root/"source.sqlite")) as c:
            with self.assertRaisesRegex(ValueError,"missing"):
                project_web_access_events(c,[self.source["source_event_id"]],require_snapshot=True)

    def test_snapshot_outside_adapter_root_is_not_exposed(self):
        self.adapter.snapshot_root=self.root/"another-root"
        with self.assertRaisesRegex(ValueError,"outside snapshot root"):
            self.read()
        self.http.assert_called_once()

    def test_transport_and_page_content_are_not_merged(self):
        self.http.return_value["body"]=b"<html><title>Client Challenge</title><p>Client Challenge</p></html>"
        result=self.cap({"url":"https://example.test/challenge"},"fixture")
        self.assertTrue(result.data["execution_succeeded"])
        self.assertFalse(result.data["source_excerpt"]["has_more"])
        self.assertIn("Client Challenge",result.data["source_excerpt"]["text"])
        self.assertEqual(result.data["source_excerpt"]["scope"],"extracted_snapshot_segment_not_full_page")

    def test_shared_reads_keep_source_identity_without_goal_or_duplicate_recovery(self):
        from harness.execution_host import SharedExecutionHost
        from harness.semantic_state_adapter import HarnessSemanticStateAdapter
        from harness.codex_dynamic_tools import DynamicToolBinding, HarnessDynamicToolAdapter
        from phase2.web_capability import web_fetch_metadata
        from runtime.tools import ToolRegistry
        from runtime.sandbox import Sandbox
        from runtime.ledger import LedgerStub
        registry=ToolRegistry(Sandbox(self.root,self.root),LedgerStub(self.root/"traces"))
        registry.register_capability(web_fetch_metadata(),self.cap)
        binding=DynamicToolBinding.from_registry(registry,"web.fetch",description="Read saved segment",
            input_schema={"type":"object","properties":{"url":{"type":"string"},"source_event_id":{"type":"string"},
                          "start_char":{"type":"integer"}},"required":["url"]})
        semantic=HarnessSemanticStateAdapter(require_registered_input=True)
        semantic.prepare_turn("shared","Continue the saved source, not a new acquisition.",turn_id="one")
        adapter=HarnessDynamicToolAdapter(registry,[binding],max_output_chars=5000,
            execution_boundary=SharedExecutionHost(registry,semantic,self.root/"contract.jsonl"))
        adapter.bind_semantic_state_adapter(semantic)
        for cid in ("read-a","read-b"):
            dispatch=adapter.dispatch({"threadId":"shared","turnId":"one","callId":cid,"tool":"web_fetch",
                "arguments":{"url":self.url,"source_event_id":self.source["source_event_id"],"start_char":900}})
            self.assertTrue(dispatch.ok)
            self.assertTrue(dispatch.execution_decision["allowed"])
            self.assertFalse(dispatch.tool_result.data["http_attempted"])
        sources=semantic.recovery_sources("shared")
        self.assertEqual(len(sources),1)
        self.assertEqual(sources[0]["start_char"],900)
        self.assertEqual(sources[0]["end_char"],1200)
        self.assertEqual(sources[0]["next_start_char"],1200)
        self.assertEqual(sources[0]["text_sha256"],hashlib.sha256(sources[0]["text"].encode()).hexdigest())
        snap=semantic.snapshot("shared")
        self.assertIsNone(snap["phase1_runtime_snapshot"]["active_goal"])
        self.assertFalse(snap["workflow_continuity"]["completion_established"])
        self.http.assert_called_once()

    def test_unified_entry_exposes_optional_cursor_and_keeps_default_budget(self):
        adapter=build_interactive_adapter(self.root/"entry")
        specs=adapter.dynamic_tools()
        spec=next(x for x in specs if x["name"]=="web_fetch")
        schema=spec["inputSchema"]
        self.assertEqual(schema["required"],["url"])
        self.assertIn("source_event_id",schema["properties"])
        self.assertEqual(schema["properties"]["max_chars"]["maximum"],3000)
