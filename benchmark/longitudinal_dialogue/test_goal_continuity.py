"""CPU-only continuity storage/identity regressions. No cognitive claims."""
from pathlib import Path
import sys,tempfile,unittest,json,copy,subprocess
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[2]),str(Path(__file__).resolve().parents[2]/'scripts')]
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from research.goal_continuity import ContinuityJournal,PersistentGoals,digest,verified_observations
from research.goal_hypothesis import GoalResearch

class ContinuityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.profile=self.root/'profile'
  self.store=ContinuityJournal(self.profile,create=True);self.addCleanup(self.store.close)
 def goals(self,thread='t',turn='u1',text='Research AI industry investment opportunities.'):
  semantic=HarnessSemanticStateAdapter(require_registered_input=True)
  semantic.prepare_turn(thread,text,turn_id=turn)
  return PersistentGoals(semantic,self.root/thread/'goal-events.jsonl',self.store)
 def submit(self,g,thread='t',turn='u1',call='c1',operation='form',parent=None,text='Research AI industry investment opportunities.',quote='Research AI industry investment opportunities.'):
  raw={'operation':operation,'candidate_id':parent,'hypothesis':text,'quote':quote}
  g.native_call={'threadId':thread,'turnId':turn,'callId':call,'tool':'goal_hypothesis','arguments':raw}
  return g.submit(thread,turn,call,raw)
 def seed(self):
  g=self.goals();r=self.submit(g);cid=r['candidate_id'];self.store.bind_scope(cid,'global','CPU explicit scope fixture')
  return g,cid
 def rewrite(self,mutate):
  entries=copy.deepcopy(self.store.entries);mutate(entries)
  previous='';raw=b''
  for i,e in enumerate(entries,1):
   part=ContinuityJournal._envelope(e['kind'],e['payload'],i,previous)
   previous=json.loads(part)['sha256'];raw+=part
  self.store.path.write_bytes(raw)
 def test_close_process_reopen_and_same_heads(self):
  _,cid=self.seed();before=self.store.view('new')
  self.store.close()
  with ContinuityJournal(self.profile)as restarted:
   self.assertEqual(restarted.view('new'),before)
   self.assertEqual(restarted.heads('new')[0]['object_id'],cid)
   self.assertEqual(restarted.handled.keys(),{('t','u1','c1')})
  code="import sys,json;from research.goal_continuity import ContinuityJournal\nwith ContinuityJournal(sys.argv[1])as s:print(json.dumps(list(s.versions)))"
  env=dict(__import__('os').environ,PYTHONPATH=str(Path(__file__).resolve().parents[2])+':'+str(Path(__file__).resolve().parents[2]/'scripts'))
  got=subprocess.check_output([sys.executable,'-B','-c',code,str(self.profile)],env=env,text=True)
  self.assertEqual(json.loads(got),[cid])
 def test_repeated_recovery_does_not_append_or_duplicate(self):
  self.seed();self.store.close();raw=(self.profile/'goal-journal.jsonl').read_bytes()
  for _ in range(3):
   with ContinuityJournal(self.profile)as s:self.assertEqual(len(s.versions),1)
  self.assertEqual(raw,(self.profile/'goal-journal.jsonl').read_bytes())
 def test_global_local_scope_and_cross_thread_parent(self):
  _,global_id=self.seed()
  local=self.goals('local');r=self.submit(local,'local',call='lc',text='Analyze current Intel report')
  self.assertEqual(len(self.store.heads('local')),2)
  self.assertEqual([r['object_id']for r in self.store.heads('new')],[global_id])
  g=self.goals('new',turn='u2',text='The long-term purpose is still investment research; clarify it.')
  receipt=self.submit(g,'new','u2','c2','refine',global_id,'Research AI investment methods','The long-term purpose')
  self.assertTrue(receipt['committed']);new=receipt['candidate_id']
  self.assertEqual(self.store.versions[new]['metadata']['previous_candidate_id'],global_id)
  self.assertEqual(self.store.families[new],global_id)
  self.assertEqual(self.store.versions[global_id]['metadata']['thread_id'],'t')
  self.assertEqual(self.store.versions[new]['metadata']['thread_id'],'new')
  with self.assertRaises(ValueError):self.submit(g,'new','u2','forbidden','revise',r['candidate_id'],'Wrong target','The long-term purpose')
 def test_same_call_retry_and_changed_payload(self):
  g,cid=self.seed()
  self.assertEqual(self.submit(g)['candidate_id'],cid)
  self.assertEqual(len(self.store.versions),1)
  with self.assertRaises(ValueError):self.submit(g,text='Changed')
  self.assertEqual(len(self.store.versions),1)
 def test_rejected_proposal_no_effective_version(self):
  g,cid=self.seed();raw={'operation':'revise','candidate_id':cid,'hypothesis':'Updated','quote':'Not CURRENT'}
  call={'threadId':'t','turnId':'u1','callId':'bad','tool':'goal_hypothesis','arguments':raw};g.native_call=call
  with self.assertRaises(ValueError):g.submit('t','u1','bad',raw)
  g._event('t','RESEARCH_GOAL_REJECTED',{'turn_id':'u1','call_id':'bad','payload_sha256':digest(raw),'reason':'CURRENT'})
  self.assertEqual([x['object_id']for x in self.store.heads('new')],[cid])
  self.assertEqual(len(self.store.failures),1)
  self.store.reload();self.assertEqual(len(self.store.versions),1)
 def test_truncated_journal_rejected_not_silently_empty(self):
  self.seed();self.store.path.write_bytes(self.store.path.read_bytes()[:-3])
  with self.assertRaises(ValueError):self.store.reload()
 def test_hash_corruption_rejected(self):
  self.seed();raw=self.store.path.read_bytes();self.store.path.write_bytes(raw.replace(b'Research AI',b'Wrong text',1))
  with self.assertRaises(ValueError):self.store.reload()
 def test_parent_tamper_rejected_even_rehashed(self):
  self.seed()
  def mutate(rr):rr[1]['payload']['event']['payload']['record']['metadata']['previous_candidate_id']='invented'
  self.rewrite(mutate)
  with self.assertRaises(ValueError):self.store.reload()
 def test_receipt_false_cannot_be_version_even_rehashed(self):
  self.seed()
  self.rewrite(lambda rr:rr[1]['payload']['event']['payload']['receipt'].update(committed=False))
  with self.assertRaises(ValueError):self.store.reload()
 def test_call_and_input_thread_mismatch_even_rehashed(self):
  self.seed()
  self.rewrite(lambda rr:rr[1]['payload']['inputs'][0]['metadata']['provenance'].update(thread_id='foreign'))
  with self.assertRaises(ValueError):self.store.reload()
 def test_materialized_cache_is_not_loaded(self):
  g,cid=self.seed();g.save('t')
  g.path.with_name('goal-research-state.json').write_text('{"heads":["invented"]}')
  self.store.reload()
  self.assertEqual(self.store.heads('new')[0]['object_id'],cid)
  g.save('t');self.assertTrue(json.loads(g.path.with_name('goal-research-state.json').read_text())['not_recovery_authority'])
 def test_writer_lease(self):
  with self.assertRaises(ValueError):ContinuityJournal(self.profile)
 def test_unknown_original_native_source_is_labelled(self):
  self.seed();view=self.store.view('new')
  self.assertEqual(view['sources'][0]['source_status'],'original_native_record_unavailable')
  self.assertTrue(view['restored_history_is_not_new_observation'])
 def test_changed_external_prefix_degrades_not_invents_observation(self):
  self.seed();iid=next(iter(self.store.inputs))
  p=self.root/'native';p.write_text('real prefix')
  self.store.origins[iid]={'path':str(p),'bytes':len(p.read_bytes()),'sha256':__import__('hashlib').sha256(p.read_bytes()).hexdigest()}
  self.assertEqual(self.store.source_status(iid),'original_native_prefix_verified')
  p.write_text('changed')
  self.assertEqual(self.store.source_status(iid),'original_native_prefix_mismatch')
  p.unlink();self.assertEqual(self.store.source_status(iid),'original_native_record_unavailable')
  self.assertEqual(self.store.observations,{})
 def test_current_quote_not_relaxed_across_thread(self):
  _,cid=self.seed();g=self.goals('new','u2','Please correct your interpretation now.')
  with self.assertRaises(ValueError):self.submit(g,'new','u2','bad','revise',cid,'AI research','Research AI industry investment opportunities.')
  self.assertEqual(self.store.heads('new')[0]['object_id'],cid)
 def test_no_automatic_active_goal_or_memory(self):
  g,_=self.seed();state=g._state('t')
  self.assertEqual(state.runtime_objects.active_goals,[])
  self.assertEqual(state.runtime_objects.active_goal_id,'')
  with self.assertRaises(ValueError):g.control('t','/goal adopt anything')
 def test_budget_is_explicit_and_refuses_impossible_identity(self):
  self.seed();view=self.store.view('new',budget=650)
  self.assertGreater(view['omitted_heads'],0)
  self.assertLessEqual(len(json.dumps(view,ensure_ascii=False)),650)
  with self.assertRaises(ValueError):self.store.view('new',budget=10)
 def test_withdraw_retains_history_but_is_not_effective(self):
  _,cid=self.seed();g=self.goals('new','u2','Cancel this continuing purpose.')
  r=self.submit(g,'new','u2','withdraw','withdraw',cid,'','Cancel this continuing purpose.')
  self.assertEqual(len(self.store.versions),2)
  v=self.store.view('another')
  self.assertEqual(v['heads'][0]['candidate_id'],r['candidate_id'])
  self.assertFalse(v['heads'][0]['current_interpretation_applicable'])
  self.assertEqual(v['history'][0]['candidate_id'],cid)
 def test_append_prevalidates_before_modifying_authority(self):
  _,cid=self.seed();raw=self.store.path.read_bytes()
  with self.assertRaises(ValueError):self.store.bind_scope('invented','global','wrong')
  self.assertEqual(raw,self.store.path.read_bytes())
 def test_audit_note_does_not_change_goal_versions(self):
  _,cid=self.seed();self.store.annotate('Task and Goal may be confused',failure_class='conceptual',references=[cid])
  self.assertEqual(len(self.store.versions),1)
  self.assertEqual(self.store.entries[-1]['kind'],'ANNOTATION')

 def test_failed_recovery_object_cannot_serve_partial_view(self):
  self.seed();self.store.path.write_bytes(self.store.path.read_bytes()[:-1])
  with self.assertRaises(ValueError):self.store.reload()
  with self.assertRaises(ValueError):self.store.view('new')

