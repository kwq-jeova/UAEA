"""Isolated A/B/C study: assessment is a journal view, never a submit command."""
from copy import deepcopy
import json
from harness.goal_integration import digest
from research.goal_envelope import unique_object
from research.goal_hypothesis import GoalResearch, SCHEMA, TOOL
from research.goal_sideband import ProposalApp

JUDGMENTS=['NO_CHANGE','FORM','REFINE','REVISE','WITHDRAW','UNKNOWN']
ASSESSMENT_SCHEMA={'type':'object','properties':{
 'judgment':{'type':'string','enum':JUDGMENTS},
 'proposal':{'anyOf':[SCHEMA,{'type':'null'}]},
 'submit_intent':{'type':'boolean'}},
 'required':['judgment','proposal','submit_intent'],'additionalProperties':False}

def decode_assessment(text):
 value=json.loads(text,object_pairs_hook=unique_object)
 if not isinstance(value,dict) or set(value)!={'answer','goal_assessment'} or not isinstance(value['answer'],str):
  raise ValueError('Expected negotiated answer/goal_assessment object')
 a=value['goal_assessment']
 if (not isinstance(a,dict) or set(a)!=set(ASSESSMENT_SCHEMA['required'])
     or a['judgment'] not in JUDGMENTS or type(a['submit_intent']) is not bool):
  raise ValueError('Invalid assessment fields')
 if len(json.dumps(a,ensure_ascii=False))>3500:raise ValueError('Assessment exceeds bounded research view')
 p=a['proposal']
 if p is not None and (not isinstance(p,dict) or set(p)-set(SCHEMA['properties'])
       or not set(SCHEMA['required']).issubset(p)):
  raise ValueError('Invalid assessment proposal fields')
 if a['judgment'] in ['NO_CHANGE','UNKNOWN'] and (p is not None or a['submit_intent']):
  raise ValueError('No-change/unknown assessment must have null proposal and no submit intent')
 if p is not None and p.get('operation')!=a['judgment'].lower():
  raise ValueError('Judgment/proposal operation mismatch')
 if a['submit_intent'] and p is None:
  raise ValueError('Submission intent without a proposal')
 return value

