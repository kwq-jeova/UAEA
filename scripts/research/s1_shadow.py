"""S1 offline research. No Runtime, model, Journal, SQLite or network imports.

Support-score filtering is NOT a calibrated generative Bayesian posterior.
Callers supply as-of, manually audited observations; no text parser grants scope.
"""
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
import math

TYPES = ('D', 'X', 'C', 'R', 'N')

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def as_of(records, time):
    """Reject (do not silently hide) requested future versions/source records."""
    records = list(records)
    if isinstance(time,bool) or not isinstance(time,(int,float)) or not math.isfinite(time):
        raise ValueError('TIME')
    for r in records:
        stamp=r['available_at']
        if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not math.isfinite(stamp):
            raise ValueError('TIME')
        if r['available_at'] > time:
            raise ValueError('FUTURE_RECORD')
        if not r.get('id') or not r.get('source_id'):
            raise ValueError('MISSING_IDENTITY')
    return list(records)

def normalize(values):
    if any(not math.isfinite(x) or x < 0 for x in values) or sum(values) <= 0:
        raise ValueError('INVALID_MASS')
    total = sum(values)
    return [x / total for x in values]

def transition(states, hazard):
    if not 0 <= hazard < 1:
        raise ValueError('HAZARD')
    candidates = [s for s in states if s not in ('H0', 'HU')]
    weights = {'H0': .2, 'HU': .5, **{s: .3 / len(candidates) for s in candidates}}
    result = []
    for source in states:
        den = sum(weights[s] for s in states if s != source)
        result.append([1-hazard if s == source else hazard*weights[s]/den for s in states])
    return result

@dataclass(frozen=True)
class Observation:
    evidence_unit: str
    kind: str
    targets: tuple
    polarity: str
    scope_marker: str
    quote: str
    interpretation_scope: str

class Filter:
    def __init__(self, candidates, scope, eta=.05, h_task=.05, h_in=.01):
        if not 0 <= len(candidates) <= 3 or len(set(candidates)) != len(candidates):
            raise ValueError('CANDIDATES')
        if any(x in ('H0','HU') for x in candidates) or not scope:
            raise ValueError('SCOPE_OR_CANDIDATE')
        if not .05 <= eta < .5:
            raise ValueError('ETA')
        self.states = ['H0', *candidates, 'HU']
        self.scope, self.eta = scope, eta
        self.h_task, self.h_in = h_task, h_in
        transition(self.states,h_task); transition(self.states,h_in)
        self.b = [.8, *[.15/len(candidates)]*len(candidates), .05] if candidates else [.95,.05]
        self.seen = set()

    def update(self, obs, boundary=False):
        if obs.evidence_unit in self.seen:
            raise ValueError('DUPLICATE_EVIDENCE_UNIT')
        if (not obs.evidence_unit or not obs.quote or obs.kind not in TYPES
            or obs.polarity not in ('+', '-', '0')
            or obs.scope_marker not in ('this', 'future', 'unmarked')
            or obs.interpretation_scope != self.scope
            or any(s not in self.states[1:-1] for s in obs.targets)):
            raise ValueError('OBSERVATION')
        if obs.kind in ('D','R') and (not obs.targets or obs.polarity not in ('+','-')):
            raise ValueError('AMBIGUOUS_TARGET_OR_POLARITY')
        if obs.kind == 'R' and obs.polarity != '+':
            raise ValueError('NEGATIVE_R_NOT_DEFINED')
        self.seen.add(obs.evidence_unit)
        if obs.kind == 'X':
            return list(self.b)  # Deliberate event-clock convention: no transition either.
        mat = transition(self.states, self.h_task if boundary else self.h_in)
        predicted = [sum(self.b[i]*mat[i][j] for i in range(len(self.b))) for j in range(len(self.b))]
        if obs.kind == 'D':
            cons = [float(s not in obs.targets) if obs.polarity == '-' else float(s in obs.targets) for s in self.states]
        elif obs.kind == 'R':
            cons = [1. if s in obs.targets else .3 for s in self.states]
        else:
            cons = [1.] * len(self.states)
        scores = [self.eta+(1-2*self.eta)*c for c in cons]
        self.b = normalize([p*l for p,l in zip(predicted,scores)])
        return list(self.b)

def confusion(pairs, alpha=1.):
    """Rows are adjudicated true type; columns fixed-classifier output. Not emissions."""
    if alpha <= 0:
        raise ValueError('SMOOTHING')
    counts = [[0]*5 for _ in TYPES]
    for truth, predicted in pairs:
        counts[TYPES.index(truth)][TYPES.index(predicted)] += 1
    return {'counts':counts, 'row_support':[sum(r) for r in counts],
            'probabilities':[normalize([x+alpha for x in r]) for r in counts]}

@dataclass
class ExceptionRecord:
    id: str
    scope: str
    allowed_action_class: str
    source_event: str
    status: str = 'unused'
    use_call_id: str = ''
    completion_event: str = ''

class Exceptions:
    """Offline bookkeeping only. start() simulates a proposed use, never executes."""
    def __init__(self):
        self.records = {}

    def add(self, id, scope, action, source_event):
        if not all((id,scope,action,source_event)) or id in self.records:
            raise ValueError('UNRESOLVED_OR_DUPLICATE_EXCEPTION')
        self.records[id] = ExceptionRecord(id,scope,action,source_event)

    def start(self, id, scope, action, call_id):
        r = self.records[id]
        if not call_id:
            raise ValueError('MISSING_CALL')
        if (r.scope,r.allowed_action_class)==(scope,action) and r.use_call_id==call_id:
            return False  # Same original event replay: do not execute or consume again.
        if (r.scope,r.allowed_action_class,r.status) != (scope,action,'unused'):
            raise ValueError('REUSE_OR_WRONG_SCOPE')
        r.status = 'in_use'
        r.use_call_id = call_id
        return True

    def finish_use(self, id, call_id, verified_success, completion_event):
        r = self.records[id]
        if r.status != 'in_use' or r.use_call_id != call_id:
            raise ValueError('NOT_IN_USE')
        if verified_success is not True or not completion_event:
            raise ValueError('SUCCESS_NOT_ESTABLISHED')
        r.status = 'consumed'
        r.completion_event = completion_event

    def end_scope(self, scope):
        for r in self.records.values():
            if r.scope == scope and r.status in ('unused','in_use'):
                r.status = 'expired' # Scope ended without verified successful use.

    def snapshot(self):
        value = [asdict(self.records[k]) for k in sorted(self.records)]
        return value, sha256(canonical(value).encode()).hexdigest()

    @classmethod
    def restore(cls, value, expected_digest, expected_ids):
        # Expected digest/IDs must come from the original checkpoint, not the received blob.
        if sha256(canonical(value).encode()).hexdigest() != expected_digest:
            raise ValueError('HANDOFF_CORRUPT')
        obj = cls()
        for raw in value:
            r = ExceptionRecord(**raw)
            if r.status not in ('unused','in_use','consumed','expired'):
                raise ValueError('STATUS')
            if (r.status == 'consumed' and (not r.use_call_id or not r.completion_event)) or (r.status == 'in_use' and not r.use_call_id):
                raise ValueError('MISSING_USE_EVIDENCE')
            obj.add(r.id,r.scope,r.allowed_action_class,r.source_event)
            obj.records[r.id] = r
        if set(obj.records) != set(expected_ids):
            raise ValueError('HANDOFF_INCOMPLETE')
        return obj
