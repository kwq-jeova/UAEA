"""Isolated, optional semantic proposal channel. Never an execution capability."""
from dataclasses import asdict
from copy import deepcopy
from hashlib import sha256
import time
import json
from harness.goal_integration import GoalIntegration, digest
from harness.semantic_interpretation import request_record
from runtime.context_manager import GoalHypothesisRecord
from runtime.runtime_objects import RuntimeObjectRecord

TOOL = 'goal_hypothesis'
OPERATIONS = ['form','maintain','refine','revise','withdraw']
SCHEMA = {
 'type':'object','properties':{
  'operation':{'type':'string','enum':OPERATIONS},
  'candidate_id':{'type':['string','null'],'description':'Prior research candidate ID for updates; null only for form.'},
  'hypothesis':{'type':'string','maxLength':500,'description':'Tentative user direction, not a path or execution claim. Empty for maintain/withdraw.'},
  'quote':{'type':'string','minLength':1,'maxLength':300,'description':'Exact substring of CURRENT registered user request; provenance is not semantic proof.'},
  'input_ids':{'type':'array','items':{'type':'string'},'maxItems':6,'description':'Optional original user input IDs asserted as basis. Never model/summary IDs.'},
  'evidence_ids':{'type':'array','items':{'type':'string'},'maxItems':4,'description':'Optional actual ExecutionObservation IDs; a link does not establish semantic support.'}},
 'required':['operation','candidate_id','hypothesis','quote'],'additionalProperties':False}
DESCRIPTION = (
 'Optional non-authoritative Goal Hypothesis research channel, not an external action or authorization. '
 'Use only when retaining a useful continuing direction or changing/withdrawing a prior candidate. '
 'Multiple alternatives or no hypothesis are allowed. Do not call every turn. '
 'Separate user ends, temporary tasks, path/conditions and correction of your own interpretation. '
 'Do not use your earlier prose or compaction as user history. '
 'The receipt records a candidate only; continue the normal answer and real tools separately.')

def candidate_head(record):
    meta=record['metadata']
    return {'candidate_id':record['object_id'],'candidate_sha256':digest(record),
        'status':record['status'],'operation':meta['operation'],
        'hypothesis':meta['hypothesis']['hypothesis'],
        'basis_input_ids':meta['asserted_support_input_ids'],
        'previous_candidate_id':meta['previous_candidate_id']}

class ProposalSemanticView:
    """Filter this semantic control's native echoes; canonical raw journal remains intact."""
    def __init__(self,delegate):
        self.delegate=delegate;self.semantic_calls=set()
    def __getattr__(self,name):return getattr(self.delegate,name)
    def consume_raw_event(self,raw_event,**kwargs):
        message=raw_event.get('message',{})
        params=message.get('params',{});item=params.get('item',{})
        name=params.get('tool') or item.get('tool') or item.get('name')
        call=params.get('callId') or item.get('call_id') or (item.get('id') if item.get('type')=='dynamicToolCall' else None)
        if name==TOOL and call:self.semantic_calls.add(call)
        if call in self.semantic_calls:return []
        return self.delegate.consume_raw_event(raw_event,**kwargs)