class CooperationResearch(GoalResearch):
 def __init__(self,*args,mechanism='A',**kwargs):
  super().__init__(*args,**kwargs)
  if mechanism not in ['A','B','C']:raise ValueError('Unknown mechanism')
  self.mechanism=mechanism;self.study_phase=False;self.last_assessment=None
 def submit(self,thread_id,turn_id,call_id,payload):
  # B denies new submissions after seed. Already-committed receipts retain base idempotency.
  if self.study_phase and self.mechanism=='B' and (thread_id,turn_id,call_id) not in self.handled:
   raise ValueError('Assessment-only research condition: candidate submission disabled after seed; normal document tools remain available')
  return super().submit(thread_id,turn_id,call_id,payload)
 def observe_final(self,thread_id,*,input_id,turn_id,model_event_id,text):
  state=self._state(thread_id);request=self._request(state,input_id)
  if (input_id!=state.current_input_id or not model_event_id
      or request.metadata['provenance'].get('turn_id')!=turn_id):
   raise ValueError('Assessment is not from current registered native Turn')
  super().observe_final(thread_id,input_id=input_id,turn_id=turn_id,model_event_id=model_event_id,text=text)
  if not self.study_phase:
   self.study_phase=True
   self._event(thread_id,'RESEARCH_COMPARISON_PHASE',{'turn_id':turn_id,
     'seed_candidate_ids':[r.object_id for r in self.heads(state)],
     'note':'Runner independently enforces exact real seed before another Turn; no Host creation'})
   return None
  if self.mechanism=='A':return None
  # Only a negotiated whole final object is an assessment. No prose/block extraction.
  if not text.lstrip().startswith('{'):
   self._event(thread_id,'RESEARCH_NO_ASSESSMENT',{'turn_id':turn_id,'model_event_id':model_event_id,
     'reason':'ordinary_answer_not_extracted'})
   return None
  try:
   value=decode_assessment(text);assessment=value['goal_assessment'];p=assessment['proposal']
   if p is not None:
    if (not isinstance(p['quote'],str) or not 0<len(p['quote'])<=300
        or p['quote'] not in request.metadata['text']):
     raise ValueError('Assessment quote is not a current original substring')
    if not isinstance(p['hypothesis'],str) or len(p['hypothesis'])>500:
     raise ValueError('Invalid assessment hypothesis')
    if p['candidate_id'] is not None and p['candidate_id'] not in {r.object_id for r in self.records(state)}:
     raise ValueError('Unknown same-thread assessment reference')
   records=[r for r in self.records(state) if r.metadata['turn_id']==turn_id]
   matches=[r.object_id for r in records if p is not None and r.metadata['submitted_proposal']==p]
   self.last_assessment={'assessment':deepcopy(assessment),'model_event_id':model_event_id,'turn_id':turn_id,
     'input_id':input_id,'raw_text_digest':digest(text),'source_kind':'model_final_assessment_only',
     'authority_level':'interpretation','semantic_correctness':'not_established',
     'candidate_created_by_assessment':False,'submissions_observed_this_turn':[r.object_id for r in records],
     'exact_matching_submission_ids':matches,'submission_relation':'matching_native_commit' if matches else 'not_observed_matching_commit',
     'reference_check_scope':'current input quote and known same-thread parent only; not full commit eligibility or semantic support'}
   self._event(thread_id,'RESEARCH_GOAL_ASSESSMENT',deepcopy(self.last_assessment))
  except (ValueError,KeyError,TypeError) as exc:
   self.last_assessment={'model_event_id':model_event_id,'turn_id':turn_id,
     'assessment_valid':False,'error':str(exc)[:220],'candidate_created_by_assessment':False}
   self._event(thread_id,'RESEARCH_ASSESSMENT_INVALID',deepcopy(self.last_assessment))
  return None
 def context(self,thread_id):
  blocks=super().context(thread_id)
  if not self.study_phase:return blocks  # All seed interfaces/context are identical.
  if self.mechanism=='A':return blocks
  control=json.loads(blocks['uaea.goal_state']['value'])
  control['research_mechanism']=self.mechanism
  control['assessment_schema']=ASSESSMENT_SCHEMA
  common=(
   'Optional research assessment: when useful, a COMPLETE final JSON object may have exactly '
   '{"answer":"normal reply","goal_assessment":{"judgment":"NO_CHANGE|FORM|REFINE|REVISE|WITHDRAW|UNKNOWN",'
   '"proposal":<normal Goal tool payload or null>,"submit_intent":false}}. '
   'No assessment is required every Turn. NO_CHANGE/UNKNOWN use null proposal and false intent. '
   'Assess user ends separately from tasks/path/conditions or correction of your own interpretation. '
   'An assessment, prose plan or submit_intent=true NEVER submits or changes a candidate. '
   'Only an accepted explicit native goal_hypothesis call is a submission. Report actual Host state, '
   'not a planned change. Native document calls keep their normal protocol. '
   'No response_format, outputSchema, extra model review or Host auto-call is used.')
  mode=(' In condition B, after the common real seed, candidate submission is disabled; '
    'you may express an assessment but must not claim it was saved. Ordinary document tools remain allowed.'
    if self.mechanism=='B' else
    ' In condition C, if you decide submission is warranted, explicitly use the existing goal_hypothesis tool. '
    'That one call already expresses a structured proposal and submission intent; no preliminary assessment call '
    'or second inference pass is required. Use its real receipt to distinguish accepted/rejected/unchanged '
    'state in the final assessment or normal answer. No forced submission, forced maintenance or retry is required.')
  control['instruction']=common+mode
  control['last_assessment_feedback']=None if self.last_assessment is None else {
    k:deepcopy(v) for k,v in self.last_assessment.items() if k in [
      'model_event_id','turn_id','input_id','raw_text_digest','candidate_created_by_assessment',
      'assessment_valid','submissions_observed_this_turn','exact_matching_submission_ids','submission_relation']}
  if self.last_assessment is not None:
   blocks['uaea.goal_assessment']={'kind':'untrusted','value':json.dumps({
      'derived_model_assessment':deepcopy(self.last_assessment),'is_source_evidence':False,
      'authority_level':'interpretation','is_submission_command':False},ensure_ascii=False)}
  control['assessment_is_not_adoption_or_execution']=True
  blocks['uaea.goal_state']['value']=json.dumps(control,ensure_ascii=False)
  return blocks

class CooperationApp(ProposalApp):
 def __init__(self,**kwargs):
  super().__init__(**kwargs)
  self.goals=CooperationResearch(self.semantic_state,self.events_path.with_name('goal-events.jsonl'))
