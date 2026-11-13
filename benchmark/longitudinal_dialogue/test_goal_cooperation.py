"""Research-mode authority and identity negatives, not semantic accuracy tests."""
from pathlib import Path
import sys,tempfile,unittest,json,copy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import research.longitudinal_dialogue
from research.goal_cooperation import CooperationResearch,decode_assessment
from harness.semantic_state_adapter import HarnessSemanticStateAdapter

class CooperationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.s=HarnessSemanticStateAdapter(require_registered_input=True)
  self.g=CooperationResearch(self.s,Path(self.temp.name)/'goal-events.jsonl')
  self.prepare('Study a source-grounded assistant.','t1')
  self.seed={'operation':'form','candidate_id':None,'hypothesis':'Study source-grounded assistance','quote':self.text}
 def prepare(self,text,turn):
  self.text=text;self.turn=turn;self.s.prepare_turn('t',text,turn_id=turn);self.state=self.g._state('t')
 def final(self,text,event='message'):
  return self.g.observe_final('t',input_id=self.state.current_input_id,turn_id=self.turn,model_event_id=event,text=text)
 def establish(self,mode):
  self.g.mechanism=mode
  receipt=self.g.submit('t','t1','seed-call',self.seed)
  self.final('Seed submitted.')
  return receipt
 def assessment(self,judgment='NO_CHANGE',proposal=None,intent=False):
  return json.dumps({'answer':'Research answer.','goal_assessment':{'judgment':judgment,'proposal':proposal,'submit_intent':intent}})
 def events(self):
  return [json.loads(x) for x in self.g.path.read_text().splitlines()]
 def test_seed_context_identical_across_conditions(self):
  contexts=[]
  for mode in ['A','B','C']:
   self.g.mechanism=mode;contexts.append(self.g.context('t'))
  self.assertEqual(contexts[0],contexts[1]);self.assertEqual(contexts[1],contexts[2])
 def test_all_conditions_allow_same_real_seed(self):
  for mode in ['A','B','C']:
   with self.subTest(mode=mode):
    self.g.mechanism=mode
    self.assertTrue(self.g.submit('t','t1','common-seed',self.seed)['committed'])
  self.assertEqual(len(self.g.records(self.state)),1)
 def test_b_replays_committed_seed_receipt_without_new_submission(self):
  old=self.establish('B')
  replay=self.g.submit('t','t1','seed-call',self.seed)
  self.assertEqual(replay['candidate_id'],old['candidate_id'])
  self.assertEqual(len(self.g.records(self.state)),1)
  self.assertEqual(sum(x['event']=='RESEARCH_GOAL_VERSION' for x in self.events()),1)
  with self.assertRaisesRegex(ValueError,'identity reused'):
   self.g.submit('t','t1','seed-call',{**self.seed,'hypothesis':'Different content'})

 def test_b_post_seed_submission_is_explicitly_denied(self):
  old=self.establish('B');self.prepare('Replace assistant with archive.','t2')
  with self.assertRaisesRegex(ValueError,'Assessment-only research condition'):
   self.g.submit('t','t2','revise',{'operation':'revise','candidate_id':old['candidate_id'],'hypothesis':'Study archives','quote':self.text})
  self.assertEqual(len(self.g.records(self.state)),1)
 def test_structured_intent_never_submits_even_in_c(self):
  old=self.establish('C');self.prepare('Replace assistant with archive.','t2')
  payload={'operation':'revise','candidate_id':old['candidate_id'],'hypothesis':'Study archives','quote':self.text}
  self.final(self.assessment('REVISE',payload,True))
  self.assertEqual(len(self.g.records(self.state)),1)
  self.assertEqual(self.g.last_assessment['exact_matching_submission_ids'],[])
  self.assertFalse(self.g.last_assessment['candidate_created_by_assessment'])
 def test_b_assessment_can_retain_candidate_without_adoption(self):
  old=self.establish('B');self.prepare('The assistant purpose continues.','t2')
  before=self.s.snapshot('t')
  self.final(self.assessment())
  after=self.s.snapshot('t')
  self.assertEqual(self.g.heads(self.state)[0].object_id,old['candidate_id'])
  for key in ['constraints','execution_authority_item_ids','workflow_continuity','phase1_runtime_snapshot']:
   self.assertEqual(before[key],after[key])
 def test_c_one_native_call_can_commit_then_assess(self):
  old=self.establish('C');self.prepare('Replace assistant with archive.','t2')
  payload={'operation':'revise','candidate_id':old['candidate_id'],'hypothesis':'Study archives','quote':self.text}
  receipt=self.g.submit('t','t2','native-revise',payload)
  self.final(self.assessment('REVISE',payload,True))
  self.assertEqual(self.g.last_assessment['exact_matching_submission_ids'],[receipt['candidate_id']])
  self.assertEqual(len(self.g.records(self.state)),2)
  self.assertEqual(self.state.runtime_objects.step_runs,[])
 def test_plain_claim_and_wrapped_json_are_not_assessments(self):
  self.establish('C');self.prepare('A new observation.','t2')
  self.final('Already revised.\\n'+self.assessment())
  self.assertIsNone(self.g.last_assessment)
  self.assertEqual(len(self.g.records(self.state)),1)
 def test_foreign_turn_cannot_create_an_assessment(self):
  self.establish('C')
  with self.assertRaises(ValueError):
   self.g.observe_final('t',input_id=self.state.current_input_id,turn_id='summary',model_event_id='m',text=self.assessment())
 def test_duplicate_mismatch_and_false_intent_rejected(self):
  invalid=['{"answer":"x","answer":"y","goal_assessment":null}',
   json.dumps({'answer':'x','goal_assessment':{'judgment':'NO_CHANGE','proposal':None,'submit_intent':True}}),
   json.dumps({'answer':'x','goal_assessment':{'judgment':'UNKNOWN','proposal':self.seed,'submit_intent':False}})]
  for text in invalid:
   with self.assertRaises(ValueError):decode_assessment(text)
 def test_bad_quote_is_invalid_but_does_not_reject_an_existing_commit(self):
  old=self.establish('C');self.prepare('Replace assistant with archive.','t2')
  p={'operation':'revise','candidate_id':old['candidate_id'],'hypothesis':'Study archives','quote':self.text}
  receipt=self.g.submit('t','t2','native-revise',p)
  bad={**p,'quote':'invented'}
  self.final(self.assessment('REVISE',bad,True))
  self.assertFalse(self.g.last_assessment['assessment_valid'])
  self.assertEqual(self.g.heads(self.state)[0].object_id,receipt['candidate_id'])
  self.assertNotIn('RESEARCH_GOAL_REJECTED',[x['event'] for x in self.events()])
 def test_model_assessment_is_projected_as_untrusted_only(self):
  old=self.establish('C');self.prepare('Replace assistant with archive.','t2')
  p={'operation':'revise','candidate_id':old['candidate_id'],'hypothesis':'Study archives','quote':self.text}
  self.final(self.assessment('REVISE',p,True))
  ctx=self.g.context('t')
  self.assertEqual(ctx['uaea.goal_assessment']['kind'],'untrusted')
  trusted=json.loads(ctx['uaea.goal_state']['value'])['last_assessment_feedback']
  self.assertNotIn('assessment',trusted)
  self.assertNotIn('derived_model_assessment',trusted)
 def test_unknown_nochange_need_no_candidate_or_version(self):
  self.establish('C');self.prepare('Only resources changed.','t2')
  for judgment in ['UNKNOWN','NO_CHANGE']:
   self.final(self.assessment(judgment=judgment))
  self.assertEqual(len(self.g.records(self.state)),1)
 def test_large_assessment_cannot_expand_context_without_bound(self):
  p={**self.seed,'hypothesis':'x'*4000}
  with self.assertRaises(ValueError):decode_assessment(self.assessment('FORM',p))
 def test_real_user_input_is_not_capability_evidence_but_valid_as_basis(self):
  old=self.establish('C');self.prepare('Replace assistant with archive.','t2')
  real_input=self.state.current_input_id
  payload={'operation':'revise','candidate_id':old['candidate_id'],'hypothesis':'Study verifiable archives',
    'quote':self.text,'input_ids':[real_input],'evidence_ids':[real_input]}
  with self.assertRaisesRegex(ValueError,'actual Capability Observation'):
   self.g.submit('t','t2','bad-native-call',payload)
  self.assertEqual(self.g.heads(self.state)[0].object_id,old['candidate_id'])
  # Independent CPU control: caller supplies a corrected explicit call; Host never rewrites/retries it.
  payload['evidence_ids']=[]
  receipt=self.g.submit('t','t2','corrected-native-call',payload)
  self.assertTrue(receipt['committed'])
  self.assertEqual(self.g.heads(self.state)[0].metadata['asserted_support_input_ids'],[real_input])
  self.assertIsNone(self.state.runtime_objects.active_goal())

 def test_goal_control_still_cannot_adopt(self):
  self.establish('C')
  with self.assertRaises(ValueError):self.g.control('t','/goal adopt anything')

if __name__=='__main__':unittest.main()
