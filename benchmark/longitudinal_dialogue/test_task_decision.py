import sys,tempfile,unittest,json
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/"scripts")]
from research.task_decision import validate_record,aggregate,render,TaskDecisionApp
from research.correction_continuity import LessonApp
SOURCE="用户条件：最晚周五可用。偏好：选便宜的。甲：到货，何时可用未说明。乙：周四可用。"
def proposal():
 return {"conditions":[{"id":"c","quote":"最晚周五可用"}],
 "candidates":[{"id":"a","name":"甲","checks":[{"condition_id":"c","evidence_quote":"甲：到货，何时可用未说明","status":"待确认"}]},
 {"id":"b","name":"乙","checks":[{"condition_id":"c","evidence_quote":"乙：周四可用","status":"符合"}]}],
 "recommendation":{"candidate_id":"b","basis_candidate_ids":["a","b"],"preference_quote":"选便宜的","reason":"乙已确认可用，甲还需确认。"}}
def validate(p):
 return validate_record(json.dumps(p,ensure_ascii=False),source_text=SOURCE,input_id="i",thread_id="t",turn_id="u",event_id="e",location="events.jsonl")
class TaskDecisionTest(unittest.TestCase):
 def test_unknown_survives_supported_fallback_and_render(self):
  r=validate(proposal());text=render(r)
  self.assertEqual(r["overall_status"],{"a":"待确认","b":"符合"})
  self.assertIn("本次先选乙",text);self.assertIn("甲：待确认",text);self.assertNotIn("甲：不符合",text)
  self.assertFalse(r["saved_to_goal_or_lesson"])
  self.assertTrue(all(x["source_id"]=="i"for x in r["source_references"]))
 def test_noncurrent_quote_rejected(self):
  p=proposal();p["candidates"][0]["checks"][0]["evidence_quote"]="历史用户说甲已可用"
  with self.assertRaises(ValueError):validate(p)
 def test_dangling_and_duplicate_condition_binding_rejected(self):
  p=proposal();p["candidates"][0]["checks"][0]["condition_id"]="missing"
  with self.assertRaises(ValueError):validate(p)
  p=proposal();p["conditions"].append({"id":"c","quote":"用户条件"})
  with self.assertRaises(ValueError):validate(p)
 def test_selected_unknown_or_foreign_candidate_rejected(self):
  for cid in ["a","missing"]:
   p=proposal();p["recommendation"]["candidate_id"]=cid
   with self.assertRaises(ValueError):validate(p)
 def test_three_valued_combination_is_not_domain_semantics(self):
  self.assertEqual(aggregate(["符合","待确认"]),"待确认")
  self.assertEqual(aggregate(["待确认","不符合"]),"不符合")
  self.assertEqual(aggregate(["符合","符合"]),"符合")
 def test_wrong_model_semantics_not_silently_corrected(self):
  p=proposal();p["candidates"][0]["checks"][0]["status"]="符合";p["recommendation"]["candidate_id"]="a"
  r=validate(p)
  self.assertEqual(r["overall_status"]["a"],"符合") # quotes valid, but semantic error must remain visible to research
  self.assertIn("NOT verified",r["source_validation"])
 def test_duplicate_keys_and_extra_answer_rejected(self):
  with self.assertRaises(ValueError):validate_record('{"conditions":[],"conditions":[]}',source_text=SOURCE,input_id="i",thread_id="t",turn_id="u",event_id="e",location="x")
  p=proposal();p["answer"]="甲不满足但选甲"
  with self.assertRaises(ValueError):validate(p)
 def test_defer_does_not_claim_absent_candidates(self):
  p=proposal();p["recommendation"]={"candidate_id":None,"basis_candidate_ids":[],"preference_quote":"","reason":"暂不推荐，候选保留。"}
  r=validate(p);self.assertIn("暂不作确定推荐",render(r));self.assertNotIn("没有已判为符合",render(r))
 def test_new_input_clears_current_state_without_erasing_audit(self):
  from unittest.mock import patch
  app=object.__new__(TaskDecisionApp);app._pending_turn=None
  app.current_task_decision={"old":True};app.user_answer="old";app.last_delivery={};app._decision_messages=[{}]
  with patch.object(LessonApp,"run_turn",return_value="native_called"):
   self.assertEqual(app.run_turn("new task"),"native_called")
  self.assertIsNone(app.current_task_decision);self.assertIsNone(app.user_answer);self.assertEqual(app._decision_messages,[])
 def test_foreign_native_identity_cannot_bind_current(self):
  with self.assertRaises(ValueError):validate_record(json.dumps(proposal()),source_text=SOURCE,input_id="",thread_id="t",turn_id="u",event_id="e",location="x")
