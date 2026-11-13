import copy
import unittest
from scripts.research.longitudinal_audit import goal_projection_checks, native_compaction_intervals

class NaturalCompactionAuditTests(unittest.TestCase):
    def events(self):
        return [{"method":method,"emittedAtMs":instant,
            "params":{"threadId":"thread-1","turnId":"turn-1",
                      "item":{"type":"contextCompaction","id":identity}}}
            for method,instant,identity in [("item/started",1000,"compact-1"),
                                           ("item/completed",2000,"compact-1")]]
    def request(self):
        return {"sequence":1,"utc":1.5,"request":{"input":[{"role":"user","content":[
            {"type":"input_text","text":"You are performing a CONTEXT CHECKPOINT COMPACTION. Create a handoff summary."}]}]}}
    def decisions(self):
        return [{"provider_request_sequence":1,"kind":"host_context_deferred_for_compaction",
                 "source":"published_host_snapshot"}]
    def test_natural_deferral_needs_completed_native_item_and_matching_summary_request(self):
        intervals=native_compaction_intervals(self.events())
        self.assertEqual(intervals,[(1000,2000)])
        self.assertTrue(goal_projection_checks([self.request()],self.decisions(),True,
                                              native_intervals=intervals)[0]["valid"])
    def test_model_marker_or_partial_or_mismatched_native_event_cannot_excuse_missing_goal(self):
        for mutation in ("no_native","not_completed","different_id","different_turn","different_thread",
                         "not_summary_request","outside_interval","no_host_deferral"):
            with self.subTest(mutation=mutation):
                events=copy.deepcopy(self.events());request=self.request();decisions=self.decisions()
                if mutation=="no_native":events=[]
                if mutation=="not_completed":events=events[:1]
                if mutation=="different_id":events[1]["params"]["item"]["id"]="other"
                if mutation=="different_turn":events[1]["params"]["turnId"]="other"
                if mutation=="different_thread":events[1]["params"]["threadId"]="other"
                if mutation=="not_summary_request":request["request"]["input"]=[]
                if mutation=="outside_interval":request["utc"]=3
                if mutation=="no_host_deferral":decisions=[]
                self.assertFalse(goal_projection_checks([request],decisions,True,
                    native_intervals=native_compaction_intervals(events))[0]["valid"])

if __name__=="__main__":
    unittest.main()
