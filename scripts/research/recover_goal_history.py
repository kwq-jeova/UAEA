"""Isolated Goal research recovery. No model calls, tool execution, or adoption."""
from pathlib import Path
from copy import deepcopy
from dataclasses import fields
import json,hashlib,sqlite3,shutil,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"scripts")]
from harness.goal_integration import digest
from research.goal_hypothesis import GoalResearch,ProposalSemanticView,candidate_head
from research.goal_hypothesis_audit import record_binding,projection_binding
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from runtime.runtime_objects import RuntimeObjectRecord,WorkflowRunRecord,StepRunRecord
from runtime.semantic_observation import ExecutionObservation

def rows(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(test,message):
    if not test:raise ValueError(message)
def typed(cls,data):
    expected={f.name for f in fields(cls)}
    need(set(data)==expected,"Incomplete or unsupported recorded "+cls.__name__)
    return cls(**deepcopy(data))

def read_history(root):
    root=Path(root).resolve()
    names=['turn-1-snapshot.json','goal-research-state.json','goal-events.jsonl',
           'app-server-events.jsonl','execution-contract.trajectory.jsonl','model-http-audit.jsonl','turns.json']
    need(all((root/n).is_file() for n in names),"Missing historical evidence")
    d={n:(rows(root/n) if n.endswith('.jsonl') else json.loads((root/n).read_text())) for n in names}
    d['source_root']=str(root);d['source_hashes']={n:sha(root/n) for n in names}
    return d

def verify(d,verify_files=True):
    s=d['turn-1-snapshot.json'];thread=s['thread_id'];scope=s['semantic_scope_id'];task=s['task_id']
    need(not s['constraints'] and not s['execution_authority_item_ids'],"Checkpoint has additional effective constraints; policy recovery outside research scope")
    need(scope=='thread:'+thread,"Scope/thread mismatch")
    need(s['completed_turn_count']==s['turn_count']==1 and s['last_terminal_state']=='completed',"Only completed one-turn research checkpoints supported")
    ps=s['phase1_runtime_snapshot']
    need(ps['active_goal'] is None and ps['workflow_count']==1 and ps['artifact_count']==ps['planned_step_count']==0,"Unrecoverable authority/multiple-workflow checkpoint")
    inputs=s['workflow_continuity']['request_continuity']['inputs']
    originals={};input_records=[]
    native=[x['message'] for x in d['app-server-events.jsonl'] if 'message' in x]
    calls={}
    for m in native:
        if m.get('method')!='item/tool/call':continue
        call=m['params'];cid=call['callId']
        if cid in calls:
            need(all(call.get(k)==calls[cid].get(k) for k in ['threadId','turnId','tool','arguments']),'Conflicting repeated Native Call ID')
        calls[cid]=call
    for item in inputs:
        r={k:v for k,v in item.items() if k!='execution'};typed(RuntimeObjectRecord,r)
        m=r['metadata'];tid=m['provenance']['turn_id'];text=m['text'];h=hashlib.sha256(text.encode()).hexdigest()
        matching=[x for x in native if x.get('method')=='item/completed' and x['params'].get('item',{}).get('type')=='userMessage' and x['params'].get('threadId')==thread and x['params'].get('turnId')==tid]
        texts=[''.join(c.get('text','') for c in x['params']['item']['content'] if c.get('type')=='text') for x in matching]
        need(text in texts and m['raw_text_sha256']==h,"Original input/Native text version mismatch")
        need(r['owner']==task and m['input_id']==r['object_id'] and m['provenance']['thread_id']==thread,"Input identity/owner mismatch")
        need(m['host_input_origin']=={'channel':'registered_user_entry','input_id':r['object_id'],'raw_text_sha256':h},"Missing registered Host origin")
        originals[r['object_id']]={'text':text,'sha256':h,'owner':task,'native_turn_id':tid}
        input_records.append(r)
    need(s['current_input_id'] in originals,"Current input unavailable")
    steps=s['workflow_continuity']['attempts'];need(len(steps)==ps['step_count'],"Historical steps incomplete")
    obs=[x for x in d['execution-contract.trajectory.jsonl'] if x['event_type']=='OBSERVATION']
    observations={};observation_bindings={}
    decisions={x['identity']['item_id']:x for x in d['execution-contract.trajectory.jsonl'] if x['event_type']=='EXECUTION_DECISION'}
    for x in obs:
        o=x['payload']['execution_observation'];oid=o['observation_id'];cid=x['identity']['item_id']
        need(oid not in observations and cid in calls,"Observation/call identity mismatch")
        need(x['identity']['thread_id']==thread and calls[cid]['threadId']==thread,"Foreign observation thread")
        turn=x['identity']['turn_id'];decision=x['payload']['decision']
        need(turn==calls[cid]['turnId'],"Observation/Native Turn mismatch")
        need(cid in decisions and decision==decisions[cid]['payload'],"Observation decision not bound to execution trace")
        need(decisions[cid]['identity']['thread_id']==thread and decisions[cid]['identity']['turn_id']==turn,"Execution decision scope mismatch")
        need(decision['action_id']==cid and decision['workflow_id']==task and decision['input_id'] in originals,"Observation execution ownership mismatch")
        need(originals[decision['input_id']]['native_turn_id']==turn,"Observation original input Turn mismatch")
        observation_bindings[oid]={'call_id':cid,'turn_id':turn,'thread_id':thread,'workflow_id':decision['workflow_id'],'input_id':decision['input_id'],'decision':deepcopy(decision)}
        item=next((m['params']['item'] for m in native if m.get('method')=='item/completed' and m['params'].get('item',{}).get('id')==cid),None)
        need(item is not None,"Observation Native receipt absent")
        result=json.loads(item['contentItems'][0]['text'])
        need(result['identity']['observation_id']==oid and result['data']['source_hash']==o['data']['source_hash'],"Observation receipt/version mismatch")
        need(all(result['identity'].get(k)==v for k,v in {'call_id':cid,'turn_id':turn,'thread_id':thread}.items()),"Observation receipt identity mismatch")
        need(hashlib.sha256(result['data']['content'].encode()).hexdigest()==result['data']['content_hash'],"Body hash mismatch")
        if verify_files:need(sha(o['data']['resolved_path'])==o['data']['source_hash'],"Historical source content changed")
        observations[oid]=deepcopy(o)
    for st in steps:
        typed(StepRunRecord,st)
        need(st['workflow_id']==task and st['execution_observation_id'] in observations,"Step observation missing")
        cid=st['action']['harness']['call_id']
        need(cid in calls,'Step call missing')
        binding=observation_bindings[st['execution_observation_id']];h=st['action']['harness']
        need(cid==binding['call_id'],'Step/Observation Call ID mismatch')
        need(h['turn_id']==binding['turn_id'] and calls[cid]['turnId']==binding['turn_id'],'Step/Observation Turn mismatch')
        need(calls[cid]['threadId']==binding['thread_id']==thread,'Step/Observation Thread mismatch')
        need(st['workflow_id']==binding['workflow_id'] and h['input_id']==binding['input_id'],'Step/Observation execution ownership mismatch')
        need(st['action']['execution_contract']==binding['decision'],'Step/Observation execution decision mismatch')
        need(st['action']['arguments']==calls[cid]['arguments'],'Step/Native arguments conflict')
        need(st['action']['harness']['input_id'] in originals,'Step original input missing')
    need(set(x['execution_observation_id'] for x in steps)==set(observations),"Unbound historical observations")
    wf=ps['active_workflow'];typed(WorkflowRunRecord,wf)
    need(wf['workflow_id']==task and set(wf['step_ids'])==set(x['step_id'] for x in steps),"Workflow identity mismatch")
    journal=d['goal-events.jsonl'];events=[x['payload'] for x in journal if x['event']=='RESEARCH_GOAL_VERSION']
    seen={};handled={};commits={}
    for e in events:
        r=e['record'];m=r['metadata'];cid=e['call_id']
        need(record_binding(e,calls.get(cid),originals,seen,set(observations)),"Goal commit/source/Native binding failed")
        typed(RuntimeObjectRecord,r)
        need(m['thread_id']==thread and r['owner']==task,"Foreign Goal scope")
        key=(thread,e['turn_id'],cid)
        need(key not in handled,"Duplicate commit identity")
        handled[key]=deepcopy(e['receipt']);seen[r['object_id']]=deepcopy(r);commits[r['object_id']]=e['committed_at_utc']
        matching=[it for it in native if it.get('method')=='item/completed' and it['params'].get('item',{}).get('id')==cid]
        need(bool(matching),"Goal receipt not in Native history")
        nr=json.loads(matching[-1]['params']['item']['contentItems'][0]['text'])
        need(all(nr.get(k)==e['receipt'][k] for k in ['candidate_id','operation','committed','candidate_sha256','payload_sha256','ok']),"Native Goal receipt mismatch")
    gs=d['goal-research-state.json'];sup={r['metadata']['previous_candidate_id'] for r in seen.values()}
    heads=[r for k,r in seen.items() if k not in sup]
    need(gs['versions']==list(seen.values()) and gs['heads']==heads,"Snapshot versions/heads conflict")
    http=d['model-http-audit.jsonl'];pre=[x for x in http if x['event']=='request_prepared'];trans=[x for x in http if x['event']=='transport_result']
    checks,appear=projection_binding(pre,seen,commits,trans)
    expected=[candidate_head(r) for r in heads];matched=None
    for q,c in zip(pre,checks):
        if not(c['valid'] and c['transport']['status']=='PASS' and c['candidate_ids_in_untrusted_view']==[h['candidate_id'] for h in expected]):continue
        for part in q['request'].get('input',[]):
            for content in part.get('content',[]):
                text=content.get('text','');tag='<external_uaea.goal_hypotheses>'
                if text.startswith(tag):
                    view=json.loads(text[len(tag):].split('</external_uaea.goal_hypotheses>')[0])
                    need(view['heads']==expected,"Wrong historical projected head")
                    matched={'sequence':q['sequence'],'view':view,'request_id':q['request_id']}
    need(matched is not None and all(appear[k] for k in seen),"No fully delivered historical Goal projection")
    # Record real prior responses for RPC idempotency; never redispatch external calls.
    rpc={}
    for cid,call in calls.items():
        it=next((m['params']['item'] for m in native if m.get('method')=='item/completed' and m['params'].get('item',{}).get('id')==cid),None)
        need(it is not None,"Completed call result missing")
        need(it['status']=='completed' and json.loads(it['contentItems'][0]['text']).get('ok') is True,"Failed/partial historical RPC recovery outside supported profile")
        rpc[cid]={'params':deepcopy(call),'result':{'success':it['status']=='completed','contentItems':deepcopy(it['contentItems'])}}
    return {'snapshot':deepcopy(s),'inputs':input_records,'versions':list(seen.values()),'heads':heads,
        'handled':[{'identity':list(k),'receipt':v} for k,v in handled.items()],
        'observations':observations,'observation_bindings':observation_bindings,'calls':rpc,'projection':matched,
        'source_root':d['source_root'],'source_hashes':d['source_hashes'],
        'coverage':'Complete Goal/input/recorded-workflow-step closure; not arbitrary Runtime checkpoint/replay',
        'not_recovered':['opaque model-output Runtime objects','old ProjectionRecord cache','planner caches not exported'],
        'original_history_unchanged':True}

def hydrate(semantic,goals,bundle):
    s=bundle['snapshot'];state=semantic._state_for(s['thread_id'])
    need(not state.runtime_objects.objects,"Recovery destination must be empty")
    store=state.runtime_objects
    store.objects=[typed(RuntimeObjectRecord,r) for r in bundle['inputs']+s['semantic_items']+bundle['versions']]
    store.workflow_runs=[typed(WorkflowRunRecord,s['phase1_runtime_snapshot']['active_workflow'])]
    store.active_workflow_id=s['task_id'];store.step_runs=[typed(StepRunRecord,r) for r in s['workflow_continuity']['attempts']]
    for k in ['semantic_scope_id','thread_id','topic','source_preferences','constraints','semantic_constraint_provenance','task_evolution','references','open_questions','turn_count','completed_turn_count','last_turn_id','last_user_input','last_agent_output','last_tool_call','semantic_observations','projection_ids','last_projection','last_terminal_state','last_error','action_decisions','ownership_binding','current_input_id']:
        setattr(state,k,deepcopy(s[k]))
    state.current_task_id=s['task_id'];state.last_relation=deepcopy(s['turn_relation'])
    state.last_projection_manifest=deepcopy(s['projection_manifest'])
    state.turn_receipts=deepcopy(s['workflow_continuity']['turn_receipts'])
    state.input_turn_ids={v['metadata']['provenance']['turn_id'] for v in bundle['inputs']}
    state.last_execution_observation=ExecutionObservation(**deepcopy(s['last_execution_observation']))
    rel=s['phase1_context']['turn_relation'];state.context_manager.set_turn_relation(rel['relation'],target_ref=rel['target_ref'],reason=rel['reason'])
    goals.handled={tuple(r['identity']):deepcopy(r['receipt']) for r in bundle['handled']}
    view=json.loads(goals.context(s['thread_id'])['uaea.goal_hypotheses']['value'])
    need(view==bundle['projection']['view'],"Regenerated Goal projection differs from real historical request")
    need([r.to_dict() for r in goals.heads(state)]==bundle['heads'],"Recovered current head differs")
    semantic.semantic_calls.update(k[2] for k in goals.handled)
    return state

def restore(root,out):
    root=Path(root).resolve();out=Path(out).resolve()
    need(not out.exists() and not out.is_relative_to(root),"Recovery must use a fresh independent destination")
    bundle=verify(read_history(root));out.mkdir(parents=True)
    shutil.copy2(root/'goal-events.jsonl',out/'goal-events.jsonl')
    semantic=ProposalSemanticView(HarnessSemanticStateAdapter(require_registered_input=True))
    goals=GoalResearch(semantic,out/'goal-events.jsonl');hydrate(semantic,goals,bundle);goals.save(bundle['snapshot']['thread_id'])
    (out/'recovered-bundle.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2))
    return bundle,semantic,goals

def clone_native_home(root,out,thread):
    root=Path(root).resolve();out=Path(out).resolve()
    need(not out.exists() and not out.is_relative_to(root),"Native copy destination must be new and outside original")
    original=root/'codex-home'
    before={str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()}
    need(not any(p.is_symlink() for p in original.rglob('*')),'Native home symlinks need separate review')
    shutil.copytree(original,out)
    db=out/'state_5.sqlite';con=sqlite3.connect(db)
    schema=con.execute("select type,name,sql from sqlite_master order by type,name").fetchall()
    row=con.execute('select rollout_path from threads where id=?',(thread,)).fetchone();need(row is not None,"Native Thread missing")
    old=Path(row[0]);need(old.is_relative_to(original),"Native rollout not under source home")
    new=out/old.relative_to(original);need(new.is_file() and sha(new)==sha(old),"Native rollout copy differs")
    con.execute('update threads set rollout_path=? where id=?',(str(new),thread));con.commit()
    need(schema==con.execute("select type,name,sql from sqlite_master order by type,name").fetchall(),"SQLite schema changed")
    tools=con.execute('select * from thread_dynamic_tools where thread_id=?',(thread,)).fetchall();con.close()
    meta=next((r['payload'] for r in rows(new) if r.get('type')=='session_meta'),None)
    need(meta is not None and meta.get('id')==thread,'Native session_meta Thread mismatch')
    saved_tools=meta.get('dynamic_tools',[])
    need(any(t.get('name')=='goal_hypothesis' for t in saved_tools),'Saved Native Goal tool missing from rollout')
    schema_hash=hashlib.sha256(json.dumps(schema,sort_keys=True).encode()).hexdigest()
    need(before=={str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()},"Original Native home modified")
    return {'thread_id':thread,'rollout_original':str(old),'rollout_copy':str(new),'rollout_sha256':sha(old),
       'source_files':before,'sqlite_schema_unchanged':True,'sqlite_schema_sha256':schema_hash,'saved_dynamic_tools_source':'rollout session_meta','saved_dynamic_tools':saved_tools,'dynamic_tools_SQLite_rows':len(tools),'relocated_only_copy_rollout_pointer':True}


def resume_recovered_app(app,bundle):
    """Resume the copied Native history, then attach proven Host Goal closure.
    No external call is dispatched while loading history; cached receipts are
    original completed results, not newly observed execution.
    """
    thread=bundle['snapshot']['thread_id'];prior_calls=bundle['calls'];loading=True
    regular=app._handle_tool_call
    def guarded(message):
        params=message.get('params',{});cid=params.get('callId')
        if cid in prior_calls:
            old=prior_calls[cid]
            need(all(params.get(k)==old['params'].get(k) for k in ['threadId','turnId','tool','arguments']),"Historical Call ID conflict; no redispatch")
            log=app.events_path.with_name('recovery-rpc-cache.jsonl')
            with log.open('a') as f:f.write(json.dumps({'call_id':cid,'historical_receipt_reused':True,'new_execution':False})+'\n')
            app._send({'jsonrpc':'2.0','id':message['id'],'result':deepcopy(old['result'])})
            return
        need(not loading,"New tool request during Native resume; model not admitted")
        return regular(message)
    app._handle_tool_call=guarded
    consume=app.semantic_state.consume_raw_event
    app.semantic_state.consume_raw_event=lambda *a,**k:[]
    try:app.start(resume_thread_id=thread)
    finally:app.semantic_state.consume_raw_event=consume
    need(app.thread_id==thread,"Native resumed another Thread")
    audit=app.events_path.with_name('model-http-audit.jsonl')
    need(not audit.exists() or not any(x.get('event')=='request_prepared' for x in rows(audit)),"Native resume unexpectedly requested a model")
    hydrate(app.semantic_state,app.goals,bundle);app.goals.save(thread)
    loading=False
    # Record cache incompleteness explicitly, without inventing model-output objects.
    publish=app._publish_runtime_context_snapshot
    def restored_publish():
        publish()
        bridge=app._history_bridge
        if bridge is None or bridge._runtime_context is None:return
        state=deepcopy(bridge._runtime_context)
        state['blocks']['uaea.research_recovery']={'kind':'application','value':json.dumps({
          'scope':bundle['coverage'],'original_thread_id':thread,
          'history_is_not_new_input_or_execution':True,'goal_versions_are_historical_commits':True,
          'unrestored_caches':bundle['not_recovered'],
          'original_model_output_count':bundle['snapshot']['evidence_provenance']['model_outputs'],
          'current_cache_counts_are_not_complete_historical_counts':True},ensure_ascii=False)}
        bridge.set_runtime_context(state['blocks'],thread_id=thread,input_id=state['input_id'])
    app._publish_runtime_context_snapshot=restored_publish
    return app

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--history',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--clone-native',action='store_true')
    a=p.parse_args();bundle,semantic,goals=restore(a.history,a.output)
    if a.clone_native:
        proof=clone_native_home(a.history,a.output/'codex-home',bundle['snapshot']['thread_id'])
        (a.output/'native-copy.json').write_text(json.dumps(proof,indent=2))
    print(json.dumps({'thread':bundle['snapshot']['thread_id'],'versions':len(bundle['versions']),'inputs':len(bundle['inputs']),'observations':len(bundle['observations']),'projection_matches_successful_request':bundle['projection']['sequence'],'scope':bundle['coverage']}))
if __name__=='__main__':main()
