"""Offline causal/authority checks for the isolated proposal experiment, not a semantic judge."""
from pathlib import Path
import argparse,json,hashlib,collections,sys
sys.path[:0]=[str(Path(__file__).resolve().parents[2]),str(Path(__file__).resolve().parents[1])]
from research.longitudinal_audit import audit,rows
import research.longitudinal_dialogue
from research.goal_hypothesis import TOOL,candidate_head
def sha(value):
 return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def lifecycle_status(checks,completed,separate,active_goals):
 """A non-exercised candidate lifecycle cannot pass through all([])."""
 if not separate or any(x is not None for x in active_goals):
  return 'FAIL'
 if any(not c['model_and_source_bound'] or not c['basis_versions_resolved'] for c in checks):
  return 'FAIL'
 if not checks:
  return 'UNKNOWN'
 return 'PASS' if completed and active_goals else 'PARTIAL'

def record_binding(event,call,original,seen,observation_ids):
 """Compare values to the actual native arguments, not merely a copied payload hash."""
 try:
  record=event['record'];meta=record['metadata'];receipt=event['receipt'];raw=call['arguments']
  source=original[meta['input_id']];target=raw['candidate_id'];operation=raw['operation']
  parent=seen.get(target)
  superseded={r['metadata']['previous_candidate_id'] for r in seen.values()}
  parent_ok=(target is None if operation=='form' else
    parent is not None and target not in superseded and parent['status']!='withdrawn')
  effective=parent['metadata']['hypothesis']['hypothesis'] if operation in ['maintain','withdraw'] else raw['hypothesis']
  basis=raw.get('input_ids',[]);evidence=raw.get('evidence_ids',[])
  identity='goal-candidate:'+hashlib.sha256(':'.join((call['threadId'],call['turnId'],event['call_id'])).encode()).hexdigest()[:24]
  return bool(parent_ok and operation in ['form','maintain','refine','revise','withdraw']
   and (operation not in ['maintain','withdraw'] or raw['hypothesis'] in ['',effective])
   and receipt['payload_sha256']==sha(raw) and meta['submitted_proposal']==raw
   and receipt['candidate_sha256']==sha(record) and receipt['committed'] is True
   and receipt['ok'] is True and receipt['operation']==operation and receipt['status']==record['status']
   and call['turnId']==meta['turn_id']==event['turn_id']==source['native_turn_id']
   and call['threadId']==meta['thread_id'] and call['tool']==TOOL
   and record['source_event_ids']==[event['call_id']] and meta['request_sha256']==source['sha256']
   and raw['quote'] and raw['quote'] in source['text'] and meta['proposal']['quote']==raw['quote']
   and meta['operation']==operation and meta['previous_candidate_id']==target
   and meta['hypothesis']=={'hypothesis':effective,'confidence':'unassessed','status':'inferred'}
   and meta['proposal']=={'summary':effective,'relation':operation,'target_goal_id':None,'quote':raw['quote'],'evidence_ids':evidence}
   and meta['asserted_support_input_ids']==basis and meta['evidence_ids']==evidence
   and all(x in observation_ids for x in evidence)
   and meta['basis_input_versions']=={x:original[x]['sha256'] for x in basis}
   and record['source_object_ids']==list(dict.fromkeys([meta['input_id']]+basis+evidence+([target] if target else [])))
   and record['object_type']=='goal_hypothesis_candidate' and record['owner']==source['owner']
   and record['object_id']==receipt['candidate_id']==identity and identity not in seen
   and record['status']==('withdrawn' if operation=='withdraw' else 'candidate')
   and meta['source_kind']=='model_semantic_tool_proposal'
   and meta['research_only'] is True and meta['authority_level']=='interpretation'
   and meta['semantic_correctness']=='not_established' and meta['adoption_eligible'] is False)
 except (KeyError,TypeError,ValueError):
  return False

def transport_binding(request,transports):
 matches=[x for x in (transports or []) if x.get('request_id')==request.get('request_id') and request.get('request_id')]
 if len(matches)!=1:return {'status':'UNKNOWN','reason':'no unique transport result'}
 event=matches[0];status=event.get('http_status')
 if event.get('transport_error') or (isinstance(status,int) and not 200<=status<300):
  return {'status':'FAIL','reason':'provider transport failed'}
 valid=(isinstance(status,int) and 200<=status<300 and isinstance(event.get('bytes_received'),int)
  and event['bytes_received']>0 and isinstance(event.get('utc'),(int,float)) and isinstance(request.get('utc'),(int,float))
  and event['utc']>=request['utc'])
 return {'status':'PASS' if valid else 'UNKNOWN','reason':'HTTP success with response bytes; not proof of complete SSE processing or understanding'}

