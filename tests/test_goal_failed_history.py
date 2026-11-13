"""Goal failed-proposal history: CPU only, no cognitive/model pass claims."""
import copy
import http.client
import tempfile
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from harness.responses_bridge import ProviderHistoryBridge
import json
import unittest
from harness.provider_history import project_provider_history, HistoryProjectionBudgetError, HistoryProjectionBindingError

def call(cid, target="goal:A", text="submitted A", operation="revise"):
    return {"type":"function_call","call_id":cid,"name":"goal_hypothesis",
            "arguments":json.dumps({"operation":operation,"candidate_id":target,
                "hypothesis":text,"quote":"CURRENT correction","input_ids":["input:current"]})}

def output(cid, **receipt):
    return {"type":"function_call_output","call_id":cid,
            "output":json.dumps({"kind":"goal_hypothesis_receipt",**receipt})}

def failed(cid, **kwargs):
    return output(cid, ok=False, committed=False, error="CURRENT required", **kwargs)

def facts(request):
    result=[]
    for field in ("input","previous_input_messages"):
        for i in request.get(field,[]):
            if isinstance(i,dict) and i.get("type")=="message":
                text=i["content"][0]["text"]
                if text.startswith("Historical runtime observation,"):
                    result.append(json.loads(text.split("\n",1)[1]))
    return result

class GoalFailedHistoryTests(unittest.TestCase):
    def test_success_form_unchanged(self):
        raw={"input":[call("form", text="old saved purpose",operation="form"),
                      output("form",ok=True,committed=True,candidate_id="goal:head")]}
        self.assertEqual(project_provider_history(raw).request, raw)

    def test_success_then_failed_revise_does_not_inherit_saved_body_or_commit(self):
        saved=call("form",text="old head",operation="form")
        raw={"input":[saved,output("form",ok=True,committed=True,candidate_id="goal:old"),
                      call("bad",target="goal:old",text="actual failed text"),failed("bad")]}
        original=copy.deepcopy(raw)
        p=project_provider_history(raw)
        self.assertEqual(raw, original)
        self.assertEqual(p.request["input"][:2],raw["input"][:2])
        f=facts(p.request)[0];a=f["goal_attempt"]
        self.assertEqual(f["call_id"],"bad")
        self.assertEqual(a["operation"],"revise")
        self.assertEqual(a["target_candidate_id"],"goal:old")
        self.assertEqual(a["submitted_arguments"],json.loads(raw["input"][2]["arguments"]))
        self.assertEqual(a["submitted_arguments"]["hypothesis"],"actual failed text")
        self.assertIs(a["host_result"]["accepted"],False)
        self.assertIs(a["host_result"]["committed"],False)
        self.assertEqual(a["host_result"]["saved_version_id"],"UNKNOWN")
        self.assertEqual(a["host_result"]["current_head"],"UNKNOWN")
        self.assertEqual(a["host_result"]["head_effect"],"not_committed_by_this_call")

    def test_multiple_failures_and_candidates_keep_order_and_binding(self):
        raw={"input":[call("a","goal:A","proposal A"),failed("a"),
                      call("b","goal:B","proposal B"),failed("b"),
                      call("c","goal:A","proposal C"),failed("c")]}
        fs=facts(project_provider_history(raw).request)
        self.assertEqual([f["call_id"] for f in fs],["a","b","c"])
        self.assertEqual([(f["goal_attempt"]["target_candidate_id"],
                          f["goal_attempt"]["submitted_arguments"]["hypothesis"]) for f in fs],
                         [("goal:A","proposal A"),("goal:B","proposal B"),("goal:A","proposal C")])

    def test_missing_committed_is_unknown(self):
        f=facts(project_provider_history({"input":[call("a"),output("a",ok=False,error="rejected")]}).request)[0]
        self.assertEqual(f["goal_attempt"]["host_result"]["committed"],"UNKNOWN")
        self.assertEqual(f["goal_attempt"]["host_result"]["head_effect"],"UNKNOWN")

    def test_missing_body_is_not_replaced_from_target(self):
        c=call("a");a=json.loads(c["arguments"]);del a["hypothesis"];c["arguments"]=json.dumps(a)
        f=facts(project_provider_history({"input":[c,failed("a")]}).request)[0]["goal_attempt"]
        self.assertEqual(f["proposal_text_visibility"],"missing")
        self.assertNotIn("hypothesis",f["submitted_arguments"])

    def test_inert_and_idempotent_reprojection(self):
        p=project_provider_history({"input":[call("a"),failed("a")]})
        self.assertTrue(all(x["type"]=="message" for x in p.request["input"]))
        f=facts(p.request)[0]
        self.assertFalse(f["replayable"])
        self.assertFalse(f["goal_attempt"]["is_saved_goal_version"])
        self.assertFalse(f["goal_attempt"]["authorizes_action"])
        self.assertEqual(project_provider_history(p.request).request,p.request)

    def test_budget_omits_whole_arguments_with_explicit_marker_not_partial_proposal(self):
        raw={"input":[call("a",text="中"*20000),failed("a")]}
        p=project_provider_history(raw,max_goal_history_bytes=3500)
        f=facts(p.request)[0]["goal_attempt"]
        self.assertIsNone(f["submitted_arguments"])
        self.assertEqual(f["arguments_visibility"],"omitted_budget")
        self.assertEqual(f["proposal_text_visibility"],"omitted_budget")
        self.assertEqual(f["target_candidate_id"],"goal:A")
        self.assertIs(f["host_result"]["committed"],False)
        self.assertLessEqual(len(p.request["input"][0]["content"][0]["text"].encode()),3500)
        self.assertEqual(p.decisions[-1]["omitted_argument_calls"],["a"])

    def test_identity_result_cannot_fit_request_is_blocked_not_silently_truncated(self):
        with self.assertRaises(HistoryProjectionBudgetError):
            project_provider_history({"input":[call("a"),failed("a")]},max_goal_history_bytes=20)

    def test_whole_request_budget_shared_by_history_arrays(self):
        raw={"input":[call("a",text="A"*10000),failed("a")],
             "previous_input_messages":[call("b",text="B"*10000),failed("b")]}
        p=project_provider_history(raw,max_goal_history_bytes=6000)
        size=sum(len(i["content"][0]["text"].encode()) for field in raw for i in p.request[field])
        self.assertLessEqual(size,6000)
        self.assertEqual([f["call_id"] for f in facts(p.request)],["a","b"])

    def test_conflicting_reused_call_id_is_blocked_not_rebound(self):
        cases=[
            [call("same",text="old form",operation="form"),output("same",ok=True,committed=True),
             call("same",text="failed revision"),failed("same")],
            [call("same"),failed("same"),output("same",ok=True,committed=True)],
            [call("same"),{**call("same"),"name":"another_tool"},failed("same")],
            [call(""),failed("")]]
        for items in cases:
            with self.subTest(items=items),self.assertRaises(HistoryProjectionBindingError):
                project_provider_history({"input":items})
        with self.assertRaises(HistoryProjectionBindingError):
            project_provider_history({"input":[call("same"),failed("same")],
                                      "previous_input_messages":[call("same",text="different"),failed("same")]})

    def test_parallel_calls_keep_original_positions_with_receipt_order(self):
        p=project_provider_history({"input":[call("a"),call("b"),failed("b"),failed("a")]})
        fs=facts(p.request)
        self.assertEqual([f["call_id"] for f in fs],["b","a"])
        self.assertEqual([f["history_position"] for f in fs],
            [{"field":"input","call_index":1,"output_index":2},
             {"field":"input","call_index":0,"output_index":3}])

    def test_unknown_receipt_shape_does_not_establish_commit(self):
        raw={"input":[call("a"),{"type":"function_call_output","call_id":"a",
                                  "output":json.dumps({"ok":False,"committed":True})}]}
        f=facts(project_provider_history(raw).request)[0]
        self.assertEqual(f["goal_attempt"]["host_result"]["committed"],"UNKNOWN")