class ObservationProjectionTests(unittest.TestCase):
 def fixture(self,ok=True,long=False):
  from harness.codex_dynamic_tools import HarnessToolDispatch,ActionRequest,ToolResult,ExecutionObservation
  from hashlib import sha256
  body='source text '*2000 if long else 'source text'
  args={'path':'fixture.md','section_index':1}
  d={'action_id':'call','workflow_id':'workflow','input_id':'input','allowed':True,'proposed_parameters':args}
  if ok:
   data={'content':body,'content_hash':sha256(body.encode()).hexdigest(),'source_hash':'sourcehash',
         'execution_succeeded':True,'execution_status':'success','capability_called':True}
  else:
   data={'error':'file not found','execution_succeeded':False,'execution_status':'failed','capability_called':True}
  observation={'observation_id':'execution:fixture','capability':'document.read_section','tool_name':'read_section',
        'status':'success'if ok else'failure','message':'read fixture'if ok else'file not found',
        'data':{k:v for k,v in data.items()if k!='content'}}
  if ok:observation['data'].update(content_excerpt=body[:1000],content_length=len(body))
  result={'ok':ok,'message':observation['message'],'data':data}
  dispatch=HarnessToolDispatch('thread','turn','call','read_section',ActionRequest('document.read_section',args,request_id='call'),
       ToolResult(**copy.deepcopy(result)),ExecutionObservation(**copy.deepcopy(observation)),max_output_chars=4000,execution_decision=d)
  response=dispatch.to_app_server_response()
  native=[{'message':{'method':'item/tool/call','params':{'threadId':'thread','turnId':'turn','callId':'call','tool':'read_section','arguments':args}}},
    {'message':{'method':'item/completed','params':{'threadId':'thread','turnId':'turn',
      'item':{'type':'dynamicToolCall','id':'call','status':'completed'if ok else'failed','contentItems':response['contentItems']}}}}]
  identity={'item_id':'call','thread_id':'thread','turn_id':'turn'}
  trace=[{'event_type':'EXECUTION_DECISION','identity':identity,'payload':d},
     {'event_type':'OBSERVATION','identity':identity,'payload':{'decision':d,'execution_observation':observation}}]
  step={'execution_observation_id':'execution:fixture','workflow_id':'workflow','action':{'harness':{'turn_id':'turn','call_id':'call','input_id':'input'},
     'arguments':args,'execution_contract':d,'host_execution_receipt':{'execution_observation':observation,'result':result}}}
  return trace,native,[step]
 def test_real_failure_shape_without_body_is_preserved(self):
  args=self.fixture(ok=False);got=verified_observations(*args)
  self.assertEqual(got['execution:fixture']['status'],'failure')
  self.assertNotIn('content_excerpt',got['execution:fixture']['data'])
 def test_success_and_explicitly_bounded_body_are_valid(self):
  for long in [False,True]:
   args=self.fixture(long=long);got=verified_observations(*args)
   self.assertEqual(got['execution:fixture']['status'],'success')
 def test_foreign_call_and_changed_failure_result_rejected(self):
  args=self.fixture(ok=False)
  for field in ['threadId','turnId','callId']:
   bad=copy.deepcopy(args);bad[1][0]['message']['params'][field]='foreign'
   with self.assertRaises(ValueError):verified_observations(*bad)
  bad=copy.deepcopy(args)
  receipt=json.loads(bad[1][1]['message']['params']['item']['contentItems'][0]['text']);receipt['ok']=True
  bad[1][1]['message']['params']['item']['contentItems'][0]['text']=json.dumps(receipt)
  with self.assertRaises(ValueError):verified_observations(*bad)

if __name__=='__main__':unittest.main()
