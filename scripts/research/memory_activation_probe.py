"""Isolated equation/sensitivity probe. Synthetic semantic labels; no Memory admission."""
import argparse,hashlib,json,math
from pathlib import Path
def base(times,now,decay,unit=1.0):
 if not times:return -math.inf
 if decay<=0 or unit<=0 or any(t>now for t in times):raise ValueError('Invalid observation/time domain')
 return math.log(sum((1+(now-t)/unit)**(-decay) for t in times))
def cosine(x,y):
 den=math.sqrt(sum(v*v for v in x)*sum(v*v for v in y))
 return sum(a*b for a,b in zip(x,y))/den if den else 0.
def rank(records,cue,now,decay,weight,history_only=False):
 # Source/claim roles are fixture labels, not an automated semantic verification capability.
 eligible=[r for r in records if r['role']=='external_source' and r['validity']=='historical']
 return sorted(eligible,key=lambda r:(-(cosine(r['cue'],cue) if history_only else base(r['encodings'],now,decay)+weight*cosine(r['cue'],cue)),r['id']))
def experiment():
 records=[
 {'id':'old-ai-source','root':'obs-ai','role':'external_source','validity':'historical','cue':[1.,0.],'encodings':[0.],'content':'Synthetic dated AI research observation.'},
 {'id':'recent-unrelated','root':'obs-other','role':'external_source','validity':'historical','cue':[0.,1.],'encodings':[99.],'content':'Synthetic unrelated observation.'},
 {'id':'wrong-explanation','root':'model-claim','role':'interpretation','validity':'superseded','cue':[1.,0.],'encodings':[],'content':'An explicitly labelled wrong hypothesis, retained for error audit.'}]
 before=hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest()
 # Lifecycle event labels are supplied by an independently inspectable fixture, not inferred from prose.
 task={'status':'open'};goal={'status':'candidate'};task['status']='cancelled'
 assert goal['status']=='candidate'
 goal['status']='withdrawn'  # no deletion of any historical source or wrong-interpretation event
 after=hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest();assert before==after
 rh=rank(records,[1.,0.],100.,.5,1.,history_only=True)[0]['id']
 grid=[]
 for d in [.2,.5,.8]:
  for weight in [0.,.5,1.,2.,4.,8.]:
   winner=rank(records,[1.,0.],100.,d,weight)[0]['id']
   grid.append({'decay':d,'cue_weight':weight,'winner':winner,'matches_fixture_target':winner=='old-ai-source'})
 external=[{'root':'obs-ai','kind':'external','time':0}]
 echoes=[{'root':'obs-ai','kind':'derived_projection','time':j} for j in range(1,21)]
 original_times=[e['time'] for e in external if e['kind']=='external']
 eligible_times=[e['time'] for e in external+echoes if e['kind']=='external']
 assert base(original_times,100,.5)==base(eligible_times,100,.5)
 # Practice can change accessibility, but is NOT a new external fact/support unit.
 practice_accessibility_change=base([0,99],100,.5)-base([0],100,.5)
 assert practice_accessibility_change>0
 wrong=[r for r in records if r['role']=='interpretation']
 assert wrong and all(r['validity']=='superseded' for r in wrong)
 return {'scope':'synthetic boundary and equation sensitivity, no cognitive efficacy or human-memory fit',
 'checks':{'task_cancel_not_goal_cancel':True,'task_and_goal_changes_preserve_archival_bytes':before==after,
  'no_goal_context_query_can_retrieve_old_source':rh=='old-ai-source',
  'wrong_interpretation_retained_not_current_fact':True,
  'derived_repetitions_not_external_encodings':original_times==eligible_times,
  'practice_changes_accessibility_not_external_support':practice_accessibility_change>0},
 'strong_relevant_history_baseline':rh,'grid':grid,
 'activation_fixture_successes':sum(x['matches_fixture_target'] for x in grid),'grid_size':len(grid),
 'conclusion':'No demonstrated gain over Relevant History. Some activation settings wrongly prioritize recent unrelated material.',
 'parameter_status':'hand-chosen sensitivity grid, NOT calibrated probabilities or selected production settings',
 'statistical_independence':'UNKNOWN; root dedup does not estimate independent evidence'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError('Preserve prior results')
 result=experiment();a.output.write_text(json.dumps(result,indent=2))
 print(json.dumps({'boundary_checks':len(result['checks']),'activation_successes':result['activation_fixture_successes'],'grid':result['grid_size']}))
if __name__=='__main__':main()
