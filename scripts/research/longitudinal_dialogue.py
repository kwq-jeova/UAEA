"""Research driver only: existing InteractiveAppServer owns every model/tool loop."""
from pathlib import Path
import argparse,hashlib,json,sys,time,copy,os
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import memory.sqlite_store
import h3_harness_interactive_repl as repl
from h3_context_characterization import write_config,build_adapter
from harness.codex_dynamic_tools import HarnessDynamicToolAdapter
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def rows(path):return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
def check_guard(guard):
    if not (guard/'service/ready.json').exists():raise RuntimeError('Owned guarded service not ready')
    p=guard/'service/state.json'
    if p.exists() and json.loads(p.read_text()).get('done'):raise RuntimeError('Guard stopped; no retry')
def verify_source_lock(out):
    lock=out/'source-lock.json'
    if lock.exists():
        for name,expected in json.loads(lock.read_text()).items():
            path=ROOT/name
            if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('Source bundle changed: '+name)

def compact_existing_thread(app,folder,after_turn):
    before=len(rows(folder/'app-server-events.jsonl'))
    original=app.semantic_state.snapshot(app.thread_id)
    rid=app._next_id()
    reply=app._request({'jsonrpc':'2.0','id':rid,'method':'thread/compact/start','params':{'threadId':app.thread_id}},
        lambda x:x.get('id')==rid,timeout=30)
    if reply is None or reply.get('error'):raise RuntimeError('Compaction start failed; no retry')
    terminal=lambda x:x.get('method')=='turn/completed' and x.get('params',{}).get('threadId')==app.thread_id
    tail=[x['message'] for x in rows(folder/'app-server-events.jsonl')[before:] if 'message' in x]
    done=next((x for x in tail if terminal(x)),None)
    if done is None:done=app._wait_for(terminal,180)
    tail=[x['message'] for x in rows(folder/'app-server-events.jsonl')[before:] if 'message' in x]
    items=[x for x in tail if x.get('method')=='item/completed' and x.get('params',{}).get('item',{}).get('type')=='contextCompaction']
    if done is None or done['params']['turn'].get('status')!='completed' or not items:raise RuntimeError('Compaction terminal not confirmed')
    after=app.semantic_state.snapshot(app.thread_id)
    dump(folder/'compaction-control.json',{'after_script_turn':after_turn,'native_turn_id':done['params']['turn']['id'],'native_status':'completed','kind':'explicit controlled compaction, not natural pressure','before':original,'after':after})

class ScenarioApp(repl.InteractiveAppServer):
    def _publish_runtime_context_snapshot(self):
        super()._publish_runtime_context_snapshot()
        bridge=self._history_bridge
        if bridge is None or bridge._runtime_context is None:return
        state=copy.deepcopy(bridge._runtime_context)
        key='uaea.runtime_facts.filesystem'
        correct=repl.turn_context_payload(self._dynamic_tools,model=self.model,filesystem_root=str(self.workspace))[key]
        state['blocks'][key]=correct
        if self._last_turn_context is not None:self._last_turn_context[key]=correct
        bridge.set_runtime_context(state['blocks'],thread_id=self.thread_id,input_id=state['input_id'])
        with self.events_path.with_name('research-context-overrides.jsonl').open('a') as f:
            f.write(json.dumps({'input_id':state['input_id'],'field':key,'replacement':correct,'scope':'fixture root correction only; Sandbox unchanged'})+'\n')


