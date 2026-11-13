
"""CPU-only real-history projection + real Codex outbound probe. No model server."""
import argparse,copy,hashlib,importlib.util,json,sys,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harness.provider_history import project_provider_history
from harness.request_audit import redact
from research.recover_goal_history import read_history,verify,restore,clone_native_home,resume_recovered_app,rows,sha
from research.goal_sideband import ProposalAdapter,ProposalApp
from h3_harness_interactive_repl import build_interactive_adapter
from h3_context_characterization import DEFAULT_CODEX_BIN,write_config
from h3_failed_attempt_recovery_probe import sse

def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def need(x,msg):
    if not x:raise AssertionError(msg)
def native_goal_pairs(root):
    events=[x['message'] for x in rows(root/'app-server-events.jsonl') if 'message'in x]
    result=[]
    for m in events:
        if m.get('method')!='item/tool/call' or m['params'].get('tool')!='goal_hypothesis':continue
        p=m['params'];cid=p['callId']
        done=[x['params']['item'] for x in events if x.get('method')=='item/completed'
              and x['params'].get('item',{}).get('id')==cid]
        need(len(done)==1,'Receipt closure missing/ambiguous')
        receipt=json.loads(done[0]['contentItems'][0]['text'])
        result.append({'call_id':cid,'thread_id':p['threadId'],'turn_id':p['turnId'],
                       'arguments':p['arguments'],'receipt':receipt})
    return result
def fact_rows(request):
    out={}
    for field in ('input','previous_input_messages'):
        for i in request.get(field,[]):
            if i.get('type')!='message':continue
            for c in i.get('content',[]):
                t=c.get('text','')
                if t.startswith('Historical runtime observation,'):
                    f=json.loads(t.split('\n',1)[1])
                    if 'goal_attempt'in f:out[f['call_id']]=f
    return out
def check_facts(request,pairs):
    fs=fact_rows(request)
    for p in pairs:
        a=fs[p['call_id']]['goal_attempt']
        need(a['submitted_arguments']==p['arguments'],'Actual failed proposal not preserved')
        need(a['operation']==p['arguments']['operation'],'Operation mismatch')
        need(a['target_candidate_id']==p['arguments']['candidate_id'],'Target mismatch')
        need(a['host_result']['committed'] is False,'Commit mismatch')
        need(a['host_result']['accepted'] is False,'Accept mismatch')
        need(a['proposal_text_visibility']=='complete','Unexpected omitted real proposal')
    return fs
def verify_capture(out, failure, success):
    folder=out/'wire'
    rejected=native_goal_pairs(failure)
    raw=(folder/'captured-wire-1.json').read_bytes()
    q=json.loads(raw);fs=check_facts(q,rejected)
    prepared=[x for x in rows(folder/'model-http-audit.jsonl') if x.get('event')=='request_prepared']
    transports=[x for x in rows(folder/'model-http-audit.jsonl') if x.get('event')=='transport_result']
    need(len(prepared)==len(transports)==1,'Capture request count mismatch')
    need(prepared[0]['forwarded_bytes_sha256']==hashlib.sha256(raw).hexdigest(),'Wire hash mismatch')
    need(prepared[0]['request']==redact(q),'Redacted capture mismatch')
    need(transports[0]['response_complete'] is True and transports[0]['http_framing_complete'] is True,
         'Incomplete response')
    native=[x['message'] for x in rows(folder/'app-server-events.jsonl') if 'message'in x]
    need(not any(m.get('method')=='item/tool/call' for m in native),'New tool dispatch detected')
    need(any(m.get('method')=='turn/completed' and m['params']['turn']['status']=='completed'
             for m in native),'Native Turn did not complete')
    original=json.loads((success/'goal-research-state.json').read_text())
    current=json.loads((folder/'goal-research-state.json').read_text())
    need(original['heads']==current['heads'] and original['versions']==current['versions'],
         'Recovered Goal state changed')
    journal=rows(folder/'goal-events.jsonl')
    need(not any(x.get('event') in ('RESEARCH_GOAL_VERSION','RESEARCH_GOAL_REJECTED')
                 for x in journal[len(rows(success/'goal-events.jsonl')):]),'New Goal attempt recorded')
    result={'passed':True,'scope':'Actual pinned Codex -> Bridge -> loopback HTTP CPU fixture; NO GPU or language model',
            'native_thread_id':json.loads((folder/'recovered-bundle.json').read_text())['snapshot']['thread_id'],'actual_outbound_requests':1,
            'failed_goal_calls_visible':list(fs),'wire_matches_http_audit':True,
            'no_new_tool_calls':True,'host_goal_heads_unchanged':True,
            'host_recovery_scope':'Original verified two-head checkpoint; failed Native branch adds no saved Goal versions. Additional old feedback inputs are Native history, not newly re-executed Host observations.',
            'fixture_response_is_not_model_behavior':True}
    originals=json.loads((out/'cpu-real-history-result.json').read_text())['original_hashes']
    need(all(sha(Path(name))==expected for name,expected in originals.items()),'Original evidence changed')
    proof=json.loads((folder/'native-copy.json').read_text())
    now={str(p.relative_to(failure/'codex-home')):sha(p) for p in (failure/'codex-home').rglob('*') if p.is_file()}
    need(now==proof['source_files'],'Original Native home changed')
    dump(out/'originals-unchanged.json',{'source_evidence':originals,'native_home_files':len(now),
         'native_source_hashes_unchanged':True})
    dump(folder/'result.json',result)
    return result

