"""Offline structural and literal-source evaluator. No semantic judge/model."""
from pathlib import Path
import argparse,json,hashlib,re,collections
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
def grounded_literal(answer,observations):
    # A true successful document Observation is required; text/candidate alone cannot prove IO.
    return 'VELA-47Q2' in answer and 'ledger.md' in answer and any(
        x.get('event_type')=='OBSERVATION'
        and x.get('payload',{}).get('decision',{}).get('capability')=='document.read_section'
        and x.get('payload',{}).get('decision',{}).get('effective_parameters',{}).get('path','').split('/')[-1]=='ledger.md'
        and x.get('payload',{}).get('execution_observation',{}).get('status')=='success'
        and 'VELA-47Q2' in json.dumps(x.get('payload',{}).get('execution_observation',{}).get('data',{}))
        for x in observations)
def document_hash_check(data,manifest):
    source=Path(manifest['path'])
    if not source.exists():return {'section_hash_matches':None,'file_version_matches':None,'scope':'fixture unavailable for replay'}
    raw=source.read_bytes();text=raw.decode()
    section='\n'.join(text.splitlines()[data['line_start']-1:data['line_end']]).strip()
    excerpt=data['content_excerpt']
    return {'section_hash_matches':hashlib.sha256(section.encode()).hexdigest()==data.get('content_hash'),
        'file_version_matches':hashlib.sha256(raw).hexdigest()==data.get('source_hash')==manifest['sha256'],
        'excerpt_prefix_matches':section.startswith(excerpt),'excerpt_is_full_section':len(excerpt)==len(section),
        'scope':'source bytes integrity, not proof the model saw full content'}

def turn_integrity(expected,turn_log,terminals,snapshots,result):
    errors=[]
    n=len(expected)
    if n<1:errors.append('empty_expected_script')
    if not (len(turn_log)==len(terminals)==len(snapshots)==n):errors.append('expected_turn_count_mismatch')
    ids=[x.get('id') for x in terminals]
    if len(set(ids))!=len(ids) or any(not x for x in ids):errors.append('duplicate_or_missing_native_turn_id')
    if result.get('turns')!=n:errors.append('result_turn_count_mismatch')
    if [x.get('turn') for x in turn_log]!=list(range(1,n+1)):errors.append('script_turn_sequence_mismatch')
    if [x.get('user_text') for x in turn_log]!=expected:errors.append('script_input_mismatch')
    if [x.get('native_turn_id') for x in turn_log]!=ids:errors.append('native_turn_binding_mismatch')
    if any(x.get('status')!='completed' for x in terminals):errors.append('native_terminal_not_completed')
    if any(s.get('last_turn_id')!=i for s,i in zip(snapshots,ids)):errors.append('snapshot_turn_binding_mismatch')
    return errors


def goal_projection_checks(prepared,decisions,expected,control_interval=None):
    deferred={x.get('provider_request_sequence') for x in decisions
        if x.get('kind')=='host_context_deferred_for_compaction' and x.get('source')=='published_host_snapshot'}
    checks=[]
    for event in prepared:
        blocks=[]
        for index,item in enumerate(event['request'].get('input',[])):
            if item.get('role')!='developer':continue
            for part in item.get('content',[]):
                if not isinstance(part,dict):continue
                text=part.get('text','')
                if not isinstance(text,str) or not text.startswith('<uaea.goal_state>'):continue
                match=re.fullmatch(r'<uaea.goal_state>(.*)</uaea.goal_state>',text,re.S)
                try:body=json.loads(match.group(1)) if match else None
                except ValueError:body=None
                valid=bool(isinstance(body,dict) and body.get('schema')=='uaea.goal_integration.v1'
                    and body.get('mode')=='shadow' and body.get('goal_completion_established') is False
                    and body.get('active_goal_id') in [None,''] and body.get('decision_id') is None and re.fullmatch('[0-9a-f]{64}',str(body.get('state_sha256',''))))
                manifest=event.get('message_manifest')
                if not isinstance(manifest,list):valid=False
                else:
                    valid=valid and any(x.get('field')=='input' and x.get('index')==index
                        and x.get('role')=='developer' and any(b.get('key')=='uaea.goal_state' for b in x.get('context_blocks',[]) if isinstance(b,dict)) for x in manifest)
                blocks.append({'input_index':index,'valid':valid})
        instant=event.get('utc')
        native_control=bool(control_interval and isinstance(instant,(float,int))
            and control_interval[0]<=instant*1000<=control_interval[1] and event.get('sequence') in deferred)
        valid=native_control or (len(blocks)==1 and blocks[0]['valid'] if expected else not blocks)
        checks.append({'request_sequence':event['sequence'],'goal_projection_present':bool(blocks),
            'scope':'confirmed_native_compaction' if native_control else 'normal_model_request',
            'blocks':blocks,'valid':bool(valid)})
    return checks

