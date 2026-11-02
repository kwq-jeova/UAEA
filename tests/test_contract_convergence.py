from __future__ import annotations
from copy import deepcopy
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from harness.codex_dynamic_tools import DynamicToolBinding, HarnessDynamicToolAdapter
from harness.execution_host import SharedExecutionHost
from harness.io_contract import turn_context_payload
from harness.request_audit import RequestAudit, redact
from harness.responses_bridge import ProviderHistoryBridge
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from runtime.capability import ToolResult
from runtime.ledger import LedgerStub
from runtime.sandbox import Sandbox
from runtime.tools import ToolRegistry
from phase2.web_capability import web_search_metadata


def setup_host(root):
    root.mkdir(exist_ok=True)
    (root/"README.md").write_text("# Facts\nSource marker: FIXTURE-47\n")
    registry = ToolRegistry(Sandbox(root, root), LedgerStub(root/"traces"))
    seen = []
    def search(args, objective):
        seen.append(deepcopy(args))
        return ToolResult(True, "Fixture source discovery; not a live provider", {
            "execution_succeeded": True, "execution_status": "success", "http_attempted": False,
            "actual_provider": args.get("provider"), "evidence_status": "candidates_available",
            "citable_results": [{"title": "Fixture", "url": "https://example.org/source", "source_id": "s1"}]})
    registry.register_capability(web_search_metadata(), search)
    bindings = [DynamicToolBinding.from_registry(registry, cap, description=cap,
                input_schema={"type":"object","properties":{}})
                for cap in ("web.search", "document.read_section", "fs.list")]
    adapter = HarnessDynamicToolAdapter(registry, bindings)
    semantic = HarnessSemanticStateAdapter()
    adapter.bind_semantic_state_adapter(semantic)
    adapter.execution_boundary = SharedExecutionHost(registry, semantic, root/"contract.jsonl")
    return adapter, semantic, seen


