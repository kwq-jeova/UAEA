"""Optional offline S1 parts. No Runtime, Journal, permissions or model imports."""
import re
from dataclasses import dataclass,field

@dataclass
class Allowance:
    scope:set
    allowance:str='once-per-object'
    time_scope:str='未标明'
    explicit_n:int|None=None
    active:bool=True
    seen:set=field(default_factory=set)
    history:list=field(default_factory=list)
    task_focus:str|None=None

    def __post_init__(self):
        if self.allowance not in ('once-per-object','unlimited-within-scope','until-corrected','explicit-N'):
            raise ValueError('allowance unresolved')
        if not self.scope or self.time_scope not in ('本次','今后','未标明'):
            raise ValueError('scope unresolved')
        if self.allowance=='explicit-N' and (not isinstance(self.explicit_n,int) or self.explicit_n<1):
            raise ValueError('N unresolved')
        if self.time_scope=='本次':self.task_focus='本次任务例外（研究派生，不写Goal）'

    def use(self,obj,method,source_version,purpose='same-deliverable'):
        key=(obj,method,source_version)
        correction=key in self.seen # User-proposed deterministic heuristic, not semantic proof.
        if not self.active or obj not in self.scope:
            ok=False;reason='out_of_scope_or_ended'
        elif correction:ok=True;reason='same_object_method_source_correction'
        elif self.allowance in ('unlimited-within-scope','until-corrected'):
            ok=True;reason='within_scope'
        elif self.allowance=='explicit-N':
            ok=len(self.seen)<self.explicit_n;reason='explicit_N_total_distinct_successes'
        else:
            ok=not any(x[0]==obj for x in self.seen);reason='once_per_object'
        self.history.append({'object':obj,'method':method,'source_version':source_version,'purpose':purpose,'allowed_in_shadow':ok,'reason':reason})
        if ok:self.seen.add(key)
        return ok

    def end_task(self):
        if self.time_scope=='本次':self.active=False;self.task_focus=None
        self.history.append({'event':'task_end','active':self.active})

    def withdraw(self):self.active=False;self.task_focus=None;self.history.append({'event':'withdrawn'})

def revision_keyword(text):
    if any(w in text for w in ('一直','误解','纠正')):return 'misunderstanding_correction'
    if any(w in text for w in ('从现在','不再','改为')):return 'purpose_change'
    return 'refinement'

ENT=re.compile(r'(?i)NVIDIA|NVDA|AMD|Intel|英伟达|英特尔')
def entity(text,current):
    hits=list(ENT.finditer(text))
    if not hits:return current
    name=hits[-1].group().lower()
    return {'nvda':'nvidia','英伟达':'nvidia','英特尔':'intel'}.get(name,name)

NEG=re.compile(r'(?:不执行|未计算|不计算|暂停|不做|不再做).{0,12}ROA|ROA.{0,10}(?:不计算|未计算|暂停)',re.I)
VALUE=re.compile(r'ROA[^。\n；]{0,100}(?:约|≈|=|为|达到)[^。\n；]{0,20}\d+(?:\.\d+)?\s*%',re.I)
def contradictions(text):
    """Narrow explicit ROA numeric detector, not generic semantic consistency."""
    current='unspecified';negative={};values={}
    for line in re.split(r'[。\n；;]',text):
        # Split at known object mentions so AMD's permitted value cannot bind NVIDIA.
        starts=[m.start() for m in ENT.finditer(line)]
        chunks=[line[a:b]for a,b in zip([0]+starts,starts+[len(line)])if b>a] if starts else [line]
        for chunk in chunks:
            current=entity(chunk,current)
            if NEG.search(chunk):negative.setdefault(current,[]).append(chunk)
            if VALUE.search(chunk):values.setdefault(current,[]).append(chunk)
    return [{'object':obj,'method':'ROA','declaration':negative[obj],'numeric_claim':values[obj],
             'action':'one optional repair only; never reject final'}for obj in negative.keys()&values.keys()]
