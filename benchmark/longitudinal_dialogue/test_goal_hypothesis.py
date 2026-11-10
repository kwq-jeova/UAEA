"""Candidate lifecycle/authority controls; not semantic accuracy tests."""
from pathlib import Path
import sys,tempfile,unittest,json,copy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import research.longitudinal_dialogue
from research.goal_hypothesis import GoalResearch,ProposalSemanticView,TOOL
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
class CandidateTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.semantic=HarnessSemanticStateAdapter(require_registered_input=True)
  self.g=GoalResearch(self.semantic,Path(self.temp.name)/'goal-events.jsonl')
  self.prepare('Compare reproducible designs, not just deploy a model.')
 def prepare(self,text,turn='turn1',thread='t'):
  self.semantic.prepare_turn(thread,text,turn_id=turn);self.state=self.semantic._state_for(thread)
  self.turn=turn;self.quote=text;self.thread=thread
 def submit(self,operation='form',candidate=None,hypothesis='Understand reproducible design choices',call='call1',**extra):
  return self.g.submit(self.thread,self.turn,call,{'operation':operation,'candidate_id':candidate,'hypothesis':hypothesis,'quote':self.quote,**extra})
 def test_form_does_not_adopt_or_create_execution(self):
  before=self.semantic.snapshot('t');receipt=self.submit();after=self.semantic.snapshot('t')
  self.assertTrue(receipt['ok']);self.assertFalse(receipt['is_execution_observation'])
  for key in ['constraints','execution_authority_item_ids','workflow_continuity','phase1_runtime_snapshot']:
   self.assertEqual(before[key],after[key])
  self.assertEqual(self.state.runtime_objects.step_runs,[])
  self.assertEqual(len(self.g.records(self.state)),1)
 def test_append_only_refine_withdraw_and_history(self):
  r1=self.submit();original=copy.deepcopy(self.g.records(self.state)[0].to_dict())
  self.prepare('Clarify original aim; the path changed.','turn2')
  r2=self.submit('refine',r1['candidate_id'],'Compare designs under resource constraints','call2')
  self.assertEqual(self.g.records(self.state)[0].to_dict(),original)
  self.prepare('Cancel that research direction.','turn3')
  r3=self.submit('withdraw',r2['candidate_id'],'','call3')
  self.assertEqual(self.g.heads(self.state)[0].status,'withdrawn')
  self.assertEqual(len(self.g.records(self.state)),3)
  with self.assertRaises(ValueError):self.submit('revise',r1['candidate_id'],'Stale old parent','call4')
 def test_no_call_means_no_candidate(self):
  self.g.observe_final('t',input_id=self.state.current_input_id,turn_id='turn1',model_event_id='m',text='Hello.')
  self.assertEqual(self.g.heads(self.state),[])
 def test_multiple_candidates_not_votes_or_adoption(self):
  self.submit();self.submit(hypothesis='Maybe only exploring options',call='call2')
  self.assertEqual(len(self.g.heads(self.state)),2);self.assertIsNone(self.state.runtime_objects.active_goal())
 def test_original_input_references_not_model_or_summary(self):
  old=self.state.current_input_id;self.submit(input_ids=[old])
  self.prepare('New user observation.','turn2')
  with self.assertRaises(ValueError):self.submit(input_ids=['model-output:fake'],call='c2')
  self.submit(input_ids=[old],call='c3')
 def test_quote_valid_does_not_mean_summary_correct(self):
  self.submit(hypothesis='The user wants to invest all resources in one GPU.')
  r=self.g.records(self.state)[0]
  self.assertEqual(r.metadata['semantic_correctness'],'not_established')
  self.assertFalse(r.metadata['adoption_eligible'])
 def test_cancelled_input_remains_history_not_authority(self):
  old=self.state.current_input_id
  next(x for x in self.state.runtime_objects.objects if x.object_id==old).status='cancelled'
  self.prepare('Old direction is cancelled; make an archive.','turn2')
  self.submit(input_ids=[old])
  self.assertEqual(self.g.records(self.state)[0].metadata['basis_input_status_at_proposal'][old],'cancelled')
  self.assertIsNone(self.state.runtime_objects.active_goal())
 def test_unknown_evidence_rejected(self):
  with self.assertRaises(ValueError):self.submit(evidence_ids=['execution:not-real'])
 def test_compaction_or_foreign_turn_cannot_create_goal(self):
  with self.assertRaises(ValueError):
   self.g.submit('t','compaction','x',{'operation':'form','candidate_id':None,'hypothesis':'X','quote':self.quote})
 def test_foreign_thread_candidate_rejected(self):
  prior=self.submit()
  self.prepare('Different thread.','turn1','other')
  with self.assertRaises(ValueError):self.submit('revise',prior['candidate_id'],'Unrelated','new')
 def test_same_call_idempotent_not_reweighted(self):
  self.submit();self.submit()
  self.assertEqual(len(self.g.records(self.state)),1)
  with self.assertRaises(ValueError):self.submit(hypothesis='Different content')
 def test_control_cannot_adopt_even_if_mode_changed(self):
  r=self.submit();self.g.mode='adopt'
  with self.assertRaises(ValueError):self.g.control('t','/goal adopt '+r['candidate_id'])
  self.assertIsNone(self.state.runtime_objects.active_goal())
 def test_maintain_cannot_silently_change_text(self):
  r=self.submit()
  with self.assertRaises(ValueError):self.submit('maintain',r['candidate_id'],'New hidden meaning','c2')
 def test_semantic_native_events_do_not_become_observations(self):
  view=ProposalSemanticView(self.semantic)
  rows=[{'method':'rawResponseItem/completed','params':{'threadId':'t','turnId':'turn1','item':{'type':'function_call','name':TOOL,'call_id':'c'}}},
   {'method':'item/completed','params':{'threadId':'t','turnId':'turn1','item':{'type':'dynamicToolCall','tool':TOOL,'id':'c','status':'completed','contentItems':[{'type':'inputText','text':'{"ok":true}'}]}}}]
  before=self.semantic.snapshot('t')
  for m in rows:self.assertEqual(view.consume_raw_event({'message':m}),[])
  after=self.semantic.snapshot('t')
  self.assertEqual(before['last_tool_call'],after['last_tool_call']);self.assertEqual(before['last_execution_observation'],after['last_execution_observation'])
  self.assertEqual(self.state.runtime_objects.step_runs,[])
 def test_user_mention_of_tool_is_not_filtered(self):
  view=ProposalSemanticView(self.semantic)
  self.assertIsNotNone(view.consume_raw_event({'message':{'method':'turn/completed','params':{'threadId':'t','turn':{'id':'turn1','status':'completed','items':[]}}}}))
 def test_goal_tool_uses_same_canonical_format_as_existing_tools(self):
  from research.goal_sideband import ProposalAdapter
  from h3_context_characterization import build_adapter
  with tempfile.TemporaryDirectory() as folder:
   base=build_adapter(Path(folder));binding=next(b for b in base.bindings if b.capability=='document.read_section')
   adapter=ProposalAdapter(base.registry,[binding])
   self.assertEqual({t['type'] for t in adapter.dynamic_tools()},{'function'})
   self.assertEqual(adapter.dynamic_tools()[-1]['name'],TOOL)
 def test_cleanup_observes_process_even_when_start_did_not_return(self):
  import subprocess
  from research.longitudinal_dialogue import close_with_receipt
  process=subprocess.Popen([sys.executable,'-c','pass'],start_new_session=True)
  class App:
   def close(self):process.wait(timeout=5)
  app=App();app.process=process
  result=close_with_receipt(app,None,None)
  self.assertEqual(result['leader_pid'],process.pid);self.assertEqual(result['leader_returncode'],0)
  self.assertEqual(result['process_group_state'],'absent')
 def test_context_typed_and_bounded(self):
  self.submit();ctx=self.g.context('t')
  self.assertEqual(ctx['uaea.goal_hypotheses']['kind'],'untrusted')
  self.assertLess(len(ctx['uaea.goal_hypotheses']['value']),4200)
  self.assertEqual(json.loads(ctx['uaea.goal_state']['value'])['active_goal_id'],'')
 def test_native_handler_receipt_roundtrip_is_not_execution(self):
  from research.goal_sideband import ProposalApp
  app=ProposalApp.__new__(ProposalApp)
  app.thread_id='t';app.goals=self.g
  published=[];sent=[]
  app._publish_runtime_context=lambda:published.append(self.g.context('t'))
  app._send=sent.append
  params={'threadId':'t','turnId':'turn1','callId':'native-c','tool':TOOL,
   'arguments':{'operation':'form','candidate_id':None,'hypothesis':'Compare reproducible designs','quote':self.quote}}
  app._handle_tool_call({'id':12,'params':params})
  self.assertEqual(len(published),1)
  result=sent[0]['result'];receipt=json.loads(result['contentItems'][0]['text'])
  self.assertTrue(result['success']);self.assertFalse(receipt['is_execution_observation'])
  self.assertFalse(receipt['active_goal_changed']);self.assertEqual(self.state.runtime_objects.step_runs,[])
  self.assertEqual(len(self.g.records(self.state)),1)
 def test_native_handler_rejects_foreign_turn_without_retaining_candidate(self):
  from research.goal_sideband import ProposalApp
  app=ProposalApp.__new__(ProposalApp)
  app.thread_id='t';app.goals=self.g
  sent=[];app._send=sent.append
  app._publish_runtime_context=lambda:self.fail('Rejected proposal cannot publish a new candidate')
  app._handle_tool_call({'id':13,'params':{'threadId':'t','turnId':'not-current',
   'callId':'foreign-c','tool':TOOL,'arguments':{}}})
  self.assertFalse(sent[0]['result']['success'])
  self.assertEqual(self.g.records(self.state),[]);self.assertEqual(self.state.runtime_objects.step_runs,[])

class AuditStatusTests(unittest.TestCase):
 def status(self,checks=(),completed=True,separate=True,active=(None,)):
  from research.goal_hypothesis_audit import lifecycle_status
  return lifecycle_status(list(checks),completed,separate,list(active))
 def test_no_proposal_cannot_pass_complete_or_incomplete(self):
  self.assertEqual(self.status(),'UNKNOWN')
  self.assertEqual(self.status(completed=False),'UNKNOWN')
 def test_real_checks_need_completed_session_and_snapshot(self):
  good={'model_and_source_bound':True,'basis_versions_resolved':True}
  self.assertEqual(self.status([good]),'PASS')
  self.assertEqual(self.status([good],completed=False),'PARTIAL')
  self.assertEqual(self.status([good],active=()),'PARTIAL')
 def test_actual_violation_fails_even_without_proposals(self):
  self.assertEqual(self.status(separate=False),'FAIL')
  self.assertEqual(self.status(active=('unexpected-active-goal',)),'FAIL')
  self.assertEqual(self.status([{'model_and_source_bound':False,'basis_versions_resolved':True}]),'FAIL')

if __name__=='__main__':unittest.main()
