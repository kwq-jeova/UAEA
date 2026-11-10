"""Offline controls; not tests of natural Goal understanding."""
from pathlib import Path
import copy,importlib.util,json,tempfile,unittest,sys,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[2]
def load(n):
 p=ROOT/'scripts/research'/('longitudinal_'+n+'.py')
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
prepare=load('prepare');audit=load('audit')
class Controls(unittest.TestCase):
 def test_fair_script_plan(self):
  d=json.loads((ROOT/'benchmark/longitudinal_dialogue/scenarios.json').read_text())
  p=prepare.make_plan(d)
  self.assertEqual(len(p),8)
  for c in d['cases']:
   self.assertEqual({x['arm'] for x in p if x['case']==c['id']},{'relevant_history','goal_shadow'})
  self.assertEqual(sum(len(next(c for c in d['cases'] if c['id']==x['case'])['turns']) for x in p),20)
 def test_bad_case_identity(self):
  for caseid in ['../escape','/tmp/data','x/y']:
   with self.assertRaises(ValueError):prepare.make_plan({'cases':[{'id':caseid,'turns':['a','b']}]})
  with self.assertRaises(ValueError):prepare.make_plan({'cases':[{'id':'duplicate','turns':['a','b']},{'id':'duplicate','turns':['a','b']}]})
 def test_control_input_not_user_turn(self):
  with self.assertRaises(ValueError):prepare.make_plan({'cases':[{'id':'test','turns':['a','/goal adopt x']}]})
 def test_claim_is_not_execution(self):
  self.assertFalse(audit.grounded_literal('已读取 ledger.md VELA-47Q2',[]))
 def test_wrong_source_and_failure(self):
  event={'event_type':'OBSERVATION','payload':{'decision':{'capability':'document.read_section','effective_parameters':{'path':'ledger.md'}},'execution_observation':{'status':'success','data':{'text':'VELA-47Q2'}}}}
  self.assertTrue(audit.grounded_literal('ledger.md VELA-47Q2',[event]))
  wrong=copy.deepcopy(event);wrong['payload']['decision']['effective_parameters']['path']='other.md'
  self.assertFalse(audit.grounded_literal('ledger.md VELA-47Q2',[wrong]))
  failed=copy.deepcopy(event);failed['payload']['execution_observation']['status']='failure'
  self.assertFalse(audit.grounded_literal('ledger.md VELA-47Q2',[failed]))
  absent=copy.deepcopy(event);absent['payload']['execution_observation']['data']={'text':'different content'}
  self.assertFalse(audit.grounded_literal('ledger.md VELA-47Q2',[absent]))
 def test_real_fixture_paths(self):
  sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
  import memory.sqlite_store
  from h3_context_characterization import build_adapter
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a=build_adapter(root);p=root/'sandbox/ledger.md'
   p.write_text('# Ledger\n\n## Record\n\nCPU fixture.\n')
   for i,path in enumerate(['ledger.md',str(p)]):
    result=a.dispatch({'threadId':'cpu','turnId':'cpu','callId':str(i),'tool':'read_section','arguments':{'path':path,'section_index':1}})
    self.assertTrue(result.ok)
 def test_output_refuses_existing(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'keep').write_text('user data')
   result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/research/longitudinal_prepare.py'),'--output',str(p)],capture_output=True)
   self.assertNotEqual(result.returncode,0);self.assertEqual((p/'keep').read_text(),'user data')
 def test_incomplete_is_not_pass(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'plan.json').write_text(json.dumps([{'id':'absent','case':'path','arm':'relevant_history'}]));(p/'scenarios.json').write_text(json.dumps({'cases':[{'id':'path','turns':['a','b']}]}))
   r=audit.audit(p);self.assertEqual(r['infrastructure_pass'],0)
