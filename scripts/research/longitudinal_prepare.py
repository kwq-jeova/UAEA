"""Create exclusive, frozen research plans; does not start a model."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2]
def make_plan(data):
    cases=data['cases'];seen=set();plan=[]
    limit=data.get('max_turns',10)
    if type(limit) is not int or not 2<=limit<=30:raise ValueError('Research turn limit must be an integer from 2 to 30')
    for i,c in enumerate(cases):
        name=c['id']
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,40}',name) or name in seen:raise ValueError('Unsafe/duplicate case id')
        seen.add(name)
        if not 2<=len(c['turns'])<=limit or any(not isinstance(t,str) or not t.strip() or t.startswith('/') for t in c['turns']):raise ValueError('Use fixed ordinary user turns, not control commands')
        for arm in (['relevant_history','goal_shadow'] if i%2==0 else ['goal_shadow','relevant_history']):
            plan.append({'id':name+'-'+arm+'-r1','case':name,'arm':arm,'repetition':1})
    if 'path' in seen:
        plan.extend({'id':'path-'+arm+'-r2','case':'path','arm':arm,'repetition':2} for arm in ['goal_shadow','relevant_history'])
    return plan
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=Path);ap.add_argument('--snapshot',action='store_true',help='Copy versioned source tree; execute returned bundle runner');ap.add_argument('--environment-lock',type=Path);ap.add_argument('--scenarios',type=Path,default=ROOT/'benchmark/longitudinal_dialogue/scenarios.json');ap.add_argument('--turn-timeout',type=float,default=420)
    a=ap.parse_args()
    import math
    if not math.isfinite(a.turn_timeout) or a.turn_timeout<=0:raise ValueError('Finite positive automatic research Turn timeout required')
    data=json.loads(a.scenarios.read_text());plan=make_plan(data)
    if a.output.resolve().is_relative_to(ROOT):raise ValueError('Keep study output outside source repository')
    fixture_paths={}
    for case in data['cases']:
        if case.get('fixture'):
            relative=Path(case['fixture'])
            if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe fixture path')
            source=(a.scenarios.parent/relative).resolve()
            if not source.is_relative_to(a.scenarios.parent.resolve()) or not source.is_file():raise ValueError('Missing fixture source')
            fixture_paths[relative]=source
    release_targets=set()
    for case in data['cases']:
        for event in case.get('fixture_releases',[]):
            if type(event.get('at_turn')) is not int or not 1<=event['at_turn']<=len(case['turns']):
                raise ValueError('Invalid fixture release turn')
            relative=Path(event.get('source',''));target=Path(event.get('target',''))
            if (not str(relative) or relative.is_absolute() or '..' in relative.parts
                    or not str(target) or target.is_absolute() or '..' in target.parts or str(target)=='.'
                    or str(target)=='ledger.md'):
                raise ValueError('Unsafe fixture release path')
            identity=(case['id'],str(target))
            if identity in release_targets:raise ValueError('Released versions must use distinct immutable targets')
            release_targets.add(identity)
            source=(a.scenarios.parent/relative).resolve()
            if not source.is_relative_to(a.scenarios.parent.resolve()) or not source.is_file():
                raise ValueError('Missing fixture release source')
            fixture_paths[relative]=source
    a.output.mkdir(parents=True,exist_ok=False)
    for relative,source in fixture_paths.items():
        target=a.output/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for name in ['sources-manifest.json','historical-user-inputs.json']:
        source=a.scenarios.parent/name
        if source.exists():shutil.copy2(source,a.output/name)
    if a.environment_lock:shutil.copy2(a.environment_lock,a.output/'environment-lock.json')
    for name,obj in [('scenarios.json',data),('plan.json',plan),('protocol.json',{'scope':data.get('kind','fixed synthetic scripts')+'; ordinary-history baseline vs existing shadow optional projection; no adoption','tool_output_chars':data.get('tool_output_chars',4000),'turn_timeout_seconds':a.turn_timeout,'sampling':'existing Harness defaults; one paired repeat is not statistical proof','permission':'test_driver; document tool only; no public transport','failure':'stop on unresolved turn or guard failure, no response retries','value':'script/contract success is not cognition or decision utility'})]:
        (a.output/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    driver=ROOT/'scripts/research/longitudinal_dialogue.py'
    if a.snapshot:
        bundle=a.output/'bundle/UAEA';bundle.mkdir(parents=True)
        for folder in ['harness','phase2','memory','backend','scripts','runtime']:
            for path in (ROOT/folder).rglob('*'):
                if not path.is_file() or '__pycache__' in path.parts or '.git' in path.parts or path.suffix not in ['.py','.json','.toml','.sh']:continue
                target=bundle/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        (a.output/'source-lock.json').write_text(json.dumps({str(p.relative_to(bundle)):hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.rglob('*') if p.is_file()},indent=2))
        (a.output/'runtime-bindings.json').write_text(json.dumps({'guard_root':str(ROOT.parent/'nemotron-bolt/records')},indent=2))
        driver=bundle/'scripts/research/longitudinal_dialogue.py'
    pins={n:hashlib.sha256((a.output/n).read_bytes()).hexdigest() for n in ['scenarios.json','plan.json','protocol.json']}
    pins[str(driver)]=hashlib.sha256(driver.read_bytes()).hexdigest()
    for p in [a.output/x for x in ['source-lock.json','runtime-bindings.json','environment-lock.json','sources-manifest.json','historical-user-inputs.json']]+[a.output/x for x in fixture_paths]:
        if p.exists():pins[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
    (a.output/'frozen.json').write_text(json.dumps(pins,indent=2))
    print(a.output)
if __name__=='__main__':main()
