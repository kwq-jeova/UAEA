"""Isolated fixed counterfactuals and prequential toy forecasts. No Runtime imports."""
from pathlib import Path
import argparse,copy,hashlib,json,math,random,statistics

def unit(v):
 n=math.sqrt(sum(x*x for x in v))
 return [x/n for x in v] if n else list(v)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def mean_vec(vectors):
 return unit([sum(v[k] for v in vectors)/len(vectors) for k in range(3)]) if vectors else [0.,0.,0.]
def context(events,beta,include_derived=False):
 c=[0.,0.,0.]
 for e in events:
  if e['origin']!='external' and not include_derived:continue
  c=unit([(1-beta)*x+beta*y for x,y in zip(c,e['cue'])])
 return c
def activation(times,now,d):
 return math.log(sum((1+now-t)**(-d) for t in times))
def cases():
 a={'id':'A','cue':unit([1,1,0]),'times':[0],'origin':'external_source','valid':'historical'}
 b={'id':'B','cue':unit([1,0,1]),'times':[0],'origin':'external_source','valid':'historical'}
 ea={'root':'external-A','origin':'external','cue':[0,1.,0]}
 eb={'root':'external-B','origin':'external','cue':[0,0,1.]}
 common={'items':[a,b],'query':[1.,0,0],'now':100,'note':'manual synthetic semantic coordinates and targets, not inferred Goal truth'}
 ab={**common,'id':'order_AB','events':[ea,eb],'target':'B'}
 ba={**common,'id':'order_BA','events':[eb,ea],'target':'A'}
 reset={**common,'id':'weak_current_cue_overrides_history','query':unit([1,.2,0]),'events':[ea,eb],'target':'A',
  'note':'target scope is manually fixed; weak feature salience deliberately exposes interference'}
 echoes={**copy.deepcopy(ab),'id':'derived_echoes','events':[ea,eb]+[
  {'root':ea['root'],'origin':'model_restatement','cue':ea['cue']} for _ in range(20)]}
 rare={**common,'id':'rare_relevant','items':[
  {**a,'cue':[1.,0,0],'times':[0]},{**b,'cue':[0.,1,0],'times':[99]}],
  'events':[],'target':'A'}
 error={**common,'id':'superseded_claim','events':[ea,eb],'target':'B','items':[a,b,
  {'id':'false-claim','cue':[1.,0,0],'times':[99]*20,'origin':'model_claim','valid':'superseded'}]}
 return [ab,ba,reset,echoes,rare,error]

def retrieval(case,params):
 ext=[e['cue'] for e in case['events'] if e['origin']=='external']
 flat=mean_vec(ext);drift=context(case['events'],params['beta'])
 naive=context(case['events'],params['beta'],include_derived=True)
 scores={m:{} for m in ['relevant_history','actr_lite','cmr_lite','actr_cmr','naive_double_shared_cue','negative_unfiltered_context']}
 # Common reviewer-given source/validity eligibility; not a learned semantic validator.
 for item in case['items']:
  if item['origin']!='external_source' or item['valid']!='historical':continue
  q=dot(item['cue'],unit(case['query']));f=dot(item['cue'],flat);c=dot(item['cue'],drift)
  b=activation(item['times'],case['now'],params['decay'])
  scores['relevant_history'][item['id']]=q+params['context_weight']*f
  scores['actr_lite'][item['id']]=q+params['context_weight']*f+b
  scores['cmr_lite'][item['id']]=q+params['context_weight']*c
  scores['actr_cmr'][item['id']]=q+params['context_weight']*c+b
  scores['naive_double_shared_cue'][item['id']]=2*q+params['context_weight']*(f+c)+b
  scores['negative_unfiltered_context'][item['id']]=q+params['context_weight']*dot(item['cue'],naive)
 result={}
 for model,values in scores.items():
  best=max(values.values());tied=[k for k,v in values.items() if math.isclose(v,best,abs_tol=1e-10)]
  result[model]={'scores':values,'top_ties':tied,'strict_hit':tied==[case['target']],
   'target_in_ties':case['target'] in tied,'budget':1,'tie_is_not_unique_success':True}
 return {'case':case['id'],'target':case['target'],'models':result,
  'context_flat':flat,'context_ordered':drift,'negative_context_includes_derived':naive}

class Forecast:
 def __init__(self,name):
  self.name=name;self.n=0;self.s=0;self.fast=.5;self.slow=.5;self.posterior=.5;self.prior=.5
 def predict(self):
  if self.name=='relevant_history_beta':return (self.s+.5)/(self.n+1)
  if self.name=='two_rate_control':return .5*self.fast+.5*self.slow
  self.prior=.95*self.posterior+.05*(1-self.posterior)
  return .1*(1-self.prior)+.9*self.prior
 def observe(self,y):
  if self.name=='relevant_history_beta':self.s+=y;self.n+=1
  elif self.name=='two_rate_control':
   self.fast=.5*y+.5*self.fast;self.slow=.05*y+.95*self.slow
  else:
   l1=.9 if y else .1;l0=.1 if y else .9
   self.posterior=self.prior*l1/(self.prior*l1+(1-self.prior)*l0)