def projection_binding(prepared,records,committed_at=None,transports=None):
 output=[];appearances={k:[] for k in records}
 for request in prepared:
  views=[];malformed=False
  for part in request['request'].get('input',[]):
   if part.get('role')!='user':continue
   for content in part.get('content',[]):
    text=content.get('text','');tag='<external_uaea.goal_hypotheses>'
    if not isinstance(text,str) or not text.startswith(tag):continue
    try:views.append(json.loads(text[len(tag):].split('</external_uaea.goal_hypotheses>')[0]))
    except ValueError:malformed=True
  heads=[h for view in views for h in view.get('heads',[])]
  instant=request.get('utc')
  known_time=isinstance(instant,(int,float)) and all(isinstance((committed_at or {}).get(k),(int,float)) for k in records)
  active={k:r for k,r in records.items() if known_time and committed_at[k]<=instant}
  superseded={r['metadata']['previous_candidate_id'] for r in active.values()}
  transport=transport_binding(request,transports)
  checks=[]
  for head in heads:
   identity=head.get('candidate_id')
   valid=identity in records and head==candidate_head(records[identity])
   commit=(committed_at or {}).get(identity);instant=request.get('utc')
   after=(instant>=commit if isinstance(commit,(int,float)) and isinstance(instant,(int,float)) else None)
   current=(identity in active and identity not in superseded) if known_time else None
   checks.append({'candidate_id':identity,'content_and_version_match':valid,'after_commit':after,'current_head_at_request':current})
   if valid and after is True and current is True and transport['status']=='PASS':appearances[identity].append(request['sequence'])
  output.append({'sequence':request['sequence'],'view_count':len(views),
   'proposal_tool_advertised':any(t.get('name')==TOOL for t in request['request'].get('tools',[])),
   'candidate_ids_in_untrusted_view':[h.get('candidate_id') for h in heads],
   'heads':checks,'transport':transport,'views_interpretation_only':bool(views) and all(v.get('is_source_evidence') is False
     and v.get('semantic_correctness')=='not_established' for v in views),
   'valid':not malformed and len(views)<=1 and all(c['content_and_version_match'] and c['after_commit'] is not False and c['current_head_at_request'] is not False for c in checks)
     and all(v.get('is_source_evidence') is False and v.get('semantic_correctness')=='not_established' for v in views)})
 return output,appearances

def snapshot_binding(path,records):
 if not path.exists():
  return {'status':'UNKNOWN' if records else 'NOT_APPLICABLE','reason':'materialized view unavailable'}
 try:
  state=json.loads(path.read_text());versions=state['versions'];ids=[r['object_id'] for r in versions]
  exact=(len(set(ids))==len(ids) and all(k in records and row==records[k] for k,row in zip(ids,versions)))
  parents={v['metadata']['previous_candidate_id'] for v in versions}
  heads=[v for v in versions if v['object_id'] not in parents]
  exact=exact and state['heads']==heads and state['active_goal_id'] in ['',None] and state['source_evidence'] is False
  return {'status':('FAIL' if not exact else 'PARTIAL' if set(ids)!=set(records) else 'PASS'),
   'saved_version_count':len(ids),'committed_version_count':len(records),
   'reason':'snapshot may lag commit; changed content is a violation, missing versions are incomplete materialization'}
 except (ValueError,KeyError,TypeError):
  return {'status':'FAIL','reason':'invalid materialized view'}

