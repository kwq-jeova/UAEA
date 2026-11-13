import copy
import hashlib
import json
import unittest
from types import SimpleNamespace
from harness.codex_dynamic_tools import HarnessToolDispatch

class ReceiptProjectionTests(unittest.TestCase):
    def make(self, ok=True, allowed=True):
        decision = {
            "schema": "uaea.execution_contract.v1", "action_id": "call-1",
            "input_id": "input-current", "workflow_id": "wf-1",
            "effective_state_id": "v1", "policy_reference": "read-only",
            "allowed": allowed, "reason": "allowed" if allowed else "policy_denied",
            "retryable": False, "authorization": {"scope": "document.read_section"},
            "request_satisfaction": "not_established",
            "effective_parameters": {"path": "/fixture/source.md"},
            "parameter_sources": {"path": {"basis": "action_proposal"}},
            "retained_request_ids": ["input-" + str(i) for i in range(100)],
            "compatibility_guard": {"valid": allowed, "conflicts": [] if allowed else ["denied"]},
        }
        data = {"content": "Exact source body, not a summary.", "content_hash": "body-hash",
                "source_hash": "source-v1", "path": "/fixture/source.md",
                "execution_status": "success" if ok else "validation_failed",
                "execution_succeeded": ok}
        observation = SimpleNamespace(capability="document.read_section",
            tool_name="read_section", status=data["execution_status"],
            message="Read source" if ok else "Rejected", observation_id="observation-1")
        dispatch = HarnessToolDispatch("thread-1", "turn-1", "call-1", "read_section",
            SimpleNamespace(parameters={"path": "/fixture/source.md"}),
            SimpleNamespace(ok=ok, data=data), observation,
            max_output_chars=12000, execution_decision=decision)
        return dispatch, decision, data

    def test_success_retains_source_receipt_and_full_decision_hash(self):
        d, decision, data = self.make()
        before = copy.deepcopy((decision, data))
        p = json.loads(d.to_app_server_response()["contentItems"][0]["text"])
        view = p["data"]["execution_decision"]
        for key in ("content", "content_hash", "source_hash", "path"):
            self.assertEqual(p["data"][key], data[key])
        for key in ("allowed", "authorization", "effective_parameters", "request_satisfaction",
                    "action_id", "input_id", "workflow_id", "effective_state_id", "policy_reference"):
            self.assertEqual(view[key], decision[key])
        self.assertEqual(p["identity"]["observation_id"], "observation-1")
        self.assertEqual(view["full_decision_sha256"],
            hashlib.sha256(json.dumps(decision, ensure_ascii=False, sort_keys=True).encode()).hexdigest())
        self.assertNotIn("retained_request_ids", view)
        self.assertEqual((decision, data), before)
        self.assertLess(len(json.dumps(view)), len(json.dumps(decision)))

    def test_rejected_or_failed_result_keeps_full_failure_semantics(self):
        for ok, allowed in ((False, False), (False, True), (True, False)):
            with self.subTest(ok=ok, allowed=allowed):
                d, decision, _ = self.make(ok, allowed)
                p = json.loads(d.to_app_server_response()["contentItems"][0]["text"])
                self.assertEqual(p["data"]["execution_decision"], decision)
                self.assertEqual(p["success"] if "success" in p else p["ok"], ok)

    def test_full_trace_decision_remains_unprojected(self):
        d, decision, _ = self.make()
        d.to_app_server_response()
        self.assertEqual(d.execution_decision, decision)
        self.assertEqual(len(d.execution_decision["retained_request_ids"]), 100)

if __name__ == "__main__":
    unittest.main()
