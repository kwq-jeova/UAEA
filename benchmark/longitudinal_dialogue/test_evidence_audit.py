"""Counterexamples for research evaluation, no model or semantic judge."""
from pathlib import Path
import copy,hashlib,importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/research'/('longitudinal_'+name+'.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
audit=load('audit')
class EvidenceAudit(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.source=self.root/'ledger.md';self.source.write_text('# File\n## Evidence\n123 USD\n')
  self.content='## Evidence\n123 USD'
  self.data={'path':str(self.source),'resolved_path':str(self.source),'line_start':2,'line_end':3,
   'content_excerpt':self.content,'content_hash':hashlib.sha256(self.content.encode()).hexdigest(),'source_hash':hashlib.sha256(self.source.read_bytes()).hexdigest()}
  self.manifest={'path':str(self.source),'sha256':self.data['source_hash']}
  self.observation={'event_type':'OBSERVATION','identity':{'thread_id':'h','turn_id':'t','item_id':'c'},
   'payload':{'capability_called':True,'execution_observation':{'observation_id':'o','capability':'document.read_section','status':'success','data':self.data}}}
  self.payload={'ok':True,'capability':'document.read_section','identity':{'call_id':'c','observation_id':'o'},'data':{**self.data,'content':self.content}}
  self.transports=[{'request_id':'req','http_status':200,'bytes_received':100,'bytes_forwarded':100,'upstream_eof':True,'http_framing_complete':True,'response_complete':True,'transport_error':None}]
  self.prepared=[{'sequence':2,'request_id':'req','request':{'input':[{'type':'function_call_output','call_id':'c','output':json.dumps(self.payload)}]}}]
 def check(self):
  return audit.document_delivery(self.prepared,[self.observation],self.manifest,True,self.transports)
 def test_actual_full_delivery(self):self.assertEqual(self.check()['status'],'PASS')
 def test_broken_pipe_does_not_prove_full_supply(self):
  self.transports[0]['transport_error']='BrokenPipeError'
  self.assertEqual(self.check()['status'],'FAIL')
 def test_legacy_200_bytes_stay_unknown(self):
  for k in ['response_complete','upstream_eof','bytes_forwarded']:self.transports[0].pop(k)
  self.assertEqual(self.check()['status'],'UNKNOWN')
 def test_partial_without_error_does_not_pass(self):
  self.transports[0]['response_complete']=False
  self.assertEqual(self.check()['status'],'FAIL')
 def _boundary_blank_line(self):
  self.source.write_text('## Evidence\n123 USD\n\n## Next\nOther\n')
  content='## Evidence\n123 USD\n'
  self.data.update(line_start=1,line_end=3,content_excerpt=content,
   content_hash=hashlib.sha256(content.encode()).hexdigest(),source_hash=hashlib.sha256(self.source.read_bytes()).hexdigest())
  self.manifest['sha256']=self.data['source_hash']
  self.payload['data']={**self.data,'content':content}
  self.prepared[0]['request']['input'][0]['output']=json.dumps(self.payload)
 def test_preserves_section_boundary_blank_line(self):
  self._boundary_blank_line()
  self.assertEqual(self.check()['status'],'PASS')
 def test_self_consistent_trimmed_observation_does_not_match_source(self):
  self._boundary_blank_line()
  stripped=self.data['content_excerpt'].rstrip('\n')
  self.data.update(content_excerpt=stripped,content_hash=hashlib.sha256(stripped.encode()).hexdigest())
  self.payload['data']={**self.data,'content':stripped}
  self.prepared[0]['request']['input'][0]['output']=json.dumps(self.payload)
  self.assertEqual(self.check()['status'],'FAIL')
 def test_correct_file_but_truncated_body(self):
  self.payload['data']['content']='[field truncated]';self.prepared[0]['request']['input'][0]['output']=json.dumps(self.payload)
  self.assertEqual(self.check()['status'],'FAIL')
 def test_self_consistent_wrong_body_hash(self):
  self.payload['data']['content']='fake';self.payload['data']['content_hash']=hashlib.sha256(b'fake').hexdigest()
  self.prepared[0]['request']['input'][0]['output']=json.dumps(self.payload)
  self.assertEqual(self.check()['status'],'FAIL')
 def test_other_call_cannot_establish_delivery(self):
  self.prepared[0]['request']['input'][0]['call_id']='wrong'
  self.assertEqual(self.check()['status'],'FAIL')
 def test_no_delivery_is_not_vacuous_pass(self):
  self.prepared=[];self.assertEqual(self.check()['status'],'FAIL')
 def test_no_required_observation_is_not_pass(self):
  self.assertEqual(audit.document_delivery([],[],self.manifest,True)['status'],'FAIL')
  self.assertEqual(audit.document_delivery([],[],None,False)['status'],'NOT_APPLICABLE')
 def test_missing_source_not_verified(self):
  self.source.unlink();self.assertEqual(self.check()['status'],'FAIL')
 def test_wrong_file_identity(self):
  self.data['resolved_path']=str(self.root/'other.md');self.assertEqual(self.check()['status'],'FAIL')
class NativeInputs(unittest.TestCase):
 def sample(self):
  return [{'method':'turn/started','params':{'turn':{'id':'t'}}},
   {'method':'item/completed','params':{'turnId':'t','item':{'type':'userMessage','content':[{'type':'text','text':'original'}]}}}]
 def test_exact_input_and_start(self):
  self.assertTrue(audit.native_turn_checks(['original'],[{'id':'t','status':'completed'}],self.sample())[0]['valid'])
 def test_runner_log_cannot_override_native_input(self):
  self.assertFalse(audit.native_turn_checks(['fake'],[{'id':'t','status':'completed'}],self.sample())[0]['valid'])
 def test_native_user_missing(self):
  self.assertFalse(audit.native_turn_checks(['original'],[{'id':'t','status':'completed'}],[])[0]['valid'])
class GoalBlocks(unittest.TestCase):
 def block(self):
  return '<uaea.goal_state>'+json.dumps({'schema':'uaea.goal_integration.v1','mode':'shadow','state_sha256':'a'*64,'goal_completion_established':False})+'</uaea.goal_state>'
 def check(self,item):
  return audit.goal_projection_checks([{'sequence':1,'request':{'input':[item]},
   'message_manifest':[{'field':'input','index':0,'role':'developer','context_blocks':[{'key':'uaea.goal_state'}]}]}],[],True)[0]['valid']
 def test_developer_structured_block(self):
  self.assertTrue(self.check({'role':'developer','content':[{'type':'input_text','text':self.block()}]}))
 def test_user_quoted_marker_is_not_projection(self):
  self.assertFalse(self.check({'role':'user','content':[{'type':'input_text','text':self.block()}]}))
 def test_plain_marker_is_not_projection(self):
  self.assertFalse(self.check({'role':'developer','content':[{'text':'mention uaea.goal_state'}]}))
 def test_bad_or_wrong_mode_json(self):
  self.assertFalse(self.check({'role':'developer','content':[{'text':self.block().replace('shadow','adopt')}]}))
  self.assertFalse(self.check({'role':'developer','content':[{'text':'<uaea.goal_state>bad</uaea.goal_state>'}]}))
 def test_missing_outbound_manifest_is_not_verified_projection(self):
  request={'sequence':1,'request':{'input':[{'role':'developer','content':[{'text':self.block()}]}]}}
  self.assertFalse(audit.goal_projection_checks([request],[],True)[0]['valid'])
 def test_goal_completed_claim_without_active_goal_rejected(self):
  self.assertFalse(self.check({'role':'developer','content':[{'text':self.block().replace('false','true')}]}))
 def test_duplicate_blocks(self):
  self.assertFalse(self.check({'role':'developer','content':[{'text':self.block()},{'text':self.block()}]}))
class Attempts(unittest.TestCase):
 def test_rejection_has_no_observation_but_counts(self):
  event={'event_type':'EXECUTION_DECISION','identity':{'thread_id':'h','turn_id':'t','item_id':'c'},'payload':{'allowed':False,'reason':'provider_fallback_not_authorized'}}
  result=audit.tool_attempts([],[event,event])
  self.assertEqual(len(result),1);self.assertEqual(result[0]['classification'],'rejected_before_capability')
 def test_native_unknown_tool_rejection_counts(self):
  event={'method':'item/completed','params':{'threadId':'h','turnId':'t','item':{'id':'c','type':'dynamicToolCall','status':'failed',
   'contentItems':[{'text':json.dumps({'ok':False,'data':{'capability_called':False}})}]}}}
  self.assertEqual(audit.tool_attempts([event],[])[0]['classification'],'rejected_before_capability')
 def test_harness_unsupported_tool_is_a_rejected_proposal(self):
  proposal={'method':'rawResponseItem/completed','params':{'threadId':'h','turnId':'t','item':{'type':'function_call','name':'unregistered','call_id':'c'}}}
  result={'method':'rawResponseItem/completed','params':{'threadId':'h','turnId':'t','item':{'type':'function_call_output','call_id':'c','output':'unsupported call: unregistered'}}}
  calls=audit.tool_attempts([proposal,result],[])
  self.assertEqual(calls[0]['classification'],'rejected_before_capability');self.assertEqual(calls[0]['rejection_layer'],'harness_tool_protocol')
 def test_tool_rpc_without_observation_is_retained_unknown(self):
  event={'method':'item/tool/call','params':{'threadId':'h','turnId':'t','callId':'c','tool':'bad_tool'}}
  result=audit.tool_attempts([event],[])
  self.assertEqual(len(result),1);self.assertEqual(result[0]['classification'],'unresolved_or_unobserved')
 def test_failed_execution_is_not_rejection(self):
  event={'event_type':'OBSERVATION','identity':{'thread_id':'h','turn_id':'t','item_id':'c'},'payload':{'capability_called':True,'execution_observation':{'status':'failed'}}}
  self.assertEqual(audit.tool_attempts([],[event])[0]['classification'],'execution_failure')
class RunnerCleanup(unittest.TestCase):
 def test_receipt_is_written_from_exit(self):
  runner=load('dialogue')
  proc=subprocess.Popen([sys.executable,'-c','pass'],start_new_session=True)
  class App:
   def close(self):proc.wait(timeout=5)
  receipt=runner.close_with_receipt(App(),proc,proc.pid)
  self.assertEqual(receipt['leader_returncode'],0);self.assertEqual(receipt['process_group_state'],'absent')
if __name__=='__main__':unittest.main()