class GoalResearch(GoalIntegration):
    source_kind = "model_semantic_tool_proposal"
    def __init__(self,semantic,path):
        super().__init__(semantic,path,mode='shadow',input_actor='test_driver',projection='optional')
        self.handled={}
    def control(self,*args,**kwargs):
        raise ValueError('Research candidates cannot adopt, complete or authorize')
    def records(self,state):
        return [r for r in state.runtime_objects.objects if r.object_type=='goal_hypothesis_candidate'
            and r.metadata.get('research_only') is True and r.metadata.get('thread_id')==state.thread_id]
    def heads(self,state):
        records=self.records(state)
        superseded={r.metadata['previous_candidate_id'] for r in records if r.metadata.get('previous_candidate_id')}
        return [r for r in records if r.object_id not in superseded]
    def original_inputs(self,state):
        valid=[]
        for r in state.runtime_objects.objects:
            if r.object_type!='workflow_request_input':continue
            checked=request_record(state.runtime_objects,r.owner,r.object_id)
            origin=checked.metadata.get('host_input_origin',{})
            if (origin.get('channel')=='registered_user_entry' and origin.get('input_id')==r.object_id
                and origin.get('raw_text_sha256')==r.metadata['raw_text_sha256']
                and r.metadata.get('provenance',{}).get('thread_id')==state.thread_id):
                valid.append(r)
        return valid
    def submit(self,thread_id,turn_id,call_id,payload):
        state=self._state(thread_id);request=self._request(state,state.current_input_id)
        if request.metadata['provenance'].get('turn_id')!=turn_id or not call_id:
            raise ValueError('Proposal is not bound to current registered native turn')
        fingerprint=digest(payload);identity=(thread_id,turn_id,call_id)
        if identity in self.handled:
            prior=self.handled[identity]
            if prior['payload_sha256']!=fingerprint:raise ValueError('Model call identity reused with changed proposal')
            return self._materialize(thread_id,prior)
        if (not isinstance(payload,dict) or set(payload)-set(SCHEMA['properties'])
            or not set(SCHEMA['required']).issubset(payload)):raise ValueError('Missing or unexpected proposal fields')
        payload=deepcopy(payload)
        operation=payload.get('operation');quote=payload.get('quote');hypothesis=payload.get('hypothesis');target=payload.get('candidate_id')
        if target is not None and not isinstance(target,str):raise ValueError('Invalid parent candidate ID')
        if operation not in OPERATIONS:raise ValueError('Unknown candidate operation')
        if not isinstance(quote,str) or not 0<len(quote)<=300 or quote not in request.metadata['text']:
            raise ValueError('Quote must come from CURRENT original input, not model/summary')
        if not isinstance(hypothesis,str) or len(hypothesis)>500:raise ValueError('Invalid hypothesis')
        heads={r.object_id:r for r in self.heads(state)}
        previous=None if target is None else heads.get(target)
        if operation=='form':
            if target is not None or not hypothesis.strip():raise ValueError('form needs new hypothesis and null candidate_id')
        elif previous is None or previous.status=='withdrawn':
            raise ValueError('Update needs current, same-thread, non-withdrawn candidate ID')
        if operation in ['maintain','withdraw']:
            original=previous.metadata['hypothesis']['hypothesis']
            if hypothesis and hypothesis!=original:raise ValueError('Use empty hypothesis for maintain/withdraw; use refine/revise to change it')
            hypothesis=original
        if operation in ['refine','revise'] and not hypothesis.strip():raise ValueError('Update needs a hypothesis')
        basis=payload.get('input_ids',[]);evidence=payload.get('evidence_ids',[])
        for values,limit in [(basis,6),(evidence,4)]:
            if not isinstance(values,list) or len(values)>limit or any(not isinstance(x,str) or not x or len(x)>200 for x in values):
                raise ValueError('Invalid source reference list')
        originals={r.object_id:r for r in self.original_inputs(state)}
        observations={s.execution_observation_id for s in state.runtime_objects.step_runs if s.execution_observation_id}
        if any(x not in originals for x in basis):raise ValueError('Basis must reference original same-thread user input, not candidate/summary')
        if any(x not in observations for x in evidence):raise ValueError('Evidence must reference actual Capability Observation')
        if len(self.records(state))>=32 or sum(k[:2]==identity[:2] for k in self.handled)>=2:
            raise ValueError('Bounded research candidate budget exhausted')
        candidate_id='goal-candidate:'+sha256(':'.join(identity).encode()).hexdigest()[:24]
        record=RuntimeObjectRecord(
            object_id=candidate_id,object_type='goal_hypothesis_candidate',owner=state.current_task_id,
            status='withdrawn' if operation=='withdraw' else 'candidate',
            source_object_ids=list(dict.fromkeys([state.current_input_id]+basis+evidence+([target] if target else []))),
            source_event_ids=[call_id],
            metadata={'research_only':True,'thread_id':thread_id,'operation':operation,'previous_candidate_id':target,
                'hypothesis':asdict(GoalHypothesisRecord(hypothesis,'unassessed','inferred')),'submitted_proposal':deepcopy(payload),
                'proposal':{'summary':hypothesis,'relation':operation,'target_goal_id':None,'quote':quote,'evidence_ids':evidence},
                'input_id':state.current_input_id,'turn_id':turn_id,'request_sha256':request.metadata['raw_text_sha256'],
                'basis_input_versions':{x:originals[x].metadata['raw_text_sha256'] for x in basis},
                'basis_input_status_at_proposal':{x:originals[x].status for x in basis},
                'asserted_support_input_ids':basis,'evidence_ids':evidence,'source_kind':self.source_kind,
                'authority_level':'interpretation','semantic_correctness':'not_established','quote_verified':True,
                'reference_validation':{'valid':True,'source_link_is_not_content_support':True},
                'new_independent_external_evidence':False,'adoption_eligible':False})
        receipt={'kind':'goal_hypothesis_receipt','ok':True,'candidate_id':candidate_id,'operation':operation,
            'status':record.status,'payload_sha256':fingerprint,'committed':True,'candidate_sha256':digest(record.to_dict()),'semantic_correctness':'not_established',
            'is_execution_observation':False,'authorizes_action':False,'active_goal_changed':False}
        self._event(thread_id,'RESEARCH_GOAL_VERSION',{'record':record.to_dict(),'receipt':receipt,'call_id':call_id,'turn_id':turn_id,'committed_at_utc':time.time()})
        state.runtime_objects.objects.append(record);self.handled[identity]=deepcopy(receipt)
        return self._materialize(thread_id,receipt)
    def _materialize(self,thread_id,receipt):
        result=deepcopy(receipt)
        try:
            self.save(thread_id)
            result['snapshot_status']='saved'
        except OSError as exc:
            # The append-only VERSION is the commit record; the snapshot is a materialized view.
            result['snapshot_status']='failed'
            result['snapshot_error']=type(exc).__name__
            self._event(thread_id,'RESEARCH_GOAL_SNAPSHOT_FAILED',{
                'candidate_id':receipt['candidate_id'],'committed':True,'reason':type(exc).__name__})
        return result
    def save(self,thread_id):
        state=self._state(thread_id)
        value={'scope':'Research candidates only, no adopted authority','heads':[r.to_dict() for r in self.heads(state)],
            'versions':[r.to_dict() for r in self.records(state)],'active_goal_id':state.runtime_objects.active_goal_id,
            'source_evidence':False,'memory_admission':'not_measured'}
        path=self.path.with_name('goal-research-state.json')
        temporary=path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2))
        temporary.replace(path)
    def observe_final(self,thread_id,**kwargs):
        self._event(thread_id,'RESEARCH_GOAL_TURN',{'input_id':kwargs['input_id'],'turn_id':kwargs['turn_id'],
            'proposal_calls':sum(key[:2]==(thread_id,kwargs['turn_id']) for key in self.handled),
            'plain_answer_is_not_candidate':True})
        self.save(thread_id)
        return None
    def context(self,thread_id):
        state=self._state(thread_id)
        inputs=self.original_inputs(state)[-8:];heads=self.heads(state)[-3:]
        dossier={'interpretations_only':True,'semantic_correctness':'not_established','is_source_evidence':False,
            'versions_immutable':True,'active_goal_adoption_disabled':True,
            'heads':[candidate_head(r.to_dict()) for r in heads],
            'input_index':[{'input_id':r.object_id,'request_status':r.status,'excerpt':r.metadata['text'][:80],'sha256':r.metadata['raw_text_sha256']} for r in inputs],
            'omitted_heads':max(0,len(self.heads(state))-3)}
        while len(json.dumps(dossier,ensure_ascii=False))>4200:
            if len(dossier['input_index'])>1:dossier['input_index'].pop(0)
            elif dossier['heads']:
                dossier['heads'].pop(0);dossier['omitted_heads']+=1
            else:raise ValueError('Research context cannot fit bounded budget')
        return {'uaea.goal_state':{'kind':'application','value':json.dumps({
            'schema':'uaea.goal_integration.v1','mode':'shadow','state_sha256':digest(self._goal_state(state)),
            'active_goal_id':'','decision_id':None,'goal_completion_established':False,'goal_is_not_authorization':True,
            'research_channel':TOOL,'instruction':DESCRIPTION},ensure_ascii=False)},
            'uaea.goal_hypotheses':{'kind':'untrusted','value':json.dumps(dossier,ensure_ascii=False)}}
