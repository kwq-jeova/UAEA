"""Research-only transport through existing Codex dynamic-tool loop."""
import json
from harness.goal_integration import digest
from harness.codex_dynamic_tools import HarnessDynamicToolAdapter
from research.longitudinal_dialogue import ScenarioApp
from research.goal_hypothesis import GoalResearch,ProposalSemanticView,TOOL,SCHEMA,DESCRIPTION

class ProposalAdapter(HarnessDynamicToolAdapter):
    def dynamic_tools(self):
        return super().dynamic_tools()+[{'type':'function','name':TOOL,'description':DESCRIPTION,'inputSchema':SCHEMA}]

class ProposalApp(ScenarioApp):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        if self.goals.mode!='shadow':raise ValueError('ProposalApp is isolated shadow only')
        self.semantic_state=ProposalSemanticView(self.semantic_state)
        self.goals=GoalResearch(self.semantic_state,self.events_path.with_name('goal-events.jsonl'))
    def _handle_tool_call(self,message):
        params=message.get('params',{})
        if params.get('tool')!=TOOL:return super()._handle_tool_call(message)
        call_id=params.get('callId','')
        try:
            if params.get('threadId')!=self.thread_id:raise ValueError('Foreign thread')
            receipt=self.goals.submit(self.thread_id,params.get('turnId'),call_id,params.get('arguments'))
        except (ValueError,KeyError,TypeError) as exc:
            receipt={'kind':'goal_hypothesis_receipt','ok':False,'committed':False,'error':str(exc)[:220],
                'is_execution_observation':False,'authorizes_action':False}
            self.goals._event(self.thread_id,'RESEARCH_GOAL_REJECTED',{'turn_id':params.get('turnId'),'call_id':call_id,
                'payload_sha256':digest(params.get('arguments')),
                'reason':str(exc)[:220],'source_kind':'model_semantic_tool_proposal'})
        else:
            # Publication is AFTER commit. Failure must not relabel the committed proposal as rejected.
            try:
                self._publish_runtime_context()
                receipt['host_context_status']='publication_call_succeeded'
            except Exception as exc:
                receipt['host_context_status']='publication_failed'
                receipt['publication_error']=type(exc).__name__
            receipt['model_context_status']='not_observed_here'
            self.goals._event(self.thread_id,'RESEARCH_GOAL_PUBLICATION',{
                'call_id':call_id,'turn_id':params.get('turnId'),'candidate_id':receipt['candidate_id'],
                'committed':True,'host_context_status':receipt['host_context_status'],
                'error_type':receipt.get('publication_error'),'model_context_status':'requires_outbound_audit'})
        self._send({'jsonrpc':'2.0','id':message.get('id'),'result':{'success':receipt['ok'],
            'contentItems':[{'type':'inputText','text':json.dumps(receipt,ensure_ascii=False)}]}})