class RequestAuditTests(unittest.TestCase):
    def test_http_snapshot_matches_bytes_received_and_does_not_leak_headers_or_credentials(self):
        received = []
        class Receiver(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                received.append(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b'data: {"type":"response.completed"}\n\n')
        server=ThreadingHTTPServer(("127.0.0.1",0),Receiver)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);audit=root/"audit.jsonl"
                state={"effective_state_id":"state-1","task_id":"w1"}
                request={"model":"local-model","input":[
                    {"role":"developer","content":[{"type":"input_text","text":
                     "<uaea.semantic_state_projection>"+json.dumps(state,separators=(chr(44),chr(58)))+"</uaea.semantic_state_projection>"}]},
                    {"type":"function_call","name":"web_search","call_id":"c1","arguments":"{}"},
                    {"type":"function_call_output","call_id":"c1","output":json.dumps({
                        "ok":True,"api_key":"BODY-SENSITIVE-47","data":{"status":"success",
                        "authorization":{"state":"unknown","subject":"provider_switch"}}})},
                    {"role":"user","content":[{"type":"input_text","text":"continue"}]}],"stream":True}
                raw=json.dumps(request).encode()
                with ProviderHistoryBridge(f"http://127.0.0.1:{server.server_port}",
                        journal_path=root/"decisions.jsonl",audit_path=audit) as bridge:
                    client=http.client.HTTPConnection("127.0.0.1",int(bridge.base_url.rsplit(":",1)[1]))
                    client.request("POST","/v1/responses",raw,{"Authorization":"Bearer HEADER-SENSITIVE-47"})
                    response=client.getresponse();self.assertEqual(response.status,200);response.read();client.close()
                self.assertEqual(received,[raw])
                content=audit.read_text()
                self.assertNotIn("BODY-SENSITIVE-47",content);self.assertNotIn("HEADER-SENSITIVE-47",content)
                events=[json.loads(l) for l in content.splitlines()]
                sent,done=events
                self.assertEqual(done["request_id"],sent["request_id"])
                self.assertEqual(done["http_status"],200)
                self.assertEqual(sent["message_manifest"][0]["state_versions"],[state])
                import hashlib
                self.assertEqual(sent["message_manifest"][0]["context_blocks"][0]["value_sha256"],
                                 hashlib.sha256(json.dumps(state,separators=(chr(44),chr(58))).encode()).hexdigest())
                tool = json.loads(sent["request"]["input"][2]["output"])
                self.assertEqual(tool["data"]["authorization"]["state"],"unknown")
                self.assertEqual([m["type"] for m in sent["message_manifest"]],
                                 ["message","function_call","function_call_output","message"])
                self.assertEqual(sent["original_bytes_sha256"],sent["forwarded_bytes_sha256"])
                self.assertEqual(audit.stat().st_mode&0o777,0o600)
        finally:server.shutdown();server.server_close();thread.join()

    def test_tagged_and_nested_json_redaction_and_size_limit_are_explicit(self):
        self.assertNotIn("private-value",redact('<external_uaea.x>{"password":"private-value"}</external_uaea.x>'))
        self.assertNotIn("private-value",redact('{"api_key":"private-value"}'))
        with tempfile.TemporaryDirectory() as tmp:
            audit=RequestAudit(Path(tmp)/"audit.jsonl",max_snapshot_bytes=20)
            raw=json.dumps({"input":"x"*100}).encode()
            audit.request(raw,raw,path="/v1/responses",sequence=1,decisions=())
            row=json.loads(audit.path.read_text())
            self.assertEqual(row["snapshot_coverage"],"manifest_only_size_limit")
            self.assertIsNone(row["request"])

    def test_unwritable_request_audit_prevents_forwarding(self):
        calls=[]
        class Receiver(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):calls.append(1);self.send_response(200);self.end_headers()
        server=ThreadingHTTPServer(("127.0.0.1",0),Receiver)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);blocked=root/"blocked";blocked.mkdir()
                with ProviderHistoryBridge(f"http://127.0.0.1:{server.server_port}",
                        journal_path=root/"history.jsonl",audit_path=blocked) as bridge:
                    client=http.client.HTTPConnection("127.0.0.1",int(bridge.base_url.rsplit(":",1)[1]))
                    client.request("POST","/v1/responses",'{"input":"hello"}')
                    response=client.getresponse();self.assertEqual(response.status,502);response.read();client.close()
                self.assertEqual(calls,[])
        finally:server.shutdown();server.server_close();thread.join()


