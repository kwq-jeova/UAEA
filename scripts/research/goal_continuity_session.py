"""Explicit opt-in research entry. Existing Harness owns model and tool execution."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from research.goal_continuity import ContinuityJournal, PersistentGoals, import_bundle
from research.goal_sideband import ProposalApp, ProposalAdapter
from research.longitudinal_dialogue import close_with_receipt,check_guard
from h3_context_characterization import build_adapter,write_config
from h3_harness_interactive_repl import DEFAULT_CODEX_BIN

class ContinuityApp(ProposalApp):
    def __init__(self, *, continuity, **kwargs):
        super().__init__(**kwargs)
        self.goals=PersistentGoals(self.semantic_state,self.events_path.with_name('goal-events.jsonl'),continuity)
    def _handle_tool_call(self,message):
        if message.get('params',{}).get('tool')!='goal_hypothesis':
            return super()._handle_tool_call(message)
        self.goals.native_call=message['params']
        try:return super()._handle_tool_call(message)
        finally:self.goals.native_call=None

def app_for(store,out,workspace,base_url='http://127.0.0.1:8003',timeout=420):
    ad=build_adapter(out/'adapter')
    binding=next(x for x in ad.bindings if x.capability=='document.read_section')
    adapter=ProposalAdapter(ad.registry,[binding],max_output_chars=12000)
    home=out/'codex-home'
    write_config(home,base_url,65536,model='nemotron-bolt-n1x',n1x=True)
    return ContinuityApp(continuity=store,codex=DEFAULT_CODEX_BIN,codex_home=home,
        workspace=workspace,base_url=base_url,adapter=adapter,events_path=out/'app-server-events.jsonl',
        stderr_path=out/'stderr.log',turn_timeout=timeout,model='nemotron-bolt-n1x',
        reasoning_effort='none',execution_contract='shared',goal_mode='shadow',
        goal_projection='optional',input_actor='test_driver')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',type=Path,required=True)
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('init');s.add_argument('--bundle',type=Path)
    s.add_argument('--global-family',action='append',default=[])
    s=sub.add_parser('view');s.add_argument('--thread',required=True)
    s=sub.add_parser('bind-scope');s.add_argument('--family',required=True)
    s.add_argument('--scope',choices=['global','local'],required=True);s.add_argument('--basis',required=True)
    s=sub.add_parser('note');s.add_argument('--text',required=True)
    s.add_argument('--failure-class',choices=['none','store','projection','semantics','reference','conceptual','unknown'],default='unknown')
    s=sub.add_parser('turn');s.add_argument('--output',type=Path,required=True)
    s.add_argument('--guard',type=Path,required=True);s.add_argument('--input',type=Path,required=True)
    a=p.parse_args()
    with ContinuityJournal(a.profile,create=a.command=='init') as store:
        if a.command=='init':
            print(json.dumps({'imported':import_bundle(store,a.bundle,global_families=a.global_family) if a.bundle else False,
                'versions':len(store.versions),'journal':str(store.path)}))
        elif a.command=='view':print(json.dumps(store.view(a.thread),ensure_ascii=False,indent=2))
        elif a.command=='bind-scope':store.bind_scope(a.family,a.scope,a.basis)
        elif a.command=='note':store.annotate(a.text,failure_class=a.failure_class)
        else:
            # This command references an already-owned guarded service. It never launches one.
            check_guard(a.guard)
            a.output.mkdir(parents=True,exist_ok=False)
            app=app_for(store,a.output,(a.output/'adapter/sandbox').resolve())
            try:
                app.start();app.run_turn(a.input.read_text())
                (a.output/'stop-snapshot.json').write_text(json.dumps(app.semantic_state.snapshot(app.thread_id),ensure_ascii=False,indent=2))
            finally:
                (a.output/'cleanup.json').write_text(json.dumps(close_with_receipt(app,None,None)))
if __name__=='__main__':main()
