"""Opt-in research final-envelope transport. No extraction from ordinary answers."""
import json
from copy import deepcopy
from harness.goal_integration import digest
from research.goal_hypothesis import GoalResearch, SCHEMA, DESCRIPTION
from research.longitudinal_dialogue import ScenarioApp

def unique_object(pairs):
    value={}
    for key,item in pairs:
        if key in value: raise ValueError('Duplicate JSON key')
        value[key]=item
    return value

def decode_proposal(text):
    value=json.loads(text,object_pairs_hook=unique_object)
    if (not isinstance(value,dict) or set(value)!={'answer','goal_proposal'}
            or not isinstance(value['answer'],str)
            or (value['goal_proposal'] is not None and not isinstance(value['goal_proposal'],dict))):
        raise ValueError('Expected negotiated answer/goal_proposal envelope')
    return value

class EnvelopeResearch(GoalResearch):
    source_kind='model_negotiated_final_proposal'
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.last_feedback=None
    def observe_final(self,thread_id,*,input_id,turn_id,model_event_id,text):
        state=self._state(thread_id)
        request=self._request(state,input_id)
        if (input_id!=state.current_input_id or not model_event_id
                or request.metadata['provenance'].get('turn_id')!=turn_id):
            raise ValueError('Final proposal is not bound to current registered turn')
        if not text.lstrip().startswith('{'):
            self._event(thread_id,'RESEARCH_FINAL_NO_PROPOSAL',{'turn_id':turn_id,
                'model_event_id':model_event_id,'reason':'ordinary_answer_not_extracted'})
            self.save(thread_id)
            return None
        try:
            value=decode_proposal(text)
            proposal=value['goal_proposal']
            self._event(thread_id,'RESEARCH_FINAL_ENVELOPE',{'input_id':input_id,'turn_id':turn_id,
                'model_event_id':model_event_id,'text_sha256':digest(text),'proposal':deepcopy(proposal)})
            if proposal is None:
                self.last_feedback={'committed':False,'reason':'explicit_null_proposal',
                    'model_event_id':model_event_id,'turn_id':turn_id}
                self.save(thread_id)
                return None
            receipt=self.submit(thread_id,turn_id,model_event_id,proposal)
        except (ValueError,KeyError,TypeError) as exc:
            self.last_feedback={'committed':False,'error':str(exc)[:220],
                'model_event_id':model_event_id,'turn_id':turn_id}
            self._event(thread_id,'RESEARCH_FINAL_REJECTED',deepcopy(self.last_feedback))
            raise
        self.last_feedback={**receipt,'model_event_id':model_event_id,'turn_id':turn_id,
            'host_context_status':'prepared_on_next_context_request',
            'model_context_status':'requires_successful_outbound_audit',
            'source_kind':self.source_kind,'not_a_native_tool_call':True}
        self._event(thread_id,'RESEARCH_FINAL_FEEDBACK',deepcopy(self.last_feedback))
        return next(r for r in self.records(state) if r.object_id==receipt['candidate_id'])
    def context(self,thread_id):
        blocks=super().context(thread_id)
        control=json.loads(blocks['uaea.goal_state']['value'])
        control['research_channel']='negotiated_final_envelope'
        control['instruction']=DESCRIPTION.replace('Do not call every turn.','Do not propose every turn.')+(
            ' In this isolated research session express an optional proposal ONLY in a complete final JSON '
            'object {"answer":"normal answer","goal_proposal":<proposal or null>}. '
            'The proposal uses the exact fields below. Native document tools retain their normal protocol. '
            'Plain answers create no candidate. No response_format/outputSchema or forced call is used. '
            'This final is validated after native Turn completion; its receipt can enter the next user Turn, '
            'not an extra model execution loop. Never claim submission before Host feedback.')
        control['final_proposal_schema']=SCHEMA
        control['last_final_feedback']=deepcopy(self.last_feedback)
        blocks['uaea.goal_state']['value']=json.dumps(control,ensure_ascii=False)
        return blocks

class EnvelopeApp(ScenarioApp):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        if self.goals.mode!='shadow': raise ValueError('EnvelopeApp is isolated shadow only')
        self.goals=EnvelopeResearch(self.semantic_state,self.events_path.with_name('goal-events.jsonl'))