def native_turn_checks(expected,terminals,messages):
    checks=[]
    for index,terminal in enumerate(terminals):
        turn=terminal.get('id')
        users=[x['params']['item'] for x in messages if x.get('method')=='item/completed'
            and x.get('params',{}).get('turnId')==turn and x['params'].get('item',{}).get('type')=='userMessage']
        texts=[''.join(y.get('text','') for y in x.get('content',[]) if y.get('type')=='text') for x in users]
        started=sum(x.get('method')=='turn/started' and x.get('params',{}).get('turn',{}).get('id')==turn for x in messages)
        checks.append({'turn_id':turn,'native_user_count':len(users),'started_count':started,
            'valid':index<len(expected) and texts==[expected[index]] and started==1 and terminal.get('status')=='completed'})
    return checks

def tool_attempts(messages,contract):
    attempts={}
    def get(identity):
        key=tuple(identity.get(k,'') for k in ['thread_id','turn_id','item_id'])
        return attempts.setdefault(key,{'thread_id':key[0],'turn_id':key[1],'call_id':key[2],
            'native':False,'decision':None,'observation':None,'native_status':None})
    for event in contract:
        if event.get('event_type') not in ['EXECUTION_DECISION','OBSERVATION']:continue
        entry=get(event['identity']);payload=event.get('payload',{})
        if event['event_type']=='EXECUTION_DECISION':entry['decision']=payload
        else:entry['observation']=payload
    for event in messages:
        params=event.get('params',{});item=params.get('item',{})
        if event.get('method')=='item/tool/call':
            entry=get({'thread_id':params.get('threadId',''),'turn_id':params.get('turnId',''),'item_id':params.get('callId','')})
            entry['native']=True;entry['tool']=params.get('tool');entry['tool_rpc_observed']=True
        if event.get('method')=='rawResponseItem/completed' and item.get('type')=='function_call' and item.get('call_id'):
            entry=get({'thread_id':params.get('threadId',''),'turn_id':params.get('turnId',''),'item_id':item['call_id']})
            entry['model_proposal_observed']=True;entry['tool']=item.get('name')
        if event.get('method')=='rawResponseItem/completed' and item.get('type')=='function_call_output' and item.get('call_id'):
            entry=get({'thread_id':params.get('threadId',''),'turn_id':params.get('turnId',''),'item_id':item['call_id']})
            entry['harness_protocol_output']=item.get('output')
        if item.get('type')!='dynamicToolCall' or event.get('method') not in ['item/started','item/completed']:continue
        entry=get({'thread_id':params.get('threadId',''),'turn_id':params.get('turnId',''),'item_id':item.get('id','')})
        entry['native']=True;entry['tool']=item.get('tool')
        if event['method']=='item/completed':
            entry['native_status']=item.get('status')
            for content in item.get('contentItems',[]):
                try:entry['native_result']=json.loads(content.get('text',''))
                except (ValueError,TypeError):pass
    for entry in attempts.values():
        decision=entry.get('decision') or {};observation=(entry.get('observation') or {}).get('execution_observation',{})
        native=entry.get('native_result') or {}
        unsupported=entry.get('harness_protocol_output')=='unsupported call: '+str(entry.get('tool'))
        entry['rejection_layer']=('harness_tool_protocol' if unsupported else 'shared_decision' if decision.get('allowed') is False else None)
        rejected=(unsupported or decision.get('allowed') is False or native.get('status')=='rejected'
            or (native.get('ok') is False and native.get('data',{}).get('capability_called') is False))
        entry['classification']=('rejected_before_capability' if rejected and not observation else
            'execution_success' if observation.get('status')=='success' else
            'execution_failure' if observation else 'unresolved_or_unobserved')
        entry['capability_called']=(entry.get('observation') or {}).get('capability_called')
    return list(attempts.values())