def evaluate(root):
 base=audit(root);cases={c['id']:c for c in json.loads((root/'scenarios.json').read_text())['cases']}
 for result in base['results']:
  folder=root/result['id'];messages=[x['message'] for x in rows(folder/'app-server-events.jsonl') if 'message' in x]
  journal=rows(folder/'goal-events.jsonl')
  versions=[x['payload'] for x in journal if x['event']=='RESEARCH_GOAL_VERSION']
  rejected=[x['payload'] for x in journal if x['event']=='RESEARCH_GOAL_REJECTED']
  native={x['params']['callId']:x['params'] for x in messages if x.get('method')=='item/tool/call' and x.get('params',{}).get('tool')==TOOL}
  turns=json.loads((folder/'turns.json').read_text()) if (folder/'turns.json').exists() else []
  original={}
  for turn in turns:
   snap=json.loads((folder/f"turn-{turn['turn']}-snapshot.json").read_text())
   original[snap['current_input_id']]={'text':turn['user_text'],'native_turn_id':turn['native_turn_id'],
     'sha256':hashlib.sha256(turn['user_text'].encode()).hexdigest(),'owner':snap.get('task_id')}
  seen={};checks=[]
  for event in versions:
   record=event['record'];meta=record['metadata'];receipt=event['receipt'];call=native.get(event['call_id'])
   source=original.get(meta['input_id'],{})
   observation_ids={x['payload']['execution_observation']['observation_id'] for x in result['observations']}
   valid=record_binding(event,call,original,seen,observation_ids) if call else False
   basis=all(ref in original and original[ref]['sha256']==version for ref,version in meta['basis_input_versions'].items())
   checks.append({'candidate_id':record['object_id'],'call_id':event['call_id'],'native_turn_id':meta['turn_id'],
     'operation':meta['operation'],'previous_candidate_id':meta['previous_candidate_id'],
     'hypothesis':meta['hypothesis']['hypothesis'],'status':record['status'],
     'model_and_source_bound':valid,'basis_versions_resolved':basis,
     'asserted_historical_input_count':len(meta['basis_input_versions']),
     'semantic_support':'not_established'})
   seen[record['object_id']]=record
  semantic_ids=set(native)
  domain_ids={x['identity']['item_id'] for x in result['observations']}
  classified=[]
  for attempt in result['tool_attempts']:
   item=dict(attempt)
   if item['call_id'] in semantic_ids:
    item['classification']=('semantic_proposal_retained' if any(v['call_id']==item['call_id'] for v in versions)
     else 'semantic_proposal_rejected' if any(v['call_id']==item['call_id'] for v in rejected) else 'semantic_proposal_unresolved')
   classified.append(item)
  prepared=[x for x in rows(folder/'model-http-audit.jsonl') if x.get('event')=='request_prepared']
  projection,appearances=projection_binding(prepared,seen,
   {e['record']['object_id']:e.get('committed_at_utc') for e in versions},
   [x for x in rows(folder/'model-http-audit.jsonl') if x.get('event')=='transport_result'])
  for check in checks:
   check['subsequent_request_sequences']=appearances[check['candidate_id']]
   check['prepared_request_sequences']=[p['sequence'] for p in projection if any(h['candidate_id']==check['candidate_id']
    and h['content_and_version_match'] and h['after_commit'] is True and h['current_head_at_request'] is True for h in p['heads'])]
   check['supply_scope']='Exact current head in outgoing request + successful provider response; model understanding not established'
   check['model_projection_status']='PASS' if appearances[check['candidate_id']] else 'NOT_OBSERVED'
  result['proposal_lifecycle']=checks;result['proposal_rejections']=rejected;result['proposal_projection']=projection
  result['semantic_proposal_not_domain_observation']=not bool(semantic_ids & domain_ids)
  result['classified_attempt_counts']=dict(collections.Counter(t['classification'] for t in classified))
  result['lifecycle_contract_status']=lifecycle_status(checks,result['completed'],
     result['semantic_proposal_not_domain_observation'],result['active_goals'])
  result['materialized_snapshot_contract']=snapshot_binding(folder/'goal-research-state.json',seen)
  result['candidate_commit_contract_status']=result['lifecycle_contract_status']
  result['candidate_projection_status']=('FAIL' if any(not p['valid'] for p in projection) else
      'UNKNOWN' if not checks else 'PASS' if all(appearances.values()) else 'PARTIAL')
  if result['candidate_projection_status']=='FAIL' or result['materialized_snapshot_contract']['status']=='FAIL':
   result['lifecycle_contract_status']='FAIL'
  elif result['lifecycle_contract_status']=='PASS' and result['materialized_snapshot_contract']['status']!='PASS':
   result['lifecycle_contract_status']='PARTIAL'
  elif result['lifecycle_contract_status']=='PASS' and result['candidate_projection_status']!='PASS':
   result['lifecycle_contract_status']='PARTIAL'
  result['proposal_publications']=[x['payload'] for x in journal if x['event']=='RESEARCH_GOAL_PUBLICATION']
  result['lifecycle_contract']=result['lifecycle_contract_status']=='PASS'
  result['lifecycle_scope']='Saved native-bound versions AND actual outbound content checked separately; no proposals is UNKNOWN'
  result['candidate_generation_observed']=bool(checks)
  result['goal_semantic_quality']='REQUIRES_INDEPENDENT_REVIEW'
  result['incremental_decision_value']='UNKNOWN'
 return base
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
 args=parser.parse_args()
 if args.report.exists():raise FileExistsError('Preserve prior experiment reports')
 result=evaluate(args.output);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))
if __name__=='__main__':main()