class PartialExcerpt(unittest.TestCase):
 def test_prefix_is_not_hash_of_full_section(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ledger.md';section='## Section'+chr(10)+'A'*1200;p.write_text('# File'+chr(10)+section+chr(10))
   data={'line_start':2,'line_end':3,'content_excerpt':section[:1000],'content_hash':hashlib.sha256(section.encode()).hexdigest(),'source_hash':hashlib.sha256(p.read_bytes()).hexdigest()}
   manifest={'path':str(p),'sha256':data['source_hash']}
   x=audit.document_hash_check(data,manifest)
   self.assertTrue(x['section_hash_matches']);self.assertFalse(x['excerpt_is_full_section'])
   data['content_hash']='forged';self.assertFalse(audit.document_hash_check(data,manifest)['section_hash_matches'])
class PreparationSnapshot(unittest.TestCase):
 def test_finance_preparation_has_fixture_and_versioned_code(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'new'
   result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/research/longitudinal_prepare.py'),'--output',str(target),'--scenarios',str(ROOT/'benchmark/longitudinal_dialogue/finance/scenarios.json'),'--snapshot'],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertTrue((target/'financial-ledger.md').is_file())
   self.assertTrue((target/'bundle/UAEA/scripts/research/longitudinal_dialogue.py').is_file())
   self.assertTrue((target/'source-lock.json').is_file())
   self.assertEqual(len(json.loads((target/'plan.json').read_text())),6)
class TurnIntegrity(unittest.TestCase):
 def sample(self):
  return ['a','b'],[{'turn':i+1,'user_text':x,'native_turn_id':'t'+str(i)} for i,x in enumerate(['a','b'])],[{'id':'t0','status':'completed'},{'id':'t1','status':'completed'}],[{'last_turn_id':'t0'},{'last_turn_id':'t1'}],{'turns':2}
 def test_complete(self):self.assertEqual(audit.turn_integrity(*self.sample()),[])
 def test_missing_turn_everywhere(self):
  expected,logs,ends,snaps,result=self.sample()
  self.assertIn('expected_turn_count_mismatch',audit.turn_integrity(expected,logs[:1],ends[:1],snaps[:1],{'turns':1}))
 def test_empty_vacuous(self):
  self.assertIn('expected_turn_count_mismatch',audit.turn_integrity(['a'],[],[],[],{'turns':0}))
 def test_duplicate_native_id(self):
  a,l,e,s,r=self.sample();e[1]['id']='t0'
  self.assertIn('duplicate_or_missing_native_turn_id',audit.turn_integrity(a,l,e,s,r))
 def test_wrong_user_script(self):
  a,l,e,s,r=self.sample();l[1]['user_text']='wrong'
  self.assertIn('script_input_mismatch',audit.turn_integrity(a,l,e,s,r))
 def test_snapshot_wrong_turn(self):
  a,l,e,s,r=self.sample();s[1]['last_turn_id']='old'
  self.assertIn('snapshot_turn_binding_mismatch',audit.turn_integrity(a,l,e,s,r))
class FixtureProjection(unittest.TestCase):
 def test_source_bundle_tamper_rejected(self):
  from unittest.mock import patch
  runner=load('dialogue')
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);code=root/'x.py';code.write_text('original')
   (root/'source-lock.json').write_text(json.dumps({'x.py':hashlib.sha256(code.read_bytes()).hexdigest()}))
   with patch.object(runner,'ROOT',root):
    runner.verify_source_lock(root)
    code.write_text('changed')
    with self.assertRaises(RuntimeError):runner.verify_source_lock(root)

 def test_actual_sandbox_root_supplies_projection(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  runner=load('dialogue')
  class Bridge:
   _runtime_context={'blocks':{},'input_id':'i'}
   def set_runtime_context(self,blocks,**kwargs):self.blocks=blocks
  with tempfile.TemporaryDirectory() as d:
   app=runner.ScenarioApp.__new__(runner.ScenarioApp)
   app._history_bridge=Bridge();app.thread_id='t';app.workspace=Path(d);app._dynamic_tools=[];app.model='test'
   app._last_turn_context={};app.events_path=Path(d)/'events.jsonl'
   with patch.object(runner.repl.InteractiveAppServer,'_publish_runtime_context_snapshot',return_value=None):
    app._publish_runtime_context_snapshot()
   text=app._history_bridge.blocks['uaea.runtime_facts.filesystem']['value']
   self.assertIn(str(Path(d)),text)
   self.assertEqual(app._last_turn_context['uaea.runtime_facts.filesystem'],app._history_bridge.blocks['uaea.runtime_facts.filesystem'])

class ControlProjection(unittest.TestCase):
 def prepared(self):
  return [{'sequence':1,'utc':1.5,'request':{'input':[]}}]
 def deferred(self):
  return [{'provider_request_sequence':1,'kind':'host_context_deferred_for_compaction','source':'published_host_snapshot'}]
 def test_confirmed_compaction_can_defer_projection(self):
  self.assertTrue(audit.goal_projection_checks(self.prepared(),self.deferred(),True,(1000,2000))[0]['valid'])
 def test_normal_shadow_request_missing_projection_rejected(self):
  self.assertFalse(audit.goal_projection_checks(self.prepared(),[],True,(1000,2000))[0]['valid'])
 def test_prompt_marker_is_not_control_provenance(self):
  requests=self.prepared();requests[0]['request']['input']=[{'role':'user','content':'CONTEXT CHECKPOINT COMPACTION'}]
  self.assertFalse(audit.goal_projection_checks(requests,[],True,(1000,2000))[0]['valid'])
 def test_deferred_outside_native_interval_rejected(self):
  self.assertFalse(audit.goal_projection_checks(self.prepared(),self.deferred(),True,(2000,3000))[0]['valid'])
 def test_unconfirmed_control_rejected(self):
  self.assertFalse(audit.goal_projection_checks(self.prepared(),self.deferred(),True)[0]['valid'])

if __name__=='__main__':unittest.main()