def document_delivery(prepared,observations,manifest,required=False):
    successful={x['identity']['item_id']:x['payload']['execution_observation'] for x in observations
        if x.get('payload',{}).get('execution_observation',{}).get('status')=='success'
        and x['payload']['execution_observation'].get('capability')=='document.read_section'}
    checks=[];source_checks=[];errors=[]
    for call,body in successful.items():
        data=body.get('data',{})
        try:
            checked=document_hash_check(data,manifest) if manifest else {'scope':'missing fixture manifest'}
            checked['path_matches_fixture']=bool(manifest and Path(data.get('resolved_path','')).resolve()==Path(manifest['path']).resolve())
        except (KeyError,TypeError,ValueError,IndexError,UnicodeError,OSError) as exc:
            checked={'error':type(exc).__name__}
        source_checks.append({'call_id':call,**checked})
        if not all(checked.get(key) is True for key in ['section_hash_matches','file_version_matches','excerpt_prefix_matches','path_matches_fixture']):
            errors.append('unverified_source:'+call)
    for event in prepared:
        for part in event['request'].get('input',[]):
            if part.get('type')!='function_call_output' or part.get('call_id') not in successful:continue
            call=part['call_id'];body=successful[call];expected=body.get('data',{})
            try:payload=json.loads(part.get('output',''))
            except (ValueError,TypeError):payload={}
            data=payload.get('data',{});content=data.get('content')
            actual=hashlib.sha256(content.encode()).hexdigest() if isinstance(content,str) else None
            valid=bool(payload.get('ok') is True and payload.get('capability')=='document.read_section'
                and actual is not None and actual==expected.get('content_hash')==data.get('content_hash')
                and data.get('source_hash')==expected.get('source_hash')
                and payload.get('identity',{}).get('call_id')==call
                and payload.get('identity',{}).get('observation_id')==body.get('observation_id'))
            checks.append({'request_sequence':event['sequence'],'call_id':call,'full_content_hash_matches':valid,
                'actual_sha256':actual,'expected_sha256':expected.get('content_hash'),
                'content_chars':len(content) if isinstance(content,str) else 0,
                'truncated':isinstance(content,str) and '[field truncated]' in content,'valid':valid})
    for call in successful:
        selected=[x for x in checks if x['call_id']==call]
        if not selected or not all(x['valid'] for x in selected):errors.append('body_not_fully_delivered:'+call)
    if required and not successful:errors.append('required_document_observation_missing')
    status='FAIL' if errors else 'PASS' if successful else 'NOT_APPLICABLE'
    return {'status':status,'required':required,'errors':errors,'source_checks':source_checks,'presentations':checks}


