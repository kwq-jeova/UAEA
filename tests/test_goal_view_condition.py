from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.research.goal_view_condition import prepare_goal_view, verify_captured_turn, verify_goal_view_transport


VIEW = {"heads": [{"candidate_id": "goal:old", "hypothesis": "current procurement goal"}]}
TAG = "external_uaea.goal_hypotheses"


def xml(view=VIEW, **kw):
    text = f"<{TAG}>\n{json.dumps(view, ensure_ascii=False)}\n</{TAG}>"
    return {"role": "user", "content": [{"type": "input_text", "text": text}], **kw}


def native(i):
    return {"namespace": "agent", "type": "function_call_output", "id": i,
            "name": "uaeagoal_hypotheses", "output": json.dumps(VIEW)}


def audit(q, request_id="r"):
    digest = hashlib.sha256(json.dumps(q, ensure_ascii=False).encode()).hexdigest()
    return [{"event": "request_prepared", "forwarded_bytes_sha256": digest, "request_id": request_id},
            {"event": "transport_started", "http_status": 200, "request_id": request_id},
            {"event": "transport_result", "http_status": 200, "response_complete": True,
             "request_id": request_id}]


class GoalViewConditionTests(unittest.TestCase):
    def setUp(self):
        self.history = [
            {"type": "message", "role": "user", "content": [
                {"type": "input_text", "text": f"Please explain my goal. <{TAG}>..."}]},
            {"type": "function_call", "call_id": "c", "name": "goal_hypothesis"},
            {"type": "function_call_output", "call_id": "c", "output": json.dumps(
                {"kind": "goal_hypothesis_receipt", "committed": True, **VIEW})}]
        self.req = {"input": self.history + [xml()], "tools": [{"name": "goal_hypothesis"}]}

    def prepare(self, arm, req=None, **kw):
        return prepare_goal_view(self.req if req is None else req, arm, expected_view=VIEW,
                                 current_index=len(self.history), **kw)

    def test_sent_arms_bind_http_body_and_preserve_all_history_and_tools(self):
        original = deepcopy(self.req)
        for arm in ["on", "off"]:
            sent, before = self.prepare(arm)
            with self.subTest(arm=arm):
                self.assertTrue(before["valid"])
                self.assertEqual(before["goal_view_removed"], arm == "off")
                self.assertEqual(original, self.req)
                self.assertEqual(self.history, sent["input"][:len(self.history)])
                self.assertEqual(sent["tools"], original["tools"])
                after = verify_goal_view_transport(sent, audit(sent), "r", arm, expected_view=VIEW)
                self.assertTrue(after["valid"])
                self.assertEqual(after["historical_goal_receipts"][0]["call_id"], "c")

    def test_residual_native_and_previous_xml_invalidate_without_erasing_either(self):
        for arm in ["on", "off"]:
            q = {**self.req, "previous_input_messages": [native("past"), xml(id="msg_past")]}
            sent, proof = self.prepare(arm, q)
            self.assertFalse(proof["valid"])
            self.assertFalse(proof["goal_view_removed"])
            self.assertEqual(proof["current_renderer_item_removed"], arm == "off")
            self.assertEqual(sent["previous_input_messages"], q["previous_input_messages"])
            self.assertEqual(proof["unbound_native"][0]["item_id"], "past")
            self.assertEqual(proof["unbound_xml"][0]["item_id"], "msg_past")

    def test_both_in_current_list_are_detected(self):
        q = {**self.req, "input": self.req["input"] + [native("unresolved")]}
        for arm in ["on", "off"]:
            sent, proof = self.prepare(arm, q)
            self.assertFalse(proof["valid"])
            self.assertIn(native("unresolved"), sent["input"])
            self.assertFalse(verify_goal_view_transport(
                sent, audit(sent), "r", arm, expected_view=VIEW)["valid"])

    def test_wrong_slot_missing_slot_duplicate_or_mismatched_host_never_removed(self):
        for items, slot in [(self.req["input"], None), (self.req["input"], 0), ([xml(), xml()], 0),
                            ([xml({"heads": []})], 0), ([xml(id="historical")], 0)]:
            q = {"input": items}
            sent, proof = prepare_goal_view(q, "off", expected_view=VIEW, current_index=slot)
            self.assertFalse(proof["valid"])
            self.assertFalse(proof["goal_view_removed"])
            self.assertEqual(q, sent)

    def test_same_tool_name_for_paired_call_does_not_turn_receipt_into_a_host_view(self):
        items = [dict(type="function_call", name="uaeagoal_hypotheses", call_id="legit"),
                 {**native("fco_abc"), "call_id": "legit"}, xml()]
        sent, proof = prepare_goal_view({"input": items}, "off", expected_view=VIEW, current_index=2)
        self.assertTrue(proof["valid"])
        self.assertEqual(sent["input"], items[:2])
        for inconsistent in [[items[1], items[0], items[2]],
                             [items[0], items[0], items[1], items[2]]]:
            sent, proof = prepare_goal_view({"input": inconsistent}, "off", expected_view=VIEW,
                                            current_index=len(inconsistent) - 1)
            self.assertFalse(proof["valid"])
            self.assertIn(items[1], sent["input"])

    def test_compaction_never_applies_ablation_and_requires_no_dedicated_view(self):
        for arm in ["on", "off"]:
            for items in [self.history, self.req["input"], [native("previous")]]:
                sent, proof = prepare_goal_view({"input": items}, arm, expected_view=None, compact=True)
                self.assertFalse(proof["goal_view_removed"])
                self.assertEqual(sent["input"], items)
                self.assertEqual(items == self.history, proof["valid"])

    def test_hash_mismatch_duplicate_receipt_invalid_id_and_truncation_not_scored(self):
        sent, _ = self.prepare("off")
        records = audit(sent)
        for bad, rid in [(audit(self.req), "r"), (records[1:], "r"), (records + [records[0]], "r"),
                         (records, "other"), (records, ""), (records[:-1], "r"),
                         (records[:-1] + [{**records[-1], "response_complete": False}], "r")]:
            self.assertFalse(verify_goal_view_transport(
                sent, bad, rid, "off", expected_view=VIEW)["valid"])

    def test_uncanonical_or_partial_reserved_envelope_not_removed_or_certified(self):
        for item in [{"role": "user", "content": xml()["content"][0]["text"]},
                     {"role": "user", "content": [{"type": "input_text", "text": f"<{TAG}>x"}]},
                     {**xml(), "role": "developer"}]:
            q = {**self.req, "input": self.req["input"] + [item]}
            sent, proof = self.prepare("off", q)
            self.assertFalse(proof["valid"])
            self.assertIn(item, sent["input"])
            self.assertTrue(proof["unbound_xml"])

    def test_saved_arm_checks_the_host_even_when_the_view_is_absent(self):
        sent, before = self.prepare("off")
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            def put(name, obj):
                (folder / name).write_text(json.dumps(obj, ensure_ascii=False))
            events = audit(sent)
            events[0]["sequence"] = 1
            (folder / "model-http-audit.jsonl").write_text("\n".join(map(json.dumps,events)))
            put("actual-projected-request-1.json", sent)
            before["expected_view"] = VIEW
            put("projection-proof-1.json", before)
            host = dict(provider_request_sequence=1, source="published_host_snapshot",
                        kind="host_context_restored",
                        goal_value_sha256=hashlib.sha256(json.dumps(VIEW, ensure_ascii=False).encode()).hexdigest())
            put("provider-history-decisions.jsonl", host)
            self.assertTrue(verify_captured_turn(folder, "off")[0]["strict_off_verified"])
            self.assertFalse(verify_captured_turn(folder, "on")[0]["valid"])
            put("projection-proof-1.json", {**before, "expected_view": {"heads": []}})
            with self.assertRaisesRegex(ValueError, "Host publication"):
                verify_captured_turn(folder, "off")
            (folder / "actual-projected-request-1.json").unlink()
            with self.assertRaisesRegex(ValueError, "counts differ"):
                verify_captured_turn(folder, "off")

    def test_uninspectable_remote_history_cannot_get_clean_off(self):
        sent, proof = self.prepare("off", {**self.req, "previous_response_id": "remote"})
        self.assertFalse(proof["valid"])
        self.assertIn("server_history_not_auditable_from_this_body", proof["reasons"])
