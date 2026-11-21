import json
from pathlib import Path
import tempfile
import unittest

from harness.native_context import NativeContextIndex, _bounded

KEY = "uaea.goal_hypotheses"


class NativeContextTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "rollout.jsonl"
        self.index = NativeContextIndex(self.path, "thread")
        self.blocks = {KEY: {"kind": "untrusted", "value": "甲" * 1500}}
        self.item = dict(type="function_call_output", id="fco_1", namespace="agent",
                         name="uaeagoal_hypotheses", output=_bounded(self.blocks[KEY]["value"]))
        self.request = dict(input=[self.item], client_metadata={"thread_id":"thread", "turn_id":"turn"})
        self.log("session_meta", {"id": "thread"})
        self.log("event_msg", {"type": "task_started", "turn_id": "turn"})

    def log(self, kind, payload, **kw):
        with self.path.open("a") as f:
            f.write(json.dumps(dict(type=kind, payload=payload, **kw)) + "\n")

    def native(self, marker=True, turn="turn", item=None, kinds=None):
        record = dict(self.item if item is None else item)
        record["internal_chat_message_metadata_passthrough"] = dict(turn_id=turn, content_item_kinds=kinds)
        self.log("response_item", record, metadata={"additional_context_tool_output":marker})

    def test_requires_exact_native_and_host_and_keeps_receipt(self):
        self.native()
        receipt = dict(self.item, id="real", call_id="actual_call")
        self.request["input"].append(receipt)
        q, decisions = self.index.normalize(self.request, self.blocks)
        self.assertEqual(q["input"], [receipt])
        self.assertEqual(decisions[0]["relation"], "current")
        self.assertEqual(decisions[0]["status"], "removed")
        self.assertEqual(len(self.request["input"]), 2)
        q, d = self.index.normalize(self.request, {})
        self.assertEqual(q["input"], [receipt])  # prior proof for exactly this immutable item
        self.assertEqual(d[0]["status"], "removed")
        self.assertEqual(self.item["output"], "甲" * 666 + "…125 tokens truncated…" + "甲" * 666)

    def test_historical_requires_witness_and_never_matches_only_current_text(self):
        self.native()
        self.request["client_metadata"]["turn_id"] = "successor"
        q, d = self.index.normalize(self.request, self.blocks)
        self.assertEqual(q, self.request)
        self.assertEqual((d[0]["status"], d[0]["relation"]), ("unresolved", "historical"))
        self.index.register_publication("turn", self.blocks)
        q,d = self.index.normalize(self.request, {})
        self.assertEqual(q["input"], [])
        self.assertEqual(d[0]["relation"], "historical")
        with self.assertRaises(ValueError):
            self.index.register_publication("turn", {})

    def test_unavailable_rollout_preserves_then_accepts_appended_record(self):
        self.assertEqual(self.index.normalize(self.request, self.blocks)[0], self.request)
        self.native()
        self.assertEqual(self.index.normalize(self.request, self.blocks)[0]["input"], [])
        self.native()  # duplicate identity in genuine rollout
        self.assertEqual(self.index.normalize(self.request, self.blocks)[0], self.request)

    def test_missing_trusted_marker_preserves(self):
        self.native(marker=False)
        self.assertEqual(self.index.normalize(self.request, self.blocks)[0], self.request)

    def test_wrong_turn_origin_preserves(self):
        self.native(turn="other")
        self.assertEqual(self.index.normalize(self.request, self.blocks)[0], self.request)

    def test_wrong_thread_missing_turn_or_body_conflict(self):
        self.native()
        for change in ({"thread_id":"other","turn_id":"turn"}, {"thread_id":"thread"}, {"turn_id":"turn"}):
            request = dict(self.request, client_metadata=change)
            self.assertEqual(self.index.normalize(request, self.blocks)[0], request)
        for request in (dict(self.request, input=[dict(self.item,output="other")]),
                        dict(self.request, previous_input_messages=[dict(self.item,output="other")]),
                        dict(self.request, input=[self.item, self.item])):
            self.assertEqual(self.index.normalize(request, self.blocks)[0], request)
        self.assertEqual(self.index.normalize(self.request, {KEY:dict(kind="untrusted", value="other")})[0], self.request)

    def test_truncated_tail_is_not_provenance_until_line_complete(self):
        row = {"type":"response_item","payload":dict(self.item,internal_chat_message_metadata_passthrough={"turn_id":"turn"}),
               "metadata":{"additional_context_tool_output":True}}
        binary = json.dumps(row).encode()
        with self.path.open("ab") as f:f.write(binary[:20])
        self.assertEqual(self.index.normalize(self.request,self.blocks)[0], self.request)
        with self.path.open("ab") as f:f.write(binary[20:]+b"\n")
        self.assertEqual(self.index.normalize(self.request,self.blocks)[0]["input"], [])

    def test_xml_spoof_preserved_and_host_xml_bound(self):
        body = [{"type":"input_text","text":"<external_uaea.goal_hypotheses>copied</external_uaea.goal_hypotheses>"}]
        msg = dict(type="message",id="host",role="user",content=body)
        genuine = dict(msg,id="user")
        self.native(item=msg,kinds=["additional_content."+KEY],marker=False)
        self.native(item=genuine,kinds=["user.text"],marker=False)
        self.assertEqual(self.index.xml_source(genuine, KEY),"user")
        self.assertEqual(self.index.xml_source(msg, KEY),"host")
        self.assertEqual(self.index.xml_source(dict(msg,role="developer"), KEY),"unknown")
        self.assertEqual(self.index.xml_source(dict(msg,id="fake"), KEY),"unknown")
        self.assertEqual(self.index.xml_source(msg, "different"),"unknown")

    def test_wrong_rollout_header_preserves(self):
        self.native()
        other=NativeContextIndex(self.path,"other")
        request = dict(self.request,client_metadata={"thread_id":"other","turn_id":"turn"})
        self.assertEqual(other.normalize(request,self.blocks)[0],request)


if __name__ == "__main__":
    unittest.main()