class SharedHostTests(unittest.TestCase):
    def test_missing_optional_parameter_gets_policy_source_without_granting_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter,semantic,seen=setup_host(Path(tmp))
            semantic.prepare_turn("thread","Search this topic",turn_id="t1")
            params={"threadId":"thread","turnId":"t1","callId":"c1","tool":"web_search",
                    "arguments":{"query":"topic","provider":"google"}}
            result=adapter.dispatch(params)
            self.assertTrue(result.ok)
            self.assertEqual(seen,[{"query":"topic","provider":"google","allow_fallback":False}])
            self.assertEqual(result.execution_decision["parameter_sources"]["allow_fallback"]["basis"],"system_policy")
            self.assertNotIn("allow_fallback",result.action_request.parameters)
            self.assertEqual(len(semantic.snapshot("thread")["workflow_continuity"]["attempts"]),1)
            # Exact same Action is a receipt replay, never another capability call.
            adapter.dispatch(params);self.assertEqual(len(seen),1)
            params["callId"]="c2";params["arguments"]["allow_fallback"]=True
            denied=adapter.dispatch(params)
            self.assertFalse(denied.ok);self.assertEqual(denied.execution_decision["reason"],"authorization_unknown")
            self.assertEqual(len(seen),1)

    def test_provider_constraint_is_not_lost_by_shared_wiring(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter,semantic,seen=setup_host(Path(tmp))
            semantic.prepare_turn("thread","只用 Google，不允许降级",turn_id="t1")
            result=adapter.dispatch({"threadId":"thread","turnId":"t1","callId":"c1",
                                     "tool":"web_search","arguments":{"query":"topic","provider":"bing"}})
            self.assertFalse(result.ok);self.assertEqual(seen,[])
            self.assertEqual(result.execution_decision["reason"],"legacy_semantic_constraint_conflict")

    def test_actual_file_read_survives_false_harness_echo_and_projection_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter,semantic,_=setup_host(Path(tmp))
            semantic.prepare_turn("thread","Read README Facts",turn_id="t1")
            params={"threadId":"thread","turnId":"t1","callId":"c1","tool":"read_section",
                    "arguments":{"path":"README.md","section":"Facts"}}
            out=adapter.dispatch(params)
            self.assertTrue(out.ok)
            snapshot=semantic.snapshot("thread")
            self.assertEqual(snapshot["last_execution_observation"]["status"],"success")
            semantic.consume_raw_event({"method":"item/completed","params":{
                "threadId":"thread","turnId":"t1","item":{"type":"dynamicToolCall","id":"c1",
                "tool":"read_section","success":False,"status":"failed",
                "contentItems":[{"type":"inputText","text":'{"ok":false,"status":"failed"}'}]}}})
            self.assertEqual(semantic.snapshot("thread")["last_execution_observation"]["status"],"success")
            self.assertEqual(len(snapshot["workflow_continuity"]["attempts"]),1)
            # The host fact already exists before model-facing serialization.
            with patch("harness.codex_dynamic_tools._bounded_json_text",side_effect=ValueError("projection")):
                with self.assertRaises(ValueError):out.to_app_server_response()
            replay=adapter.dispatch(params)
            self.assertEqual(replay.observation.observation_id,out.observation.observation_id)
            self.assertEqual(len(semantic.snapshot("thread")["workflow_continuity"]["attempts"]),1)
            self.assertFalse(snapshot["workflow_continuity"]["completion_established"])

    def test_acquired_host_excerpt_is_not_automatically_model_supplied(self):
        from types import SimpleNamespace
        from hashlib import sha256
        from harness.evidence_provenance import source_inventory
        text="Source excerpt"
        step=SimpleNamespace(capability="web.fetch", action={"harness":{},
            "outcome":{"execution_succeeded":True,"result_available":True,
                       "access_event_id":"source","content_sha256":"hash",
                       "excerpt_delivery":"not_established",
                       "source_excerpt":{"text":text,"source_event_id":"source",
                                         "content_sha256":"hash",
                                         "text_sha256":sha256(text.encode()).hexdigest()}}})
        inventory=source_inventory([step])
        self.assertTrue(inventory[0]["page_fetch_observed"])
        self.assertFalse(inventory[0]["excerpt_supplied"])

    def test_ordinary_answer_is_not_projected_as_a_pending_execution_or_repeated_proposal(self):
        semantic=HarnessSemanticStateAdapter()
        semantic.prepare_turn("t","你是什么模型",turn_id="one")
        semantic.consume_raw_event({"method":"item/completed","params":{
            "threadId":"t","turnId":"one","item":{"type":"agentMessage","id":"a1","text":"模型身份回答"}}})
        payload=semantic.prepare_turn("t","搜索指定主题",turn_id="two").payload
        continuation=payload["workflow_continuation"]
        self.assertNotIn("unattempted_requests",continuation)
        self.assertNotIn("assistant_proposal",continuation)
        self.assertEqual(continuation["current_request"],"搜索指定主题")
        context=turn_context_payload([],semantic_projection=payload)
        self.assertIn("not necessarily unfinished",context["uaea.context_boundary"]["value"])
        manifest=semantic.snapshot("t")["projection_manifest"]
        self.assertEqual(manifest["input_id"],semantic.snapshot("t")["current_input_id"])
        self.assertIn("workflow_continuation",manifest["included_fields"])


if __name__=="__main__":unittest.main()
