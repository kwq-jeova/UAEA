import sys,tempfile,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from research.correction_continuity import LessonStore,LessonApp
class ContinuityTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/"lessons.db";self.s=LessonStore(self.path)
  self.a={"claim":"验收完成才可开工，不能仅凭到货判断可用。","when_relevant":"设备采购要求截止前可用，但摘要只有到货信息。","one_check":"最多读取一次相关验收条款，材料够则不查。","quote":"验收完成才可开工"}
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def submit(self,**kw):
  v=dict(thread="t",turn="u",call="c",input_id="i",text="验收完成才可开工，请纠正。",arguments=self.a,location="native.jsonl");v.update(kw);return self.s.submit(**v)
 def test_restart_and_retrieve(self):
  r=self.submit();self.s.close();self.s=LessonStore(self.path)
  v=self.s.view("设备采购最晚可用，只有到货日")
  self.assertEqual(v["selected"][0]["candidate_id"],r["candidate_id"])
  self.assertIn("验收完成才可开工",v["selected"][0]["correction_text"])
 def test_duplicate_idempotent(self):
  self.submit();self.assertTrue(self.submit()["duplicate"])
  self.assertEqual(self.s.connection.execute("SELECT count(*) FROM candidates").fetchone()[0],1)
 def test_conflicting_call_rejected(self):
  self.submit()
  with self.assertRaises(ValueError):self.submit(arguments={**self.a,"claim":"不同"})
 def test_noncurrent_quote_rejected(self):
  with self.assertRaises(ValueError):self.submit(arguments={**self.a,"quote":"历史原话"})
 def test_extra_fields_rejected(self):
  with self.assertRaises(ValueError):self.submit(arguments={**self.a,"state":"closed"})
 def test_missing_source_fail_closed(self):
  self.submit();self.s.connection.execute("DELETE FROM source_records");self.s.connection.commit()
  with self.assertRaises(ValueError):self.s.view("验收")
 def test_cannot_hide_candidate(self):
  self.submit();self.s.connection.execute("UPDATE candidates SET candidate_state='closed'");self.s.connection.commit()
  with self.assertRaises(ValueError):self.s.view("验收")
 def test_generic_second_domain_same_code(self):
  self.submit()
  self.submit(call="c2",input_id="i2",text="草案数字不能当成正式采用量。",arguments={"claim":"草案不等于定稿正式采用数字。","when_relevant":"询问正式采用量或草案记录时区分来源状态。","one_check":"最多读取一份对应状态的记录。","quote":"草案数字不能当成正式采用量"})
  v=self.s.view("正式采用量与草案记录是多少")
  self.assertIn("草案",v["selected"][0]["claim"]);self.assertEqual(len(v["inventory"]),2)
 def test_backup_identical_and_does_not_delete(self):
  self.submit();p=Path(self.tmp.name)/"copy.db";self.s.backup(p);other=LessonStore(p)
  try:self.assertEqual(self.s.view("验收"),other.view("验收"))
  finally:other.close()

 def test_corrupt_raw_and_column_rejected(self):
  self.submit();row=self.s.connection.execute("SELECT raw_json FROM candidates").fetchone()
  raw=json.loads(row[0]);raw["claim"]="同时改坏正文"
  self.s.connection.execute("UPDATE candidates SET claim=?,raw_json=?",("同时改坏正文",json.dumps(raw,ensure_ascii=False)));self.s.connection.commit()
  with self.assertRaises(ValueError):self.s.view("验收")
 def test_pending_input_cannot_replace_current_source(self):
  app=object.__new__(LessonApp);app._pending_turn={"turn_id":"old"};app._lesson_text="original";app._correction_open=True
  with self.assertRaises(ValueError):app.run_turn("unsent input")
  self.assertEqual(app._lesson_text,"original")
 def test_pending_correction_cannot_relabel_current_source(self):
  app=object.__new__(LessonApp);app._pending_turn={"turn_id":"old"};app._lesson_text="original";app._correction_open=False
  with self.assertRaises(ValueError):app.run_correction("unsent correction")
  self.assertFalse(app._correction_open)
 def test_foreign_turn_rejected_by_app(self):
  app=object.__new__(LessonApp);app.thread_id="t";app._turn_wait={"turn_id":"u"};app._pending_turn=None;app._correction_open=True
  app._lesson_event=lambda *a:None;responses=[];app._send=responses.append
  app._handle_tool_call({"id":1,"params":{"tool":"correction_lesson","threadId":"t","turnId":"foreign","callId":"c","arguments":self.a}})
  receipt=json.loads(responses[0]["result"]["contentItems"][0]["text"])
  self.assertFalse(receipt["committed"])


 def test_whitespace_cannot_commit_unrecoverable_candidate(self):
  with self.assertRaises(ValueError):self.submit(arguments={**self.a,"claim":" "+self.a["claim"]})
  self.assertEqual(self.s.connection.execute("SELECT count(*) FROM candidates").fetchone()[0],0)
 def test_current_input_text_mismatch_rejected(self):
  from types import SimpleNamespace
  app=object.__new__(LessonApp);app.thread_id="t";app._turn_wait={"turn_id":"u"};app._pending_turn=None
  app._correction_open=True;app._lesson_text="new unsent text"
  snap={"current_input_id":"i","workflow_continuity":{"request_continuity":{"inputs":[{"object_id":"i","metadata":{"text":"original text"}}]}}}
  app.semantic_state=SimpleNamespace(snapshot=lambda thread:snap)
  app._lesson_event=lambda *a:None;responses=[];app._send=responses.append
  app._handle_tool_call({"id":1,"params":{"tool":"correction_lesson","threadId":"t","turnId":"u","callId":"c","arguments":self.a}})
  receipt=json.loads(responses[0]["result"]["contentItems"][0]["text"])
  self.assertFalse(receipt["committed"]);self.assertIn("mismatch",receipt["error"])


 def test_new_call_cannot_duplicate_or_overwrite_one_correction(self):
  self.submit()
  with self.assertRaises(ValueError):self.submit(call="different-call")
  self.assertEqual(self.s.connection.execute("SELECT count(*) FROM candidates").fetchone()[0],1)

 def test_scope_only_abstains_from_claim_only_overlap(self):
  self.submit(arguments={"claim":"使用时不应当成其他数据。","when_relevant":"设备验收开工日程。","one_check":"读取一次验收条款。","quote":self.a["quote"]})
  q="草案不应当成正式数据使用。"
  self.assertEqual(self.s.view(q)["selected"],[])
  old=LessonStore(self.path,retrieval_basis="claim_and_scope")
  try:self.assertEqual(len(old.view(q)["selected"]),1)
  finally:old.close()
 def test_scope_selection_does_not_rewrite_delivered_lesson(self):
  self.submit();q="设备采购要求截止前可用，但摘要只有到货信息。"
  current=self.s.view(q)
  old=LessonStore(self.path,retrieval_basis="claim_and_scope")
  try:self.assertEqual(current["selected"],old.view(q)["selected"])
  finally:old.close()
 def test_invalid_retrieval_basis_rejected(self):
  with self.assertRaises(ValueError):LessonStore(self.path,retrieval_basis="industry_rule")