def close_with_receipt(app,process,pgid):
    process=process or getattr(app,'process',None)
    if pgid is None and process is not None and process.poll() is None:
        try:pgid=os.getpgid(process.pid)
        except ProcessLookupError:pass
    app.close()
    group='unknown'
    if pgid is not None:
        try:os.killpg(pgid,0);group='present'
        except ProcessLookupError:group='absent'
        except PermissionError:pass
    return {'leader_pid':process.pid if process else None,
        'leader_returncode':process.poll() if process else None,'process_group':pgid,
        'process_group_state':group,'scope':'Observed native Harness process cleanup; not model-service ownership or Memory state.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--guard',type=Path,required=True);ap.add_argument('--goal-channel',choices=['legacy','sideband'],default='legacy')
    a=ap.parse_args();out=a.output.resolve();guard=a.guard.resolve()
    bindings=json.loads((out/'runtime-bindings.json').read_text()) if (out/'runtime-bindings.json').exists() else {}
    guard_root=Path(bindings.get('guard_root',str(ROOT.parent/'nemotron-bolt/records')))
    if not guard.is_relative_to(guard_root):raise ValueError('Unexpected guard root')
    for n,h in json.loads((out/'frozen.json').read_text()).items():
        p=Path(n) if Path(n).is_absolute() else out/n
        if hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise RuntimeError('Frozen input changed: '+n)
    verify_source_lock(out)
    cases={x['id']:x for x in json.loads((out/'scenarios.json').read_text())['cases']}
    check_guard(guard)
    dump(out/'service-reference.json',{'record':str(guard),'ready_observation':json.loads((guard/'service/ready.json').read_text()),
        'ready_sha256':hashlib.sha256((guard/'service/ready.json').read_bytes()).hexdigest(),
        'scope':'Referenced existing guarded service; Runner does not establish ownership, memory configuration or lifecycle safety by declaration.'})
    output_limit=json.loads((out/'protocol.json').read_text()).get('tool_output_chars',4000)
    if not isinstance(output_limit,int) or not 4000<=output_limit<=12000:raise ValueError('Research tool-output bound invalid')
    completed=[]
    for item in json.loads((out/'plan.json').read_text()):
        check_guard(guard);case=cases[item['case']];folder=out/item['id'];folder.mkdir(exist_ok=False)
        adapter0=build_adapter(folder/'adapter')
        binding=next(b for b in adapter0.bindings if b.capability=='document.read_section')
        adapter_type=HarnessDynamicToolAdapter
        if a.goal_channel=='sideband' and item['arm']=='goal_shadow':
            from research.goal_sideband import ProposalAdapter
            adapter_type=ProposalAdapter
        adapter=adapter_type(adapter0.registry,[binding],max_output_chars=output_limit)
        assert adapter.dynamic_tools()[0]['name']=='read_section'
        fixture=folder/'adapter/sandbox/ledger.md'
        fixture.write_text((out/case['fixture']).read_text() if case.get('fixture') else '# Ledger\n\n## Record\n\nRecord code: VELA-47Q2. This is one local sample, not a system-wide reliability assessment.\n')
        dump(folder/'fixture-manifest.json',{'path':str(fixture),'sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'missing_exists':(fixture.parent/'missing.md').exists(),'scope':'frozen historical researcher extract' if case.get('fixture') else 'synthetic local source, no public HTTP'})
        home=folder/'codex-home';write_config(home,'http://127.0.0.1:8003',32768,model='nemotron-bolt-n1x',n1x=True)
        app_type=ScenarioApp
        if a.goal_channel=='sideband' and item['arm']=='goal_shadow':
            from research.goal_sideband import ProposalApp
            app_type=ProposalApp
        app=app_type(codex=repl.DEFAULT_CODEX_BIN,codex_home=home,workspace=folder/'adapter/sandbox',base_url='http://127.0.0.1:8003',
            adapter=adapter,events_path=folder/'app-server-events.jsonl',stderr_path=folder/'stderr.log',turn_timeout=180,
            model='nemotron-bolt-n1x',reasoning_effort='none',execution_contract='shared',
            goal_mode='shadow' if item['arm']=='goal_shadow' else 'off',
            goal_projection='optional' if item['arm']=='goal_shadow' else 'none',input_actor='test_driver')
        turns=[];started=time.monotonic();process=None;pgid=None
        try:
            app.start()
            process=app.process
            if process is not None and process.poll() is None:pgid=os.getpgid(process.pid)
            for i,text in enumerate(case['turns'],1):
                check_guard(guard);verify_source_lock(out);start=time.monotonic();before=len(rows(folder/'app-server-events.jsonl'))
                app.run_turn(text)
                if app._pending_turn is not None:raise RuntimeError('Native Turn unresolved; no next input/retry')
                tail=rows(folder/'app-server-events.jsonl')[before:]
                terminal=[x['message'] for x in tail if x.get('message',{}).get('method')=='turn/completed']
                if not terminal or terminal[-1]['params']['turn'].get('status')!='completed':raise RuntimeError('No successful native terminal')
                snap=app.semantic_state.snapshot(app.thread_id)
                dump(folder/f'turn-{i}-snapshot.json',snap)
                if a.goal_channel=='sideband' and item['arm']=='goal_shadow':
                    dump(folder/f'goal-turn-{i}.json',{'heads':[r.to_dict() for r in app.goals.heads(app.goals._state(app.thread_id))]})
                assert snap['phase1_runtime_snapshot']['active_goal'] is None
                assert snap['evidence_provenance']['model_output_is_source_evidence'] is False
                turns.append({'turn':i,'user_text':text,'seconds':time.monotonic()-start,
                    'native_turn_id':terminal[-1]['params']['turn']['id'],
                    'host_workflow_completion':snap['workflow_continuity']['completion_established']})
                dump(folder/'turns.json',turns)
                check_guard(guard)
                print('TURN_COMPLETE',item['id'],i,flush=True)
                if case.get('compact_after')==i:
                    compact_existing_thread(app,folder,i)
                    print('COMPACTION_COMPLETE',item['id'],flush=True)
        except Exception as exc:
            dump(folder/'failure.json',{'type':type(exc).__name__,'detail':str(exc),'completed_turns':len(turns),'retry':False})
            raise
        finally:
            cleanup=close_with_receipt(app,process,pgid)
            dump(folder/'cleanup-observation.json',cleanup)
        if cleanup['leader_returncode'] is None or cleanup['process_group_state']!='absent':
            raise RuntimeError('Harness cleanup not confirmed; no next session')
        dump(folder/'result.json',{**item,'turns':len(turns),'seconds':time.monotonic()-started,
            'cleanup_observation':'cleanup-observation.json',
            'cleanup_sha256':hashlib.sha256((folder/'cleanup-observation.json').read_bytes()).hexdigest(),
            'authority_evidence':'See per-turn Host snapshots and Goal journal; absence of Memory admission was not independently measured.'})
        completed.append(item['id']);dump(out/'progress.json',completed)
        print('SESSION_COMPLETE',item['id'],flush=True)
if __name__=='__main__':main()
