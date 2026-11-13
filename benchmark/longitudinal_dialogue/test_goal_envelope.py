"""Negative controls for isolated final proposals; not cognitive truth tests."""
from pathlib import Path
import sys,tempfile,unittest,json,copy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import research.longitudinal_dialogue
from research.goal_envelope import EnvelopeResearch,decode_proposal
from research.goal_hypothesis import GoalResearch
from harness.semantic_state_adapter import HarnessSemanticStateAdapter

class EnvelopeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.s=HarnessSemanticStateAdapter(require_registered_input=True)
  self.g=EnvelopeResearch(self.s,Path(self.temp.name)/'events.jsonl')
  self.prepare('Study a source-grounded assistant.','t1')
  self.payload={'operation':'form','candidate_id':None,'hypothesis':'Study source-grounded assistance','quote':self.text}
 def prepare(self,text,turn):
  self.text=text;self.turn=turn;self.s.prepare_turn('t',text,turn_id=turn);self.state=self.g._state('t')
 def final(self,value=None,event='m1'):
  text=value if isinstance(value,str) else json.dumps({'answer':'Tentative interpretation.','goal_proposal':self.payload if value is None else value})
  return self.g.observe_final('t',input_id=self.state.current_input_id,turn_id=self.turn,model_event_id=event,text=text)
 def test_plain_claim_never_submitted(self):
  self.assertIsNone(self.final('I revised the Goal.'))
  self.assertEqual(self.g.heads(self.state),[])
 def test_valid_json_inside_plain_answer_is_not_a_submission(self):
  envelope=json.dumps({'answer':'Draft only.','goal_proposal':self.payload})
  self.assertIsNone(self.final('Already saved.\\n'+envelope+'\\nExtra explanation.'))
  self.assertEqual(self.g.heads(self.state),[])
  with self.assertRaises(ValueError):self.final(envelope+'\\nExtra explanation.')
  self.assertEqual(self.g.heads(self.state),[])
 def test_null_and_malformed_are_distinct(self):
  self.final('{"answer":"Unknown.","goal_proposal":null}')
  self.assertEqual(self.g.last_feedback['reason'],'explicit_null_proposal')
  with self.assertRaises(ValueError):self.final('{"answer":"bad","goal_proposal":')
  self.assertEqual(self.g.heads(self.state),[])
 def test_duplicate_or_extra_fields_rejected(self):
  for value in ['{"answer":"x","answer":"y","goal_proposal":null}',
                '{"answer":"x","goal_proposal":null,"adopt":true}']:
   with self.assertRaises(ValueError):decode_proposal(value)
 def test_origin_and_no_authority(self):
  before=self.s.snapshot('t');r=self.final();after=self.s.snapshot('t')
  self.assertEqual(r.metadata['source_kind'],'model_negotiated_final_proposal')
  self.assertEqual(r.source_event_ids,['m1'])
  for key in ['constraints','execution_authority_item_ids','workflow_continuity','phase1_runtime_snapshot']:
   self.assertEqual(before[key],after[key])
  self.assertEqual(self.state.runtime_objects.step_runs,[])
  self.assertFalse(self.g.last_feedback['is_execution_observation'])
 def test_sideband_default_source_preserved(self):
  g=GoalResearch(self.s,Path(self.temp.name)/'sideband.jsonl')
  g.submit('t','t1','call',self.payload)
  self.assertEqual(g.records(self.state)[0].metadata['source_kind'],'model_semantic_tool_proposal')
 def test_bad_quote_and_fake_observation_rejected(self):
  for bad in [{**self.payload,'quote':'not in original'},{**self.payload,'evidence_ids':['fake']}]:
   with self.assertRaises(ValueError):self.final(bad)
  self.assertEqual(self.g.heads(self.state),[])
 def test_same_event_replay_is_idempotent(self):
  a=self.final();b=self.final()
  self.assertEqual(a.object_id,b.object_id);self.assertEqual(len(self.g.records(self.state)),1)
  with self.assertRaises(ValueError):self.final({**self.payload,'hypothesis':'changed same event'})
 def test_revision_parent_and_next_context_receipt(self):
  old=self.final()
  self.prepare('Replace assistance research with a project archive.','t2')
  self.payload={'operation':'revise','candidate_id':old.object_id,'hypothesis':'Study a verifiable project archive','quote':self.text}
  new=self.final(event='m2')
  self.assertEqual(new.metadata['previous_candidate_id'],old.object_id)
  ctx=self.g.context('t')
  state=json.loads(ctx['uaea.goal_state']['value'])
  self.assertEqual(state['last_final_feedback']['candidate_id'],new.object_id)
  self.assertEqual(state['last_final_feedback']['model_context_status'],'requires_successful_outbound_audit')
  self.assertEqual(json.loads(ctx['uaea.goal_hypotheses']['value'])['heads'][0]['candidate_id'],new.object_id)
 def test_foreign_turn_or_input_rejected(self):
  inputid=self.state.current_input_id
  with self.assertRaises(ValueError):
   self.g.observe_final('t',input_id=inputid,turn_id='summary',model_event_id='m',text='{"answer":"x","goal_proposal":null}')
 def test_withdraw_preserves_history_and_rejects_stale_parent(self):
  old=self.final();original=copy.deepcopy(old.to_dict())
  self.prepare('Stop that direction.','t2')
  self.payload={'operation':'withdraw','candidate_id':old.object_id,'hypothesis':'','quote':self.text}
  new=self.final(event='m2')
  self.assertEqual(old.to_dict(),original);self.assertEqual(new.status,'withdrawn')
  self.prepare('A new observation.','t3')
  self.payload={'operation':'revise','candidate_id':old.object_id,'hypothesis':'x','quote':self.text}
  with self.assertRaises(ValueError):self.final(event='m3')

if __name__=='__main__':unittest.main()