def run(a):
    out=a.output.resolve();need(out.is_dir(),'Use prepared fresh batch')
    success=a.success.resolve();failure=a.failure.resolve()
    immutable=[success/'goal-events.jsonl',success/'app-server-events.jsonl',
               failure/'goal-events.jsonl',failure/'app-server-events.jsonl',
               failure/'goal-research-state.json']
    before={str(p):sha(p) for p in immutable}
    accepted=native_goal_pairs(success);rejected=native_goal_pairs(failure)
    need(len(accepted)==2 and len(rejected)==6,'Unexpected frozen case')
    need(all(p['receipt']['committed'] is False for p in rejected),'Not failed case')
    state=json.loads((failure/'goal-research-state.json').read_text())
    original=json.loads((success/'goal-research-state.json').read_text())
    need(state['versions']==original['versions'] and state['heads']==original['heads'],
         'Failed branch changed original Goal state')
    allpairs=accepted+rejected
    items=[]
    for p in allpairs:
        items += [{'type':'function_call','call_id':p['call_id'],'name':'goal_hypothesis',
                  'arguments':json.dumps(p['arguments'],ensure_ascii=False),
                  'internal_chat_message_metadata_passthrough':{'turn_id':p['turn_id']}},
                 {'type':'function_call_output','call_id':p['call_id'],
                  'output':json.dumps(p['receipt'],ensure_ascii=False)}]
    reconstructed={'input':items}
    # This artifact is a semantic reconstruction from Native, not original wire bytes.
    dump(out/'native-call-receipt-bindings.json',allpairs)
    dump(out/'native-reconstructed-history.json',reconstructed)
    spec=importlib.util.spec_from_file_location('harness._provider_history_before',out/'before/harness/provider_history.py')
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    dump(out/'projection-before.json',old.project_provider_history(reconstructed).request)
    fixed=project_provider_history(reconstructed)
    dump(out/'projection-after.json',fixed.request)
    fs=check_facts(fixed.request,rejected)
    need(fixed.request['input'][:4]==items[:4],'Successful form history changed')
    dump(out/'cpu-real-history-result.json',{'passed':True,'accepted_forms':len(accepted),
        'rejected_revises':len(rejected),'call_order':list(fs),
        'decisions':fixed.decisions,'original_hashes':before,
        'comparison_basis':'exact parsed Native arguments and original Host receipts; reconstructed wire encoding not claimed'})

    # Clone the real failed Native Thread. Its Goal heads are identical to the
    # independently verified original Host checkpoint. Never replay its tool calls.
    folder=out/'wire';bundle,_,_=restore(success,folder)
    thread=bundle['snapshot']['thread_id']
    proof=clone_native_home(failure,folder/'codex-home',thread)
    dump(folder/'native-copy.json',proof)
    requests=[];request_bytes=[];server_errors=[]
    class CPUFixture(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            try:
                need(self.path.split('?')[0]=='/v1/responses','Unexpected CPU route')
                body=self.rfile.read(int(self.headers['Content-Length']))
                request_bytes.append(body);q=json.loads(body);requests.append(q)
                (folder/f'captured-wire-{len(requests)}.json').write_bytes(body)
                need(len(requests)==1,'No retry permitted in outbound probe')
                # Fixed protocol fixture; not an LLM or cognition measurement.
                item={'type':'message','role':'assistant','id':'cpu-audit-final',
                      'content':[{'type':'output_text','text':'CPU_OUTBOUND_CAPTURED_NO_MODEL'}]}
                body=sse(item,'cpu-outbound-replay-1')
                self.send_response(200);self.send_header('Content-Type','text/event-stream')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            except Exception as exc:
                server_errors.append(repr(exc));self.send_error(500)
    server=ThreadingHTTPServer(('127.0.0.1',0),CPUFixture)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    import tomllib
    model=tomllib.loads((failure/'codex-home/config.toml').read_text())['model']
    write_config(folder/'codex-home',base,65536,model=model,n1x=True)
    adapter=build_interactive_adapter(folder/'adapter')
    adapter.__class__=ProposalAdapter
    app=ProposalApp(codex=DEFAULT_CODEX_BIN,codex_home=folder/'codex-home',
        workspace=folder/'adapter/sandbox',base_url=base,adapter=adapter,
        events_path=folder/'app-server-events.jsonl',stderr_path=folder/'stderr.log',
        turn_timeout=60,model=model,goal_mode='shadow',execution_contract='shared',input_actor='test_driver')
    new_calls=[]
    def forbid(message):
        new_calls.append(message)
        raise AssertionError('CPU outbound probe must never dispatch a tool, including history')
    app._handle_tool_call=forbid
    try:
        resume_recovered_app(app,bundle)
        app.run_turn('CPU传输审计：仅确认收到请求，不调用工具，不修改任何候选。此输出由CPU协议桩返回，不评价认知。')
        need(not new_calls,'Unexpected tool dispatch')
        need(not server_errors and len(requests)==1,'Actual outbound capture incomplete')
        wirefacts=check_facts(requests[0],rejected)
        prepared=[x for x in rows(folder/'model-http-audit.jsonl') if x.get('event')=='request_prepared']
        transport=[x for x in rows(folder/'model-http-audit.jsonl') if x.get('event')=='transport_result']
        need(len(prepared)==len(transport)==1,'Missing HTTP audit')
        need(prepared[0]['forwarded_bytes_sha256']==hashlib.sha256(request_bytes[0]).hexdigest(),'Wire bytes/audit mismatch')
        need(prepared[0]['request']==redact(requests[0]),'Redacted audit snapshot differs from actual CPU receiver')
        need(transport[0]['http_framing_complete'] is True and transport[0]['response_complete'] is True,'Incomplete fixture transfer')
        heads=app.goals.heads(app.semantic_state._state_for(thread))
        need([r.to_dict() for r in heads]==original['heads'],'Host heads changed')
        need(len(app.goals.records(app.semantic_state._state_for(thread)))==2,'Unexpected new Goal version')
        dump(folder/'result.json',{'passed':True,'scope':'Actual pinned Codex -> Bridge -> loopback HTTP CPU fixture; NO GPU or language model',
            'native_thread_id':thread,'actual_outbound_requests':1,'failed_goal_calls_visible':list(wirefacts),
            'wire_matches_http_audit':True,'no_new_tool_calls':True,'host_goal_heads_unchanged':True,
            'host_recovery_scope':'Original verified two-head checkpoint; failed Native branch adds no saved Goal versions. Additional old feedback inputs are Native history, not newly re-executed Host observations.',
            'fixture_response_is_not_model_behavior':True})
    finally:
        app.close();server.shutdown();server.server_close()
    need(before=={str(p):sha(p) for p in immutable},'Original evidence changed')
    dump(out/'originals-unchanged.json',before)
    print(json.dumps({'cpu_real_history':'PASS','actual_harness_outbound':'PASS','failed_calls':6,'no_model':True}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--success',type=Path,required=True)
    p.add_argument('--failure',type=Path,required=True);p.add_argument('--verify-capture',action='store_true')
    a=p.parse_args()
    if a.verify_capture:
        print(json.dumps(verify_capture(a.output,a.failure,a.success)))
    else:run(a)
