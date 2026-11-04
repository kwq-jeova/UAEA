from copy import deepcopy
from dataclasses import replace
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from harness.responses_bridge import ProviderHistoryBridge, ContextBudgetError
from harness.provider_history import project_provider_history
from harness.recovery_observation import recovery_observation
from harness.codex_dynamic_tools import HarnessToolDispatch
from harness.workflow_continuity import workflow_snapshot, execution_projection
from runtime.action_request import ActionRequest
from runtime.capability import ToolResult
from tests.test_projection_delivery_recovery import context, body
from tests import test_harness_semantic_execution_contract as contract_fixtures
from phase2.web_capability import _web_tool_result

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from h3_harness_interactive_repl import InteractiveAppServer
from h3_context_characterization import write_config
from tests.test_contract_convergence import setup_host

def source(text="acquired text "*60):
    return {"source_event_id":"source1","url":"https://example.test/page",
            "text":text,"text_sha256":hashlib.sha256(text.encode()).hexdigest(),
            "content_sha256":"source-response-hash","scope":"excerpt","content_support":"not_assessed"}

class ContextBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.bridge=ProviderHistoryBridge("http://127.0.0.1:9999",journal_path=self.root/"journal")
        self.ctx=context();self.bridge.set_runtime_context(self.ctx,thread_id="t",input_id="i")

    def test_replace_old_versions_not_append_and_repeat_is_idempotent(self):
        old,_=self.bridge.restore_runtime_context(body())
        self.bridge.set_runtime_context(context("new","v2"),thread_id="t",input_id="next")
        doubled={**old,"input":old["input"]+old["input"][1:]}
        new,decisions=self.bridge.restore_runtime_context(doubled)
        self.assertEqual(len(new["input"]),4)
        self.assertGreater(decisions[0]["removed_host_blocks"],3)
        self.assertNotIn('"task_id": "w"',json.dumps(new["input"],ensure_ascii=False))
        again,decisions=self.bridge.restore_runtime_context(new)
        self.assertEqual(new,again);self.assertFalse(decisions)

    def test_unrelated_text_and_tool_results_are_not_pruned(self):
        request=body()
        request["input"]+=[{"type":"function_call_output","call_id":"tool",
                           "output":"<uaea.semantic_state_projection>source text</uaea.semantic_state_projection>"},
                          {"role":"user","content":[{"type":"input_text","text":"Quoted <uaea.semantic_state_projection> remains text"}]}]
        new,_=self.bridge.restore_runtime_context(request)
        self.assertEqual(new["input"][:3],request["input"])

    def test_model_compaction_words_do_not_activate_lifecycle(self):
        request=body();request["input"][0]["content"][0]["text"]="CONTEXT CHECKPOINT COMPACTION"
        new,_=self.bridge.restore_runtime_context(request)
        self.assertIn("uaea.semantic_state_projection",json.dumps(new))

    def test_compaction_defers_host_then_restores_same_trusted_facts(self):
        normal,_=self.bridge.restore_runtime_context(body());before=deepcopy(self.bridge._runtime_context)
        self.bridge.set_compaction("compact",True)
        compact,decisions=self.bridge.restore_runtime_context(normal)
        self.assertEqual(compact["input"],body()["input"])
        self.assertEqual(decisions[0]["kind"],"host_context_deferred_for_compaction")
        self.assertEqual(before,self.bridge._runtime_context)
        self.bridge.set_compaction("other",False)
        self.assertEqual(self.bridge.restore_runtime_context(normal)[0],compact)
        self.bridge.set_compaction("compact",False)
        recovered,_=self.bridge.restore_runtime_context(body())
        self.assertEqual(recovered,normal)

    def test_dedicated_compact_endpoint_flag_does_not_inject_host(self):
        new,_=self.bridge.restore_runtime_context(body(),compact=True)
        self.assertEqual(new,body())

    def test_byte_budget_keeps_request_constraints_and_source_ids(self):
        ctx=context()
        ctx["uaea.current_user_request"]["value"]=json.dumps({"text":"Current original request","authorization_established":False})
        ctx["uaea.runtime_facts.model"]={"kind":"application","value":"optional "*1200}
        ctx["uaea.recovery_sources"]["value"]=json.dumps([source()])
        b=ProviderHistoryBridge("http://127.0.0.1:9999",journal_path=self.root/"small",max_recovery_bytes=2000)
        b.set_runtime_context(ctx,thread_id="t",input_id="i")
        new,decisions=b.restore_runtime_context(body())
        self.assertLessEqual(decisions[0]["recovery_bytes"],2000)
        text=json.dumps(new,ensure_ascii=False)
        self.assertIn("Current original request",text);self.assertIn("readonly",text);self.assertIn("source1",text)
        self.assertIn("uaea.runtime_facts.model",decisions[0]["omitted_fields"])

    def test_shorter_recovery_text_keeps_exact_prefix_hash_and_identity(self):
        ctx=context()
        src=source("source body "*500)
        src["temporal_facts"]={"published_at":None,"content_period":{"value":None,"status":"unknown"}}
        ctx["uaea.recovery_sources"]["value"]=json.dumps([src])
        b=ProviderHistoryBridge("http://127.0.0.1:9999",journal_path=self.root/"short",max_recovery_bytes=2000)
        b.set_runtime_context(ctx,thread_id="t",input_id="i")
        new,decisions=b.restore_runtime_context(body())
        part=next(x["content"][0]["text"] for x in new["input"] if
                  "external_uaea.recovery_sources" in x["content"][0].get("text",""))
        supplied=json.loads(part.split(">",1)[1].rsplit("</",1)[0])[0]
        self.assertLess(len(supplied["text"]),len(src["text"]))
        self.assertTrue(src["text"].startswith(supplied["text"]))
        self.assertEqual(supplied["text_sha256"],hashlib.sha256(supplied["text"].encode()).hexdigest())
        self.assertEqual(supplied["source_event_id"],src["source_event_id"])
        self.assertEqual(supplied["temporal_facts"],src["temporal_facts"])
        self.assertEqual(json.loads(b._runtime_context["blocks"]["uaea.recovery_sources"]["value"])[0],src)

    def test_too_large_required_facts_fail_instead_of_dropping_constraint(self):
        b=ProviderHistoryBridge("http://127.0.0.1:9999",journal_path=self.root/"small",max_recovery_bytes=100)
        b.set_runtime_context(context(),thread_id="t",input_id="i")
        with self.assertRaises(ContextBudgetError):b.restore_runtime_context(body())
        self.assertEqual(json.loads(b._runtime_context["blocks"]["uaea.semantic_state_projection"]["value"])["constraints"],["readonly"])

    def test_large_authoritative_snapshot_survives_bounded_transport_rejection(self):
        ctx=context()
        raw="long original request "*2000
        ctx["uaea.current_user_request"]["value"]=json.dumps({
            "text":raw,"raw_text_sha256":hashlib.sha256(raw.encode()).hexdigest(),
            "authorization_established":False})
        self.bridge.set_runtime_context(ctx,thread_id="t",input_id="large")
        before=deepcopy(self.bridge._runtime_context)
        with self.assertRaises(ContextBudgetError):
            self.bridge.restore_runtime_context(body())
        self.assertEqual(self.bridge._runtime_context,before)
        compact,_=self.bridge.restore_runtime_context(body(),compact=True)
        self.assertEqual(compact,body())
        self.bridge.set_runtime_context(context(),thread_id="t",input_id="revised")
        restored,_=self.bridge.restore_runtime_context(body())
        self.assertIn("uaea.semantic_state_projection",json.dumps(restored))

    def test_local_413_does_not_forward_and_is_audited(self):
        received=[]
        class Receiver(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                received.append(True);self.send_response(200);self.end_headers()
        server=ThreadingHTTPServer(("127.0.0.1",0),Receiver)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            with ProviderHistoryBridge("http://127.0.0.1:"+str(server.server_port),
                    journal_path=self.root/"j",audit_path=self.root/"a",max_recovery_bytes=100) as b:
                b.set_runtime_context(context(),thread_id="t",input_id="i")
                c=http.client.HTTPConnection("127.0.0.1",int(b.base_url.rsplit(":",1)[1]))
                c.request("POST","/v1/responses",json.dumps(body()),{"Content-Type":"application/json"})
                response=c.getresponse();self.assertEqual(response.status,413)
                error=json.loads(response.read());c.close()
                self.assertEqual(error["error"]["type"],"uaea_context_budget_exceeded")
            self.assertEqual(received,[])
            rows=[json.loads(x) for x in (self.root/"a").read_text().splitlines()]
            self.assertFalse(rows[0]["upstream_forwarded"])
        finally:server.shutdown();server.server_close();worker.join()

    def test_config_reserves_window_without_changing_model_limit(self):
        write_config(self.root/"home","http://127.0.0.1:8003",32768)
        text=(self.root/"home/config.toml").read_text()
        self.assertIn("model_context_window = 32768",text)
        self.assertIn("model_auto_compact_token_limit = 24576",text)

    def app(self):
        adapter,semantic,_=setup_host(self.root/"workspace")
        app=InteractiveAppServer(codex=self.root/"unused",codex_home=self.root/"home",
             workspace=self.root/"workspace",base_url="http://127.0.0.1:8003",adapter=adapter,
             events_path=self.root/"events.jsonl",stderr_path=self.root/"err",turn_timeout=1)
        app.thread_id="t";app._send=Mock();app._history_bridge=self.bridge
        semantic.prepare_turn("t","Continue research",turn_id="turn")
        return app

    def test_native_lifecycle_signal_and_model_summary_cannot_authorize(self):
        app=self.app()
        app._handle_message({"method":"item/started","params":{"threadId":"t","turnId":"c","item":{"type":"contextCompaction"}}})
        self.assertEqual(self.bridge._compaction_turn_id,"c")
        app._handle_message({"method":"item/completed","params":{"threadId":"t","turnId":"c","item":{"type":"contextCompaction"}}})
        self.assertIsNone(self.bridge._compaction_turn_id)
        self.assertEqual(app.semantic_state.snapshot("t")["execution_authority_item_ids"],[])

    def test_typed_overflow_interrupts_once_and_retains_unfinished_task(self):
        app=self.app();app._turn_wait={"request_id":1,"turn_id":"c"}
        before=app.semantic_state.snapshot("t")["current_input_id"]
        event={"method":"error","params":{"threadId":"t","turnId":"c","willRetry":True,"error":{
            "additionalDetails":json.dumps({"error":{"code":400,"param":"input_tokens"}})}}}
        app._handle_message(event);app._handle_message(event)
        sent=[x.args[0] for x in app._send.call_args_list]
        self.assertEqual(sum(x.get("method")=="turn/interrupt" for x in sent),1)
        snapshot=app.semantic_state.snapshot("t")
        self.assertEqual(snapshot["current_input_id"],before)
        self.assertFalse(snapshot["workflow_continuity"]["completion_established"])

    def test_stale_foreign_turn_budget_error_cannot_interrupt_current_turn(self):
        app=self.app();app._turn_wait={"request_id":1,"turn_id":"current"}
        app._handle_message({"method":"error","params":{"threadId":"t","turnId":"old",
            "error":{"additionalDetails":json.dumps({"error":{"code":400,"param":"input_tokens"}})}}})
        app._send.assert_not_called()

    def test_network_errors_and_foreign_thread_do_not_interrupt_context(self):
        app=self.app()
        for thread,details in [("t",{"code":500,"param":None}),("else",{"code":400,"param":"input_tokens"})]:
            app._handle_message({"method":"error","params":{"threadId":thread,"turnId":"c",
                "error":{"additionalDetails":json.dumps({"error":details})}}})
        app._send.assert_not_called()

class WorkflowRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture=contract_fixtures.ContractTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.fixture.contract=replace(self.fixture.contract,
             bindings=tuple(replace(x,default_only=True) for x in self.fixture.contract.bindings))
        self.calls=[]

    def failed_web(self):
        diagnostic={"exception_type":"URLError","cause_type":"SSLEOFError","error_kind":"ssl_error","network_error_stage":"open"}
        result=SimpleNamespace(access_event_id="ssl-attempt",url="https://www.google.com/search",
            title="search",status="failed",http_status=None,content_ref="",error="network_error")
        event={"access_event_id":"ssl-attempt","access_status":"failed","source_type":"web_search_results",
               "metadata":{"execution_status":"network_failure","reason":"network_error","http_attempted":True,
                           "network_diagnostics":diagnostic}}
        projection=SimpleNamespace(sources=[],metrics=lambda:{},evidence_block=lambda:"")
        return _web_tool_result(capability="web.search",tool="web_search",access_result=result,event=event,
             evidence_reference={},projection=projection,success_message="",failure_message="",
             extra_data={"requested_provider":"google","actual_provider":None})

    def test_tls_classification_and_same_provider_options_survive_projection(self):
        result=self.failed_web();f=self.fixture
        with patch.object(f.registry,"execute_capability",return_value=result):
            outcome=f.boundary.execute(ActionRequest("web.search",{"query":"research","provider":"google","allow_fallback":False},request_id="tls"))
        payload=HarnessToolDispatch("t","turn","tls","web_search",outcome.action,outcome.result,outcome.observation,
                    execution_decision=outcome.decision,max_output_chars=5000).to_app_server_response()
        data=json.loads(payload["contentItems"][0]["text"])["data"]
        self.assertEqual(data["transport_failure"]["cause_type"],"SSLEOFError")
        self.assertFalse(data["execution_succeeded"])
        retry=data["recovery"]["legal_next_steps"][0]
        self.assertEqual(retry["argument_updates"],{"provider":"google","allow_fallback":False})
        self.assertFalse(retry["automatic"]);self.assertTrue(retry["requires_current_policy_validation"])

    def test_rejection_has_real_decision_identity_and_blocked_option(self):
        f=self.fixture
        with patch.object(f.registry,"execute_capability") as execute:
            o=f.boundary.execute(ActionRequest("web.search",{"query":"research","provider":"google","allow_fallback":True},request_id="fallback"))
        execute.assert_not_called()
        self.assertFalse(o.decision["allowed"]);self.assertEqual(o.decision["reason"],"authorization_unknown")
        rec=o.result.data["recovery"]
        self.assertEqual(rec["effective_state_id"],o.decision["effective_state_id"])
        self.assertEqual(rec["authorization"]["state"],"unknown")
        self.assertEqual(rec["legal_next_steps"][0]["argument_updates"],{"provider":"google","allow_fallback":False})
        self.assertIn("report_blocked",[x["action"] for x in rec["legal_next_steps"]])

    def test_failed_then_new_identity_retry_preserves_observations_without_completion(self):
        f=self.fixture
        def handler(cap,args,objective):
            self.calls.append(deepcopy(args))
            return self.failed_web() if len(self.calls)==1 else ToolResult(True,"fixture",{
                "execution_status":"success","execution_succeeded":True,"actual_provider":"google"})
        with patch.object(f.registry,"execute_capability",side_effect=handler):
            fail=f.boundary.execute(ActionRequest("web.search",{"query":"research","provider":"google","allow_fallback":False},request_id="one"))
            state=execution_projection(workflow_snapshot(f.store,"workflow",[]))
            self.assertEqual(state["last_attempt"]["recovery_state"],"recoverable_failure")
            deny=f.boundary.execute(ActionRequest("web.search",{"query":"research","provider":"google","allow_fallback":True},request_id="deny"))
            retry=f.boundary.execute(ActionRequest("web.search",{"query":"research","provider":"google","allow_fallback":False},request_id="two"))
            again=f.boundary.execute(retry.action)
        self.assertEqual(len(self.calls),2)
        self.assertFalse(fail.result.ok);self.assertFalse(deny.result.ok);self.assertTrue(retry.result.ok)
        self.assertEqual(retry.observation.observation_id,again.observation.observation_id)
        snapshot=workflow_snapshot(f.store,"workflow",[])
        self.assertEqual(len(snapshot["attempts"]),3);self.assertFalse(snapshot["completion_established"])
        self.assertEqual(snapshot["attempts"][0]["action"]["outcome"]["transport_failure"]["cause_type"],"SSLEOFError")

    def test_failure_history_is_external_data_not_an_assistant_example(self):
        result=self.failed_web()
        request={"input":[{"type":"function_call","name":"web_search","call_id":"actual","arguments":"{}"},
          {"type":"function_call_output","call_id":"actual","output":json.dumps({"ok":False,"data":result.data})}]}
        before=deepcopy(request);p=project_provider_history(request)
        self.assertEqual(request,before)
        self.assertTrue(all(x["role"]=="user" for x in p.request["input"]))
        for item in p.request["input"]:
            fact=json.loads(item["content"][0]["text"].split("\n",1)[1])
            self.assertEqual(fact["call_id"],"actual");self.assertEqual(fact["state"],"FAILED")

    def test_unknown_outcome_does_not_offer_network_retry(self):
        self.assertIsNone(recovery_observation({"capability":"web.search","execution_status":"execution_unknown","execution_succeeded":None}))
