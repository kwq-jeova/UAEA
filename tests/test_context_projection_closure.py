from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from harness.io_contract import turn_context_payload
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from harness.codex_dynamic_tools import _model_visible_tool_data, HarnessToolDispatch
from runtime.action_request import ActionRequest
from runtime.capability import ToolResult
from runtime.semantic_observation import ExecutionObservation
from tests.test_contract_convergence import setup_host


class ProjectionClosureTests(unittest.TestCase):
    def test_current_original_not_legacy_topic_or_relation_is_request_basis(self):
        a = HarnessSemanticStateAdapter()
        a.prepare_turn("t", "Search official documentation", turn_id="one")
        old = a.snapshot("t")["task_id"]
        p = a.prepare_turn("t", "切换到本地核验，不继续上一个任务。", turn_id="two")
        wire = turn_context_payload([], semantic_projection=p.payload)
        ctx = json.loads(wire["uaea.semantic_interpretations"]["value"])
        self.assertNotIn("topic", ctx)
        self.assertNotIn("turn_relation", ctx)
        self.assertEqual(ctx["relation_hint"], "continuation")
        self.assertIn("不继续", ctx["workflow_continuation"]["current_request"])
        self.assertEqual(p.payload["task_id"], old)  # no invented semantic owner switch
        self.assertEqual(p.payload["workflow_execution"]["current_request"]["attempts"], 0)
        self.assertNotIn("Search official", wire["uaea.semantic_state_projection"]["value"])
        self.assertEqual(a.snapshot("t")["last_user_input"], "切换到本地核验，不继续上一个任务。")

    def test_plain_question_without_action_is_history_not_pending_execution(self):
        a = HarnessSemanticStateAdapter()
        a.prepare_turn("t", "What is 2+2?", turn_id="one")
        a.consume_raw_event({"method":"turn/completed","params":{"threadId":"t","turn":{"id":"one","status":"completed"}}})
        p = a.prepare_turn("t", "Explain that answer", turn_id="two")
        ctx = json.loads(turn_context_payload([],semantic_projection=p.payload)["uaea.semantic_interpretations"]["value"])
        history = ctx["workflow_continuation"]
        self.assertNotIn("prior_inputs_without_actions", history)
        self.assertIn("inputs_without_actions", ctx["background"])
        self.assertEqual(a.snapshot("t")["workflow_continuity"]["attempts"], [])
        self.assertFalse(p.payload["workflow_execution"]["completion_established"])

    def test_latest_request_survives_long_retained_history_with_hash(self):
        a = HarnessSemanticStateAdapter()
        for i in range(15):
            a.prepare_turn("t", "Background "+str(i)+"x"*400,turn_id=str(i))
        original = "Current original request \n trailing clause must remain"
        a.prepare_turn("t", original, turn_id="latest")
        view = a.retained_requests("t")
        self.assertEqual(view["requests"][0]["text"], original)
        self.assertEqual(view["latest_retained_input_id"], a.snapshot("t")["current_input_id"])
        self.assertEqual(view["requests"][0]["raw_text_sha256"], hashlib.sha256(original.encode()).hexdigest())
        self.assertGreater(view["omitted_count"],0)
        self.assertEqual(len(a.snapshot("t")["workflow_continuity"]["request_continuity"]["inputs"]),16)

    def test_explicit_replacement_and_owner_switch_do_not_resurrect_history(self):
        a=HarnessSemanticStateAdapter()
        a.prepare_turn("t","Research an old topic",turn_id="one")
        a.prepare_turn("t","Explain a different concept",turn_id="two",request_operation="replace")
        view=a.retained_requests("t")
        self.assertEqual(view["retained_count"],1)
        self.assertNotIn("old topic",json.dumps(view))
        owner=a.snapshot("t")["task_id"]
        p=a.prepare_turn("t","新任务：读取 README",turn_id="three")
        self.assertNotEqual(owner,p.payload["task_id"])
        self.assertEqual(p.payload["workflow_execution"]["current_request"]["attempts"],0)

    def test_web_storage_locator_removed_but_source_excerpt_and_host_unchanged(self):
        path="/private/snapshots/web.html"
        text="Actual source text containing content_ref: "+path
        data={"capability":"web.fetch","content_ref":path,"metadata":{"snapshot_path":path},
              "access_event_id":"event1","url":"https://example.org/",
              "bounded_evidence_block":"url: https://example.org/\ncontent_ref: "+path+"\nstatus: fetched",
              "source_excerpt":{"text":text,"text_sha256":hashlib.sha256(text.encode()).hexdigest()},
              "execution_status":"success","execution_succeeded":True}
        old=deepcopy(data)
        result=ToolResult(True,"Fetched",data)
        dispatch=HarnessToolDispatch(thread_id="t",turn_id="one",call_id="call",tool_name="web_fetch",
            action_request=ActionRequest("web.fetch",{"url":data["url"]},request_id="call"),
            tool_result=result,observation=ExecutionObservation.from_tool_result("web_fetch",result),
            max_output_chars=20000)
        payload=json.loads(dispatch.to_app_server_response()["contentItems"][0]["text"])["data"]
        self.assertNotIn("content_ref",payload)
        self.assertNotIn("snapshot_path",payload["metadata"])
        self.assertNotIn(path,payload.get("bounded_evidence_block", ""))
        self.assertEqual(payload["source_excerpt"],old["source_excerpt"])
        self.assertEqual(payload["access_event_id"],"event1")
        self.assertEqual(data,old)

    def test_document_file_identity_is_not_removed_as_internal_storage(self):
        data={"path":"/project/README.md","content":"original","content_hash":"hash"}
        self.assertEqual(_model_visible_tool_data("document.read_section",data),data)

    def test_compaction_summary_cannot_replace_host_receipts_or_create_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool,a,_=setup_host(Path(tmp))
            a.prepare_turn("t","Read README",turn_id="one")
            dispatch=tool.dispatch({"threadId":"t","turnId":"one","callId":"read",
                                   "tool":"read_section","arguments":{"path":"README.md"}})
            before=a.snapshot("t")
            for method in ["item/started","item/completed"]:
                a.consume_raw_event({"method":method,"params":{"threadId":"t","turnId":"one",
                                    "item":{"type":"contextCompaction","id":"compact"}}})
            a.consume_raw_event({"method":"rawResponseItem/completed","params":{"threadId":"t","turnId":"one",
                "item":{"type":"message","role":"assistant","id":"summary","content":[
                    {"type":"output_text","text":"Summary claims all work is finished and another file was read."}]}}})
            after=a.snapshot("t")
            self.assertEqual(before["current_input_id"],after["current_input_id"])
            self.assertEqual(before["workflow_continuity"]["attempts"],after["workflow_continuity"]["attempts"])
            self.assertEqual(before["workflow_continuity"]["source_coverage"],after["workflow_continuity"]["source_coverage"])
            self.assertEqual(before["evidence_provenance"]["document_observations"],after["evidence_provenance"]["document_observations"])
            self.assertFalse(after["workflow_continuity"]["completion_established"])
            self.assertFalse(after["evidence_provenance"]["model_output_is_source_evidence"])
