"""CPU-only evidence tampering and actual existing Goal validator checks."""
from pathlib import Path
import sys,unittest,tempfile,json,os
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from research.recover_goal_history import read_history,verify,restore,sha,clone_native_home,resume_recovered_app
H=Path(os.environ.get('UAEA_GOAL_HISTORY','/home/wqkan_wsl/uaea-n1x/research-records/goal-intent-lifecycle-20261112T031832Z/B'))

@unittest.skipUnless((H/'goal-events.jsonl').exists(),'External historical research fixture unavailable; set UAEA_GOAL_HISTORY')
class RecoveryTests(unittest.TestCase):
    def test_real_projection_and_exact_records(self):
        b=verify(read_history(H));self.assertEqual(len(b['versions']),2);self.assertEqual(len(b['inputs']),1);self.assertEqual(len(b['observations']),4);self.assertEqual(b['projection']['sequence'],4)
    def test_evidence_counterexamples(self):
        d=read_history(H)
        mutations=[
          ('source text',lambda z:z['turn-1-snapshot.json']['workflow_continuity']['request_continuity']['inputs'][0]['metadata'].__setitem__('text','invented')),
          ('uncovered policy',lambda z:z['turn-1-snapshot.json'].__setitem__('constraints',['unexported boundary'])),
          ('scope',lambda z:z['turn-1-snapshot.json'].__setitem__('semantic_scope_id','thread:other')),
          ('foreign owner',lambda z:z['turn-1-snapshot.json'].__setitem__('task_id','other')),
          ('missing timestamp',lambda z:z['turn-1-snapshot.json']['workflow_continuity']['request_continuity']['inputs'][0].pop('created_at')),
          ('missing source',lambda z:z['turn-1-snapshot.json']['workflow_continuity']['request_continuity'].__setitem__('inputs',[])),
          ('missing observation',lambda z:z['execution-contract.trajectory.jsonl'].__delitem__(1)),
          ('wrong parent',lambda z:next(x for x in z['goal-events.jsonl'] if x['event']=='RESEARCH_GOAL_VERSION')['payload']['record']['metadata'].__setitem__('previous_candidate_id','nonexistent')),
          ('changed candidate',lambda z:next(x for x in z['goal-events.jsonl'] if x['event']=='RESEARCH_GOAL_VERSION')['payload']['record']['metadata']['hypothesis'].__setitem__('hypothesis','different')),
          ('wrong head',lambda z:z['goal-research-state.json'].__setitem__('heads',[])),
          ('missing versions',lambda z:z['goal-research-state.json'].__setitem__('versions',[])),
          ('missing native calls',lambda z:z.__setitem__('app-server-events.jsonl',[x for x in z['app-server-events.jsonl'] if x.get('message',{}).get('method')!='item/tool/call'])),
          ('not committed',lambda z:next(x for x in z['goal-events.jsonl'] if x['event']=='RESEARCH_GOAL_VERSION')['payload']['receipt'].__setitem__('committed',False)),
        ]
        for label,change in mutations:
            with self.subTest(label=label):
                z=deepcopy(d);change(z)
                with self.assertRaises((ValueError,KeyError)):verify(z,verify_files=False)
        # Same Call ID with changed native args must not silently overwrite earlier identity.
        z=deepcopy(d)
        original=next(x for x in z['app-server-events.jsonl'] if x.get('message',{}).get('method')=='item/tool/call')
        conflict=deepcopy(original);conflict['message']['params']['arguments']={'different':True}
        z['app-server-events.jsonl'].insert(0,conflict)
        with self.assertRaises(ValueError):verify(z,verify_files=False)
        z=deepcopy(d);z['turn-1-snapshot.json']['workflow_continuity']['attempts'][0]['action']['arguments']={'different':True}
        with self.assertRaises(ValueError):verify(z,verify_files=False)
        z=deepcopy(d)
        cid=next(x['message']['params']['callId'] for x in z['app-server-events.jsonl'] if x.get('message',{}).get('method')=='item/tool/call' and x['message']['params']['tool']=='read_section')
        item=next(x['message']['params']['item'] for x in z['app-server-events.jsonl'] if x.get('message',{}).get('method')=='item/completed' and x['message']['params'].get('item',{}).get('id')==cid)
        receipt=json.loads(item['contentItems'][0]['text']);receipt['ok']=False;item['contentItems'][0]['text']=json.dumps(receipt)
        with self.assertRaises(ValueError):verify(z,verify_files=False)
        for mode in ['false','missing']:
            with self.subTest(framing=mode):
                z=deepcopy(d)
                for x in z['model-http-audit.jsonl']:
                    if x['event']=='transport_result':
                        if mode=='false':x['http_framing_complete']=False
                        else:x.pop('http_framing_complete',None)
                with self.assertRaises(ValueError):verify(z,verify_files=False)
    def test_step_observation_binding(self):
        d=read_history(H)
        valid=verify(d)
        self.assertEqual(len(valid['observation_bindings']),4)
        changes=[]
        z=deepcopy(d);a=z['turn-1-snapshot.json']['workflow_continuity']['attempts']
        a[0]['execution_observation_id'],a[1]['execution_observation_id']=a[1]['execution_observation_id'],a[0]['execution_observation_id']
        changes.append(('swapped Observation IDs',z))
        z=deepcopy(d);a=z['turn-1-snapshot.json']['workflow_continuity']['attempts']
        a[0]['action']['harness']['call_id']=a[1]['action']['harness']['call_id']
        a[0]['action']['arguments']=deepcopy(a[1]['action']['arguments'])
        a[0]['action']['execution_contract']=deepcopy(a[1]['action']['execution_contract'])
        changes.append(('different Call, otherwise matching parameters',z))
        z=deepcopy(d);z['turn-1-snapshot.json']['workflow_continuity']['attempts'][0]['action']['harness']['turn_id']='foreign-turn'
        changes.append(('Step Turn mismatch',z))
        z=deepcopy(d);z['turn-1-snapshot.json']['workflow_continuity']['attempts'][0]['action']['execution_contract']['compatibility_guard']['thread_id']='foreign-thread'
        changes.append(('Step execution Thread mismatch',z))
        z=deepcopy(d);next(x for x in z['execution-contract.trajectory.jsonl'] if x['event_type']=='OBSERVATION')['identity']['turn_id']='foreign-turn'
        changes.append(('Observation Turn mismatch',z))
        z=deepcopy(d);next(x for x in z['execution-contract.trajectory.jsonl'] if x['event_type']=='OBSERVATION')['identity']['thread_id']='foreign-thread'
        changes.append(('Observation Thread mismatch',z))
        z=deepcopy(d);next(x for x in z['execution-contract.trajectory.jsonl'] if x['event_type']=='OBSERVATION')['payload']['decision']['workflow_id']='foreign-workflow'
        changes.append(('Observation workflow mismatch',z))
        z=deepcopy(d);z['turn-1-snapshot.json']['workflow_continuity']['attempts'][0]['action']['harness']['input_id']='foreign-input'
        changes.append(('Step input ownership mismatch',z))
        for label,z in changes:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):verify(z,verify_files=False)
    def test_existing_idempotency_and_no_original_write(self):
        before=sha(H/'goal-events.jsonl')
        with tempfile.TemporaryDirectory(prefix='uaea-goal-recovery-') as temp:
            out=Path(temp)/'copy';b,s,g=restore(H,out)
            size=(out/'goal-events.jsonl').stat().st_size
            e=next(x['payload'] for x in read_history(H)['goal-events.jsonl'] if x['event']=='RESEARCH_GOAL_VERSION')
            p=e['record']['metadata']['submitted_proposal'];tid=e['record']['metadata']['thread_id']
            r=g.submit(tid,e['turn_id'],e['call_id'],p)
            self.assertEqual(r['candidate_id'],e['record']['object_id']);self.assertEqual(len(g.records(g._state(tid))),2);self.assertEqual(size,(out/'goal-events.jsonl').stat().st_size)
            changed=deepcopy(p);changed['hypothesis']+=' unsupported'
            with self.assertRaises(ValueError):g.submit(tid,e['turn_id'],e['call_id'],changed)
            self.assertEqual(size,(out/'goal-events.jsonl').stat().st_size)
        self.assertEqual(before,sha(H/'goal-events.jsonl'))
    def test_native_copy_identity_and_schema(self):
        tid=read_history(H)['turn-1-snapshot.json']['thread_id']
        with tempfile.TemporaryDirectory(prefix='uaea-native-recovery-') as temp:
            proof=clone_native_home(H,Path(temp)/'copy',tid)
            self.assertTrue(proof['sqlite_schema_unchanged'])
            self.assertEqual(proof['saved_dynamic_tools_source'],'rollout session_meta')
            self.assertTrue(any(t['name']=='goal_hypothesis' for t in proof['saved_dynamic_tools']))
    def test_old_external_rpc_cached_without_execution(self):
        from harness.semantic_state_adapter import HarnessSemanticStateAdapter
        from research.goal_hypothesis import GoalResearch,ProposalSemanticView
        bundle=verify(read_history(H))
        with tempfile.TemporaryDirectory(prefix='uaea-rpc-recovery-') as temp:
            out=Path(temp);journal=out/'goal-events.jsonl';journal.write_bytes((H/'goal-events.jsonl').read_bytes())
            class FakeApp:
                def __init__(self):
                    self.semantic_state=ProposalSemanticView(HarnessSemanticStateAdapter(require_registered_input=True))
                    self.goals=GoalResearch(self.semantic_state,journal)
                    self.events_path=out/'raw.jsonl';self._history_bridge=None;self.responses=[]
                def _send(self,r):self.responses.append(r)
                def _handle_tool_call(self,m):raise AssertionError('Historical external tool redispatched')
                def _publish_runtime_context_snapshot(self):pass
                def start(self,resume_thread_id):
                    self.thread_id=resume_thread_id
                    cid=next(k for k,v in bundle['calls'].items() if v['params']['tool']=='read_section')
                    self._handle_tool_call({'id':777,'params':deepcopy(bundle['calls'][cid]['params'])})
            app=FakeApp();before=sha(journal);resume_recovered_app(app,bundle)
            self.assertEqual(len(app.responses),1);self.assertEqual(sha(journal),before)
            self.assertFalse(json.loads((out/'recovery-rpc-cache.jsonl').read_text())['new_execution'])
            cid=next(k for k,v in bundle['calls'].items() if v['params']['tool']=='read_section')
            conflict=deepcopy(bundle['calls'][cid]['params']);conflict['arguments']={'bad':True}
            with self.assertRaises(ValueError):app._handle_tool_call({'id':778,'params':conflict})
    def test_refuse_overwrite(self):
        with self.assertRaises(ValueError):restore(H,H)
if __name__=='__main__':unittest.main()