def audit(out):
    cases={x['id']:x for x in json.loads((out/'scenarios.json').read_text())['cases']}
    results=[]
    for item in json.loads((out/'plan.json').read_text()):
        f=out/item['id'];events=rows(f/'app-server-events.jsonl')
        messages=[x['message'] for x in events if isinstance(x.get('message'),dict)]
        all_terminals=[x['params']['turn'] for x in messages if x.get('method')=='turn/completed']
        control=json.loads((f/'compaction-control.json').read_text()) if (f/'compaction-control.json').exists() else None
        terminals=[x for x in all_terminals if not control or x.get('id')!=control['native_turn_id']]
        answers=[x['params']['item'].get('text','') for x in messages if x.get('method')=='item/completed' and x['params'].get('item',{}).get('type')=='agentMessage']
        usage=[x['params'].get('tokenUsage') for x in messages if x.get('method')=='thread/tokenUsage/updated']
        contract=rows(f/'execution-contract.trajectory.jsonl')
        observations=[x for x in contract if x.get('event_type')=='OBSERVATION']
        request_audit=rows(f/'model-http-audit.jsonl')
        prepared=[x for x in request_audit if x.get('event')=='request_prepared']
        snaps=[json.loads(p.read_text()) for p in sorted(f.glob('turn-*-snapshot.json'),key=lambda p:int(p.name.split('-')[1]))]
        compact=[x for x in messages if x.get('method')=='item/completed' and x['params'].get('item',{}).get('type')=='contextCompaction']
        normalized=list((f/'normalized-trajectories').glob('*')) if (f/'normalized-trajectories').exists() else []
        complete=(f/'result.json').exists()
        turn_answers=[[x['params']['item'].get('text','') for x in messages if x.get('method')=='item/completed'
            and x['params'].get('turnId')==terminal['id'] and x['params'].get('item',{}).get('type')=='agentMessage'] for terminal in terminals]
        # Native terminal items are a fallback only when item events lack turnId.
        for i,terminal in enumerate(terminals):
            if not turn_answers[i]:turn_answers[i]=[x.get('text','') for x in terminal.get('items',[]) if x.get('type')=='agentMessage']
        final_answer='\n'.join(turn_answers[-1]) if complete and turn_answers else ''
        manifest=json.loads((f/'fixture-manifest.json').read_text()) if (f/'fixture-manifest.json').exists() else None
        delivered=document_delivery(prepared,observations,manifest,bool(cases[item['case']].get('fixture') or item['case']=='evidence'))
        fixture_checks=delivered['source_checks'];delivery=delivered['presentations']
        result={**item,'document_body_delivery':delivery,'result_file_present':complete,'completed':False,'controlled_compaction_native_turn':control['native_turn_id'] if control else None,'all_native_terminal_count':len(all_terminals),'native_turn_statuses':[x.get('status') for x in terminals],
            'answers':answers,'turn_answers':turn_answers,'source_hash_checks':fixture_checks,'observations':observations,'last_cumulative_usage':usage[-1] if usage else None,
            'usage_updates':len(usage),'request_prepared_count':len(prepared),
            'request_snapshot_coverage':[x.get('snapshot_coverage') for x in prepared],
            'goal_projection_in_requests':['uaea.goal_state' in json.dumps(x['request']) for x in prepared],
            'transport_results':[{'request_id':x.get('request_id'),'http_status':x.get('http_status'),'transport_error':x.get('transport_error')} for x in request_audit if x.get('event')=='transport_result'],
            'compaction_items':len(compact),'compacted_notifications':sum(x.get('method')=='thread/compacted' for x in messages),
            'normalized_files':[str(x.relative_to(f)) for x in normalized],
            'projection_and_state_files':[(p.name,p.stat().st_size) for p in [f/'context-projections.jsonl',f/'semantic-state-snapshots.jsonl',f/'provider-history-decisions.jsonl'] if p.exists()],
            'goal_journal':rows(f/'goal-events.jsonl'),
            'active_goals':[x['phase1_runtime_snapshot']['active_goal'] for x in snaps],
            'model_output_is_source':[x['evidence_provenance']['model_output_is_source_evidence'] for x in snaps],
            'workflow_completed':[x['workflow_continuity']['completion_established'] for x in snaps],
            'source_literal_criterion':grounded_literal(final_answer,observations) if item['case']=='evidence' and complete else None,
            'missing_source_failure_observed':any(x.get('payload',{}).get('decision',{}).get('effective_parameters',{}).get('path','').split('/')[-1]=='missing.md' and x['payload']['execution_observation']['status']!='success' for x in observations),
            'first_request_contains_hidden_fixture_code': 'VELA-47Q2' in json.dumps(prepared[0]['request'],ensure_ascii=False) if prepared else None,
            'sampling_fields':{k:prepared[0]['request'][k] for k in ['temperature','seed','top_p'] if k in prepared[0]['request']} if prepared else {},
            'seconds':json.loads((f/'result.json').read_text())['seconds'] if complete else None}
        result['turn_integrity_errors']=turn_integrity(cases[item['case']]['turns'],json.loads((f/'turns.json').read_text()) if (f/'turns.json').exists() else [],
            terminals,snaps,json.loads((f/'result.json').read_text()) if complete else {})
        expected_control=cases[item['case']].get('compact_after')
        if expected_control is not None:
            confirmed=bool(control and control.get('after_script_turn')==expected_control
                and control.get('native_status')=='completed'
                and any(x.get('id')==control['native_turn_id'] and x.get('status')=='completed' for x in all_terminals)
                and any(x.get('params',{}).get('turnId')==control['native_turn_id'] for x in compact))
            if not confirmed:result['turn_integrity_errors'].append('controlled_compaction_not_confirmed')
        control_interval=None
        if control and any(x.get('id')==control['native_turn_id'] and x.get('status')=='completed' for x in all_terminals) and any(
                x.get('params',{}).get('turnId')==control['native_turn_id'] for x in compact):
            times=[x['emittedAtMs'] for x in messages if isinstance(x.get('emittedAtMs'),(int,float))
                and (x.get('params',{}).get('turnId')==control['native_turn_id']
                    or x.get('params',{}).get('turn',{}).get('id')==control['native_turn_id'])]
            if times:control_interval=(min(times),max(times))
        result['goal_projection_checks']=goal_projection_checks(prepared,rows(f/'provider-history-decisions.jsonl'),
            item['arm']=='goal_shadow',control_interval)
        if len({x.get('id') for x in all_terminals})!=len(all_terminals):result['turn_integrity_errors'].append('duplicate_native_terminal')
        native_checks=native_turn_checks(cases[item['case']]['turns'],terminals,messages)
        result['native_user_checks']=native_checks
        if not all(x['valid'] for x in native_checks):result['turn_integrity_errors'].append('native_user_input_binding_failed')
        if len(turn_answers)!=len(cases[item['case']]['turns']) or any(not any(t.strip() for t in texts) for texts in turn_answers):
            result['turn_integrity_errors'].append('normal_response_missing')
        result['completed']=complete and not result['turn_integrity_errors']
        result['native_input_turns']=sum(x['valid'] for x in native_checks)
        result['confirmed_user_turns']=sum(x['valid'] and any(t.strip() for t in texts) for x,texts in zip(native_checks,turn_answers))
        result['document_delivery_contract']=delivered
        result['tool_attempts']=tool_attempts(messages,contract)
        result['tool_attempt_counts']=dict(collections.Counter(x['classification'] for x in result['tool_attempts']))
        result['expected_turns']=len(cases[item['case']]['turns'])
        result['infrastructure_contract']=bool(result['completed'] and delivered['status'] in ['PASS','NOT_APPLICABLE'] and not result['turn_integrity_errors']
            and prepared and normalized and all(x['valid'] for x in result['goal_projection_checks']) and all(x is None for x in result['active_goals']) and not any(result['model_output_is_source']))
        results.append(result)
    return {'scope':'Fixed scripts (synthetic or explicitly historical adaptations); structural checks separate from qualitative semantic review and real value',
            'infrastructure_pass':sum(x['infrastructure_contract'] for x in results),'planned_sessions':len(results),
            'completed_turns':sum(x['confirmed_user_turns'] for x in results),'decision_value':'UNKNOWN','results':results}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--report',type=Path);a=ap.parse_args()
    result=audit(a.output);target=a.report or a.output/'audited-results.json'
    if target.exists():raise FileExistsError('Preserve prior audit: choose a new --report path')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))
if __name__=='__main__':main()