class GoalHistoryBridgeTests(unittest.TestCase):
    def test_actual_bridge_journal_and_required_identity_budget(self):
        captured=[]
        class CPU(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                captured.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200);self.send_header("Content-Length","2");self.end_headers();self.wfile.write(b"{}")
        upstream=ThreadingHTTPServer(("127.0.0.1",0),CPU)
        threading.Thread(target=upstream.serve_forever,daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for budget,expected in [(24000,200),(20,413),(24000,400)]:
                    path=Path(tmp)/f"{budget}-{expected}";path.mkdir()
                    with ProviderHistoryBridge(f"http://127.0.0.1:{upstream.server_port}",
                        max_recovery_bytes=budget,journal_path=path/"decisions.jsonl",
                        audit_path=path/"http.jsonl") as bridge:
                        items=[call("bad"),failed("bad")]
                        if expected==400:
                            items += [call("bad",text="conflicting")]
                        body=json.dumps({"input":items}).encode()
                        from urllib.parse import urlsplit
                        addr=urlsplit(bridge.base_url)
                        con=http.client.HTTPConnection(addr.hostname,addr.port,timeout=5)
                        con.request("POST","/v1/responses",body=body,headers={"Content-Type":"application/json"})
                        response=con.getresponse();self.assertEqual(response.status,expected);response.read();con.close()
                    if expected==200:
                        self.assertEqual(facts(captured[-1])[0]["call_id"],"bad")
                        rows=[json.loads(x) for x in (path/"decisions.jsonl").read_text().splitlines()]
                        self.assertTrue(any(x.get("projection_effect")=="goal_failure_history_budget" for x in rows))
                    else:
                        audit=[json.loads(x) for x in (path/"http.jsonl").read_text().splitlines()]
                        reason="goal_failure_history_over_budget" if expected==413 else "goal_history_identity_conflict"
                        self.assertTrue(any(x.get("reason")==reason and
                            x["upstream_forwarded"] is False for x in audit))
                self.assertEqual(len(captured),1)
        finally:upstream.shutdown();upstream.server_close()
