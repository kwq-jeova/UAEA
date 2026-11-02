from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy
from tests.test_contract_convergence import setup_host
from harness.evidence_provenance import source_inventory, ground_claim


class DocumentEvidenceClosureTests(unittest.TestCase):
    def test_actual_section_read_links_source_but_does_not_verify_generated_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter, semantic, _ = setup_host(Path(tmp))
            semantic.prepare_turn("t","Read Facts",turn_id="one")
            call={"threadId":"t","turnId":"one","callId":"read",
                  "tool":"read_section","arguments":{"path":"README.md","section":"Facts"}}
            result=adapter.dispatch(call)
            self.assertTrue(result.ok)
            store=semantic._state_for("t").runtime_objects
            sources=source_inventory(store.step_runs)
            self.assertEqual(len(sources),1)
            source=sources[0]
            self.assertEqual(source["scope"],"document_section")
            self.assertFalse(source["excerpt_supplied"])
            claim=ground_claim(sources,text="quoted",paths=[source["path"]],
                               quote="Source marker: FIXTURE-47",
                               execution_claim={"path":source["path"],"operation":"document.read_section"})
            self.assertEqual(claim["source_linked"]["status"],"linked")
            self.assertEqual(claim["execution_grounded"]["status"],"supported")
            self.assertEqual(claim["acquired_quote_match"]["status"],"exact_in_acquired_excerpt")
            self.assertEqual(claim["quote_match"]["status"],"not_found_in_supplied_excerpt")
            self.assertFalse(claim["source_evidence"])
            self.assertEqual(claim["content_supported"],"not_assessed_requires_semantic_judgment")
            wrong=ground_claim(sources,text="wrong quotation",paths=[source["path"]],quote="fabricated")
            self.assertEqual(wrong["source_linked"]["status"],"linked")
            self.assertEqual(wrong["acquired_quote_match"]["status"],"not_established")

    def test_null_reference_cannot_link_a_document_with_no_url(self):
        with self.assertRaises(ValueError):
            ground_claim([{"source_id":"obs","url":None}],text="claim",urls=[None])

    def test_no_read_and_history_output_never_create_file_evidence(self):
        adapter=None
        with tempfile.TemporaryDirectory() as tmp:
            adapter, semantic, _=setup_host(Path(tmp))
            semantic.prepare_turn("t","Read README",turn_id="one")
            semantic.consume_raw_event({"method":"item/completed","params":{
                "threadId":"t","turnId":"one","item":{"type":"agentMessage","id":"claim",
                "text":"I read README and its contents are verified."}}})
            semantic.prepare_turn("t","Repeat the quote",turn_id="two")
            store=semantic._state_for("t").runtime_objects
            self.assertEqual(source_inventory(store.step_runs),[])
            claim=ground_claim([],text="read",paths=["README.md"],quote="claimed quote",
                               execution_claim={"path":"README.md","operation":"document.read_section"})
            self.assertEqual(claim["execution_grounded"]["status"],"not_established")
            self.assertEqual(claim["source_linked"]["status"],"not_linked")
            self.assertFalse(claim["history_confers_source_authority"])
            self.assertFalse(semantic.snapshot("t")["workflow_continuity"]["completion_established"])

    def test_failed_read_does_not_create_acquired_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter, semantic,_=setup_host(Path(tmp))
            semantic.prepare_turn("t","Read missing",turn_id="one")
            outcome=adapter.dispatch({"threadId":"t","turnId":"one","callId":"missing",
                "tool":"read_section","arguments":{"path":"missing.md","section":"Facts"}})
            self.assertFalse(outcome.ok)
            self.assertEqual(source_inventory(semantic._state_for("t").runtime_objects.step_runs),[])


class DeliveryAuditTests(unittest.TestCase):
    def test_exact_payload_status_and_body_hash_match_the_host_receipt(self):
        from harness.delivery_audit import audit_deliveries
        from hashlib import sha256
        body="full section\nsecond line"
        host=[{"event_type":"OBSERVATION","identity":{"item_id":"call"},
               "payload":{"execution_observation":{"observation_id":"obs","capability":"document.read_section",
                 "data":{"execution_status":"success","execution_succeeded":True,
                         "content_hash":sha256(body.encode()).hexdigest()}}}}]
        payload={"ok":True,"status":"success","data":{"execution_status":"success",
                                                       "execution_succeeded":True,"content":body}}
        requests=[{"event":"request_prepared","request_id":"req","request":{"input":[
            {"type":"function_call","call_id":"call","arguments":"{}"},
            {"type":"function_call_output","call_id":"call","output":json.dumps(payload)}]}},
            {"event":"transport_result","request_id":"req","http_status":200}]
        report=audit_deliveries(host,requests)
        delivery=report["calls"][0]["deliveries"][0]
        self.assertTrue(delivery["status_matches_host"])
        self.assertTrue(delivery["content_hash_matches_host"])
        self.assertEqual(delivery["index"],1)
        self.assertFalse(report["creates_execution_or_source_facts"])
        payload["data"]["content"]="wrong"
        requests[0]["request"]["input"][1]["output"]=json.dumps(payload)
        self.assertFalse(audit_deliveries(host,requests)["calls"][0]["deliveries"][0]["content_hash_matches_host"])

    def test_failure_history_fact_preserves_false_status_without_becoming_execution(self):
        from harness.delivery_audit import audit_deliveries
        host=[{"event_type":"OBSERVATION","identity":{"item_id":"call"},
               "payload":{"execution_observation":{"observation_id":"obs","capability":"web.search",
                 "data":{"execution_status":"http_failure","execution_succeeded":False}}}}]
        fact={"schema":"uaea.terminal_attempt_fact.v1","call_id":"call","phase":"outcome",
              "observation":{"execution_status":"http_failure","execution_succeeded":False}}
        request={"event":"request_prepared","request_id":"req","request":{"input":[{
            "type":"message","role":"assistant","content":[{"type":"input_text","text":
            "Historical runtime observation, not a tool invocation or user authorization:\n"+json.dumps(fact)}]}]}}
        report=audit_deliveries(host,[request])
        self.assertTrue(report["calls"][0]["deliveries"][0]["status_matches_host"])
        self.assertEqual(report["calls"][0]["deliveries"][0]["representation"],"terminal_history_fact")
        fact["observation"]["execution_succeeded"]=0
        request["request"]["input"][0]["content"][0]["text"]=(
            "Historical runtime observation, not a tool invocation or user authorization:\n"+json.dumps(fact))
        self.assertFalse(audit_deliveries(host,[request])["calls"][0]["deliveries"][0]["status_matches_host"])

    def test_assistant_claim_without_host_receipt_cannot_establish_delivery(self):
        from harness.delivery_audit import audit_deliveries
        requests=[{"event":"request_prepared","request_id":"r","request":{"input":[
            {"role":"assistant","content":[{"type":"input_text","text":"I successfully read README.md"}]}]}}]
        self.assertEqual(audit_deliveries([],requests)["calls"],[])


if __name__=="__main__":unittest.main()