class RecommendationV2Test(unittest.TestCase):
 def test_inference_reason_is_not_falsely_validated_as_source(self):
  p=proposal();p["recommendation"]["reason"]="先用已确认的乙，甲仍可能符合，待取得可用时间后再判断。"
  self.assertNotIn(p["recommendation"]["reason"],SOURCE)
  r=validate(p)
  self.assertIn(p["recommendation"]["reason"],render(r))
  self.assertFalse(any(x.get("summary")==p["recommendation"]["reason"]for x in r["source_references"]))
  self.assertEqual(r["judgment"]["recommendation"]["basis_candidate_ids"],["a","b"])
 def test_recommendation_cannot_borrow_missing_or_unlinked_judgment(self):
  for ids in [["missing"],["a"],["b","b"],["方案乙"]]:
   p=proposal();p["recommendation"]["basis_candidate_ids"]=ids
   with self.assertRaises(ValueError):validate(p)
 def test_more_expensive_candidate_stays_qualified(self):
  source="用户条件：最晚周五可用。偏好：选便宜的。甲：10元，周四可用。乙：20元，周四可用。"
  p=proposal();p["candidates"][0]["checks"][0].update(evidence_quote="甲：10元，周四可用",status="符合")
  p["candidates"][1]["checks"][0]["evidence_quote"]="乙：20元，周四可用"
  p["recommendation"].update(candidate_id="a",reason="两个都合格，甲便宜；乙只是较贵，不是不合格。")
  r=validate_record(json.dumps(p,ensure_ascii=False),source_text=source,input_id="i",thread_id="t",turn_id="u",event_id="e",location="fixture")
  self.assertEqual(r["overall_status"],{"a":"符合","b":"符合"})
  text=render(r);self.assertIn("本次推荐甲",text);self.assertIn("乙：符合",text)
 def test_host_id_format_fully_exposed_for_all_reference_fields(self):
  from research.task_decision import OUTPUT_SCHEMA,ID_PATTERN,identifier
  schemas=[OUTPUT_SCHEMA["properties"]["conditions"]["items"]["properties"]["id"],
   OUTPUT_SCHEMA["properties"]["candidates"]["items"]["properties"]["id"],
   OUTPUT_SCHEMA["properties"]["candidates"]["items"]["properties"]["checks"]["items"]["properties"]["condition_id"],
   OUTPUT_SCHEMA["properties"]["recommendation"]["properties"]["candidate_id"]["anyOf"][0],
   OUTPUT_SCHEMA["properties"]["recommendation"]["properties"]["basis_candidate_ids"]["items"]]
  for x in schemas:
   self.assertEqual(x,{"type":"string","minLength":1,"maxLength":16,"pattern":ID_PATTERN})
  for value in ["方案甲","0a","a b","a"*17,"a\\n"]:
   with self.assertRaises(ValueError):identifier(value)
  for value in ["A","a_1-B","Z"*16]:self.assertEqual(identifier(value),value)
class NativeSchemaTest(unittest.TestCase):
 def test_native_schema_uses_existing_turn_contract_without_mutating_caller(self):
  from unittest.mock import patch
  from research.task_decision import TaskDecisionApp,OUTPUT_SCHEMA
  from research.correction_continuity import LessonApp
  app=object.__new__(TaskDecisionApp)
  msg={"method":"turn/start","params":{"threadId":"t","input":[{"type":"text","text":"same user"}]}}
  with patch.object(LessonApp,"_request_turn",return_value={"sent":True}) as parent:
   self.assertEqual(app._request_turn(msg,timeout=420),{"sent":True})
   delivered=parent.call_args.args[0]
   self.assertEqual(delivered["params"]["outputSchema"],OUTPUT_SCHEMA)
   self.assertEqual(delivered["params"]["input"],msg["params"]["input"])
   self.assertNotIn("outputSchema",msg["params"])
   self.assertEqual(parent.call_args.kwargs,{"timeout":420})
if __name__=="__main__":unittest.main()