def generate(regime,seed,length):
 rng=random.Random(seed);state=rng.randrange(2);ys=[];zs=[]
 for _ in range(length):
  if rng.random()<.05:state=1-state
  p=(.9 if state else .1) if regime=='matched_markov' else .5
  ys.append(int(rng.random()<p));zs.append(state if regime=='matched_markov' else None)
 return {'y':ys,'hidden_state_for_audit_only':zs}
def forecasts(data,params,poison=False):
 names=['relevant_history_beta','two_rate_control','known_hmm']
 out={}
 for regime,sequences in data.items():
  metrics={n:[] for n in names};reliability={n:[[] for _ in range(5)] for n in names}
  for sequence in sequences:
   models={n:Forecast(n) for n in names};losses={n:[] for n in names};logloss={n:[] for n in names}
   for t,y in enumerate(sequence['y']):
    for n,model in models.items():
     p=model.predict()
     if t>=params['warmup']:
      losses[n].append((p-y)**2);logloss[n].append(-math.log(p if y else 1-p))
      reliability[n][min(int(p*5),4)].append((p,y))
     model.observe(y)
     if poison:
      # Deliberately invalid "self-echo = fresh trial" control; not a proposed model.
      for _ in range(3):model.predict();model.observe(y)
   for n in names:metrics[n].append({'brier':statistics.mean(losses[n]),'log_loss':statistics.mean(logloss[n])})
  out[regime]={}
  for n in names:
   out[regime][n]={'mean_brier':statistics.mean(v['brier'] for v in metrics[n]),
    'mean_log_loss':statistics.mean(v['log_loss'] for v in metrics[n]),'per_trajectory':metrics[n],
    'reliability_bins':[{'count':len(v),'mean_prediction':statistics.mean(x[0] for x in v) if v else None,
    'frequency':statistics.mean(x[1] for x in v) if v else None} for v in reliability[n]]}
  for n in names[1:]:
   diffs=[a['brier']-b['brier'] for a,b in zip(metrics[n],metrics[names[0]])]
   out[regime][n]['paired_brier_minus_baseline']={'mean':statistics.mean(diffs),
    'se_across_independent_trajectories':statistics.stdev(diffs)/math.sqrt(len(diffs))}
 return out

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
 out=args.output;out.mkdir(parents=True,exist_ok=False)
 params={'decay':.5,'beta':.8,'context_weight':.5,'seed':4921,'trajectories':24,'length':48,'warmup':8,
  'hmm_stay':.95,'hmm_emissions':[.1,.9],'stationary_probability':.5,
  'two_rate_fast':.5,'two_rate_slow':.05,'two_rate_mix':.5}
 fixtures=cases();data={r:[generate(r,params['seed']+i+10000*k,params['length'])
  for i in range(params['trajectories'])] for k,r in enumerate(['matched_markov','stationary_noise'])}
 for n,obj in [('parameters.json',params),('retrieval-cases.json',fixtures),('forecast-data.json',data)]:
  (out/n).write_text(json.dumps(obj,indent=2))
 pins={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['parameters.json','retrieval-cases.json','forecast-data.json']}
 pins['script']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 (out/'frozen-before-evaluation.json').write_text(json.dumps(pins,indent=2))
 ranked=[retrieval(c,params) for c in fixtures]
 forecast=forecasts(data,params);negative=forecasts(data,params,poison=True)
 # Counterfactual identity/ordering checks, not claims of semantic correctness.
 assert ranked[0]['models']['relevant_history']==ranked[1]['models']['relevant_history']
 assert ranked[0]['models']['cmr_lite']['top_ties']!=ranked[1]['models']['cmr_lite']['top_ties']
 for model in ['relevant_history','actr_lite','cmr_lite','actr_cmr']:
  assert ranked[0]['models'][model]==ranked[3]['models'][model],model
 assert ranked[3]['models']['negative_unfiltered_context']['top_ties']!=ranked[3]['models']['cmr_lite']['top_ties']
 result={'scope':'synthetic discriminating tasks; manually supplied semantics; no original human-model replication',
 'retrieval':ranked,'forecasts':forecast,'invalid_echo_control':negative,
 'summary':{m:{'strict_hits':sum(v['models'][m]['strict_hit'] for v in ranked),
  'target_in_ties':sum(v['models'][m]['target_in_ties'] for v in ranked),'cases':len(ranked)} for m in ranked[0]['models']},
 'probability_scope':'Known toy generators or explicit stationary Bernoulli prior; not calibrated Goal confidence',
 'cls_scope':'two-rate scalar EMA control is NOT full CLS or learned semantic consolidation',
 'stopping':'No fitted parameter scan, no deployment, no Goal/Memory adoption'}
 (out/'results.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({'retrieval':result['summary'],'forecast_brier':{r:{n:round(v['mean_brier'],4) for n,v in metrics.items()} for r,metrics in forecast.items()}}))
if __name__=='__main__':main()
