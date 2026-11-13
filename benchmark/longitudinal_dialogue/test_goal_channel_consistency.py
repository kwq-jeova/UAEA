"""Research regression counterexamples, not semantic correctness judgments."""
from pathlib import Path
import sys,tempfile,unittest,json,copy
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[2]),str(Path(__file__).resolve().parents[2]/'scripts')]
import research.longitudinal_dialogue
from research.goal_hypothesis import GoalResearch,TOOL,candidate_head
from research.goal_sideband import ProposalApp
from research.goal_hypothesis_audit import record_binding,projection_binding,sha
from harness.semantic_state_adapter import HarnessSemanticStateAdapter

class ConsistencyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.g=GoalResearch(HarnessSemanticStateAdapter(require_registered_input=True),Path(self.temp.name)/'goal-events.jsonl')
  self.g.semantic.prepare_turn('t','Compare source-grounded designs.',turn_id='turn1')
  self.state=self.g._state('t')
  self.raw={'operation':'form','candidate_id':None,'hypothesis':'Compare reproducible designs','quote':'Compare source-grounded designs.'}
 def app(self):
  app=ProposalApp.__new__(ProposalApp);app.thread_id='t';app.goals=self.g
  self.sent=[];app._send=self.sent.append
  return app
 def message(self):
  return {'id':1,'params':{'threadId':'t','turnId':'turn1','callId':'c','tool':TOOL,'arguments':copy.deepcopy(self.raw)}}
 def events(self):
  return [json.loads(l) for l in self.g.path.read_text().splitlines()]
 def fixture(self):
  self.g.submit('t','turn1','c',self.raw)
  event=next(x['payload'] for x in self.events() if x['event']=='RESEARCH_GOAL_VERSION')
  request=self.g._request(self.state,self.state.current_input_id)
  original={self.state.current_input_id:{'text':request.metadata['text'],'sha256':request.metadata['raw_text_sha256'],'native_turn_id':'turn1','owner':self.state.current_task_id}}
  return event,self.message()['params'],original
 def test_saved_content_tampering_detected_with_unchanged_call_hash(self):
  event,call,original=self.fixture()
  self.assertTrue(record_binding(event,call,original,{},set()))
  for field,value in [('operation','revise'),('previous_candidate_id','wrong'),('hypothesis',{'hypothesis':'OTHER','confidence':'unassessed','status':'inferred'}),
   ('input_id','wrong'),('evidence_ids',['invented']),('submitted_proposal',{})]:
   bad=copy.deepcopy(event);bad['record']['metadata'][field]=value
   # Even a recomputed record checksum cannot mask disagreement with native values.
   bad['receipt']['candidate_sha256']=sha(bad['record'])
   self.assertFalse(record_binding(bad,call,original,{},set()),field)
 def test_materialized_snapshot_tamper_and_missing_version_are_distinct(self):
  from research.goal_hypothesis_audit import snapshot_binding
  event,_,_=self.fixture();record=event['record'];identity=record['object_id']
  path=self.g.path.with_name('goal-research-state.json')
  self.assertEqual(snapshot_binding(path,{identity:record})['status'],'PASS')
  view=json.loads(path.read_text());view['versions'][0]['metadata']['hypothesis']['hypothesis']='OTHER'
  path.write_text(json.dumps(view))
  self.assertEqual(snapshot_binding(path,{identity:record})['status'],'FAIL')
  self.g.save('t')
  extra=copy.deepcopy(record);extra['object_id']='another'
  self.assertEqual(snapshot_binding(path,{identity:record,'another':extra})['status'],'PARTIAL')
 def test_same_id_different_projected_content_detected(self):
  event,call,original=self.fixture();r=event['record'];head=candidate_head(r)
  def prepared(h):return [{'sequence':2,'utc':2,'request_id':'req2','request':{'input':[{'role':'user','content':[{'text':'<external_uaea.goal_hypotheses>'+json.dumps(
   {'heads':[h],'is_source_evidence':False,'semantic_correctness':'not_established'})+'</external_uaea.goal_hypotheses>'}]}]}}]
  good,found=projection_binding(prepared(head),{r['object_id']:r},{r['object_id']:1},[{'request_id':'req2','utc':3,'http_status':200,'bytes_received':100,'bytes_forwarded':100,'upstream_eof':True,'http_framing_complete':True,'response_complete':True,'transport_error':None}])
  self.assertTrue(good[0]['valid']);self.assertEqual(found[r['object_id']],[2])
  bad=copy.deepcopy(head);bad['hypothesis']='OTHER'
  result,found=projection_binding(prepared(bad),{r['object_id']:r})
  self.assertFalse(result[0]['valid']);self.assertEqual(found[r['object_id']],[])
 def test_committed_not_yet_projected_is_not_model_visibility(self):
  event,_,_=self.fixture();r=event['record']
  _,found=projection_binding([{'sequence':1,'request':{'input':[]}}],{r['object_id']:r})
  self.assertEqual(found[r['object_id']],[])
 def test_projection_before_commit_or_without_time_is_not_delivery_proof(self):
  event,_,_=self.fixture();r=event['record'];identity=r['object_id']
  view={'heads':[candidate_head(r)],'is_source_evidence':False,'semantic_correctness':'not_established'}
  request={'sequence':1,'utc':1,'request':{'input':[{'role':'user','content':[{'text':
   '<external_uaea.goal_hypotheses>'+json.dumps(view)+'</external_uaea.goal_hypotheses>'}]}]}}
  output,found=projection_binding([request],{identity:r},{identity:2})
  self.assertFalse(output[0]['valid']);self.assertEqual(found[identity],[])
  output,found=projection_binding([request],{identity:r})
  self.assertIsNone(output[0]['heads'][0]['after_commit']);self.assertEqual(found[identity],[])
 def test_old_head_after_withdraw_is_invalid_even_with_exact_hash(self):
  event,_,_=self.fixture();old=event['record']
  self.g.semantic.prepare_turn('t','Cancel the local task.',turn_id='turn2')
  self.g.submit('t','turn2','withdraw',{'operation':'withdraw','candidate_id':old['object_id'],'hypothesis':'','quote':'Cancel the local task.'})
  records={x.object_id:x.to_dict() for x in self.g.records(self.state)}
  new=next(k for k in records if k!=old['object_id'])
  view={'heads':[candidate_head(old)],'is_source_evidence':False,'semantic_correctness':'not_established'}
  def req(time):return {'sequence':time,'utc':time,'request_id':'r'+str(time),'request':{'input':[{'role':'user','content':[{'text':
   '<external_uaea.goal_hypotheses>'+json.dumps(view)+'</external_uaea.goal_hypotheses>'}]}]}}
  transport=[{'request_id':'r3','utc':4,'http_status':200,'bytes_received':100,'bytes_forwarded':100,'upstream_eof':True,'http_framing_complete':True,'response_complete':True}]
  output,found=projection_binding([req(3)],records,{old['object_id']:1,new:2},transport)
  self.assertFalse(output[0]['valid']);self.assertFalse(output[0]['heads'][0]['current_head_at_request'])
  self.assertEqual(found[old['object_id']],[])
  # Before the withdrawal the old head was legitimate; historical record is not erased.
  output,found=projection_binding([req(1.5)],records,{old['object_id']:1,new:2},[])
  self.assertTrue(output[0]['valid'])
 def test_prepared_is_not_successful_transport(self):
  event,_,_=self.fixture();record=event['record'];identity=record['object_id']
  view={'heads':[candidate_head(record)],'is_source_evidence':False,'semantic_correctness':'not_established'}
  request={'sequence':2,'utc':2,'request_id':'r','request':{'input':[{'role':'user','content':[{'text':
   '<external_uaea.goal_hypotheses>'+json.dumps(view)+'</external_uaea.goal_hypotheses>'}]}]}}
  variants=[[],[{'request_id':'wrong','utc':3,'http_status':200,'bytes_received':5}],
   [{'request_id':'r','utc':3,'http_status':200,'bytes_received':5,'transport_error':'BrokenPipeError'}],
   [{'request_id':'r','utc':3,'http_status':503,'bytes_received':5}],
   [{'request_id':'r','utc':3,'http_status':200,'bytes_received':0}]]
  for transport in variants:
   output,found=projection_binding([request],{identity:record},{identity:1},transport)
   self.assertTrue(output[0]['valid']);self.assertEqual(found[identity],[])
   self.assertNotEqual(output[0]['transport']['status'],'PASS')
 def test_long_hypothesis_projects_exact_full_content_with_hash(self):
  self.raw['hypothesis']='Research '+('x'*480)
  self.g.submit('t','turn1','c',self.raw)
  view=json.loads(self.g.context('t')['uaea.goal_hypotheses']['value'])
  self.assertEqual(view['heads'][0]['hypothesis'],self.raw['hypothesis'])
  self.assertEqual(view['heads'][0]['candidate_sha256'],sha(self.g.records(self.state)[0].to_dict()))
 def test_publication_failure_retains_commit_and_same_call_retry_only_republishes(self):
  app=self.app()
  app._publish_runtime_context=lambda:(_ for _ in ()).throw(ValueError('projection failed'))
  app._handle_tool_call(self.message())
  first=json.loads(self.sent[-1]['result']['contentItems'][0]['text'])
  self.assertTrue(first['committed']);self.assertTrue(first['ok'])
  self.assertEqual(first['host_context_status'],'publication_failed')
  app._publish_runtime_context=lambda:None
  app._handle_tool_call(self.message())
  second=json.loads(self.sent[-1]['result']['contentItems'][0]['text'])
  self.assertEqual(first['candidate_id'],second['candidate_id'])
  self.assertEqual(second['host_context_status'],'publication_call_succeeded')
  self.assertEqual(second['model_context_status'],'not_observed_here')
  self.assertEqual(len(self.g.records(self.state)),1)
  kinds=[x['event'] for x in self.events()]
  self.assertEqual(kinds.count('RESEARCH_GOAL_VERSION'),1)
  self.assertEqual(kinds.count('RESEARCH_GOAL_PUBLICATION'),2)
  self.assertNotIn('RESEARCH_GOAL_REJECTED',kinds)
 def test_materialized_snapshot_failure_does_not_reject_committed_journal(self):
  with patch.object(self.g,'save',side_effect=OSError('disk unavailable')):
   receipt=self.g.submit('t','turn1','c',self.raw)
  self.assertTrue(receipt['committed']);self.assertEqual(receipt['snapshot_status'],'failed')
  receipt2=self.g.submit('t','turn1','c',self.raw)
  self.assertEqual(receipt2['snapshot_status'],'saved')
  self.assertEqual(len(self.g.records(self.state)),1)
  self.assertEqual(sum(x['event']=='RESEARCH_GOAL_VERSION' for x in self.events()),1)
 def test_payload_and_receipt_mutation_cannot_rewrite_committed_state(self):
  self.raw['input_ids']=[self.state.current_input_id]
  receipt=self.g.submit('t','turn1','c',self.raw)
  self.raw['input_ids'].append('fake');receipt['candidate_id']='fake'
  r=self.g.records(self.state)[0]
  self.assertEqual(r.metadata['submitted_proposal']['input_ids'],[self.state.current_input_id])
 def test_missing_required_candidate_id_rejected(self):
  del self.raw['candidate_id']
  with self.assertRaises(ValueError):self.g.submit('t','turn1','c',self.raw)
  self.assertEqual(self.g.records(self.state),[])
 def test_changed_payload_same_call_does_not_create_second_candidate(self):
  self.g.submit('t','turn1','c',self.raw)
  self.raw['hypothesis']='Another interpretation'
  with self.assertRaises(ValueError):self.g.submit('t','turn1','c',self.raw)
  self.assertEqual(len(self.g.records(self.state)),1)
if __name__=='__main__':unittest.main()