class ResponseBasisTest(unittest.TestCase):
 def receipt(self,*,ok=True,complete=True,content="source body"):
  params={"callId":"c","threadId":"t","turnId":"u","tool":"read_section","arguments":{"path":"source.md","section_index":1}}
  payload={"identity":{"call_id":"c","thread_id":"t","turn_id":"u"},
   "data":{"execution_succeeded":ok,"content":content if ok else None,
   "document_projection":{"content_complete":complete,"visible_content_sha256":"hash","omitted_content_chars":0},
   "error":None if ok else "not found"}}
  return params,{"success":ok,"contentItems":[{"text":json.dumps(payload)}]}
 def test_zero_reads_does_not_imply_no_historical_reads(self):
  from research.correction_continuity import response_basis
  v=response_basis([],input_id="i")
  self.assertEqual(v["successful_body_receipts"],0)
  self.assertIn("not a statement about earlier",v["scope"])
 def test_success_complete_and_partial_separate(self):
  from research.correction_continuity import read_receipt_fact
  p,r=self.receipt();self.assertEqual(read_receipt_fact(p,r)["body_status"],"complete")
  p,r=self.receipt(complete=False);self.assertEqual(read_receipt_fact(p,r)["body_status"],"partial")
 def test_failed_read_never_counts_as_body(self):
  from research.correction_continuity import read_receipt_fact,response_basis
  p,r=self.receipt(ok=False);fact=read_receipt_fact(p,r)
  self.assertFalse(fact["execution_succeeded"]);self.assertEqual(fact["body_status"],"none")
  self.assertEqual(response_basis([fact],input_id="i")["successful_body_receipts"],0)
 def test_receipt_identity_mismatch_rejected(self):
  from research.correction_continuity import read_receipt_fact
  p,r=self.receipt();p["turnId"]="other"
  with self.assertRaises(ValueError):read_receipt_fact(p,r)
 def test_omission_marked_without_false_full_history(self):
  from research.correction_continuity import response_basis
  v=response_basis([{"body_status":"complete","call_id":str(i)}for i in range(12)],input_id="i")
  self.assertEqual(len(v["recent_receipts"]),8);self.assertEqual(v["omitted_earlier_receipts"],4)
  self.assertEqual(v["successful_body_receipts"],12)
 def test_same_helper_for_both_domains_and_unknown_completeness(self):
  from research.correction_continuity import read_receipt_fact
  for file in ["terms.md","minutes.md"]:
   p,r=self.receipt(complete=None);p["arguments"]["path"]=file
   self.assertEqual(read_receipt_fact(p,r)["path"],file)
   self.assertEqual(read_receipt_fact(p,r)["body_status"],"unknown")

if __name__=="__main__":unittest.main()
