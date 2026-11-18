"""Research-only budget decisions; no I/O, model calls, retries, or Agent Loop.

The driver remains responsible for checking Guard, observing actual Native/SSE
progress, and passing native completion. A wait timeout is not native failure.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
import time
import threading
from functools import wraps


def _locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


@dataclass(frozen=True)
class BudgetConfig:
    soft_seconds: float
    hard_seconds: float
    no_progress_seconds: float
    max_requests: int

    def __post_init__(self):
        values = (self.soft_seconds, self.hard_seconds, self.no_progress_seconds)
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError("Budget seconds must be finite positive numbers")
        if self.soft_seconds > self.hard_seconds:
            raise ValueError("Soft budget cannot exceed hard limit")
        if isinstance(self.max_requests, bool) or not isinstance(self.max_requests, int) or self.max_requests < 1:
            raise ValueError("max_requests must be a positive integer")


@dataclass(frozen=True)
class Decision:
    action: str                 # continue / stop / observe_only
    status: str                 # running / completed / budget_stop / ...
    reason: str
    elapsed: float
    since_progress: float
    request_count: int
    progress_count: int
    soft_reached: bool
    request_allowed: bool = False
    completed_observed: bool = False

    def to_dict(self):
        return asdict(self)


class BudgetPolicy:
    # Notification/heartbeat/log-file growth alone is intentionally absent.
    PROGRESS_KINDS = frozenset({
        "output_delta", "tool_result", "provider_completed",
        "compaction_completed", "native_item_completed",
    })

    def __init__(self, config, *, clock=time.monotonic):
        self._lock = threading.RLock()
        self.config = config
        self.clock = clock
        self.started = self.last_progress = self._last_clock = self._read_clock()
        self.request_ids = set()
        self.progress_ids = {}
        self.progress_count = 0
        self.events = []
        self.terminal = None
        self.first_terminal = None

    def _read_clock(self):
        now = self.clock()
        if not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("Clock must return a finite monotonic value")
        return float(now)

    def _now(self):
        now = self._read_clock()
        if now < self._last_clock:
            raise ValueError("Clock moved backwards")
        self._last_clock = now
        return now

    def _decision(self, now, action, status, reason, *, request_allowed=False,
                  completed=False):
        return Decision(action, status, reason, now - self.started,
                        now - self.last_progress, len(self.request_ids),
                        self.progress_count,
                        now - self.started >= self.config.soft_seconds,
                        request_allowed, completed)

    @_locked
    def note_progress(self, kind, identity, payload):
        """Record new substantive evidence/event, not task completion.

        The caller must use genuine event identity, not a polling timestamp.
        Re-observation of the same kind/identity never refreshes inactivity.
        A conflicting re-use of identity raises instead of silently replacing it.
        Progress is an execution fact only; it does not certify a good answer.
        """
        now = self._now()
        if self.terminal is not None:
            return False
        if kind not in self.PROGRESS_KINDS:
            self.events.append({"event": "non_progress_ignored", "kind": kind, "at": now})
            return False
        if not isinstance(identity, str) or not identity:
            raise ValueError("Progress requires an actual non-empty event identity")
        if payload is None or payload == "" or payload == {} or payload == []:
            return False
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
        key = (kind, identity)
        previous = self.progress_ids.get(key)
        if previous:
            if previous != fingerprint:
                raise ValueError("Progress identity reused with different content")
            return False
        self.progress_ids[key] = fingerprint
        self.progress_count += 1
        self.last_progress = now
        self.events.append({"event": "progress", "kind": kind, "identity": identity,
                            "payload_sha256": fingerprint, "at": now})
        return True

    @_locked
    def evaluate(self, *, completed=False, guard_failure=None,
                 execution_failure=None, external_interrupt=None,
                 request_requested=False):
        """Check resource safety first, then observed terminal facts and budgets.

        Already-observed native completion wins ordinary budget checks, so a
        poll arriving just after a deadline does not invent a failed delivery.
        No work may continue past a hard limit when no terminal was observed.
        Guard failure remains a stop even if completion was observed together.
        """
        now = self._now()
        if guard_failure is not None:
            result = self._decision(now, "stop", "safety_stop",
                                    "guard_failure:" + str(guard_failure),
                                    completed=completed)
        elif self.terminal is not None:
            return self.terminal
        elif execution_failure is not None:
            result = self._decision(now, "stop", "execution_fault", str(execution_failure),
                                    completed=completed)
        elif external_interrupt is not None:
            result = self._decision(now, "stop", "external_interruption", str(external_interrupt),
                                    completed=completed)
        elif completed:
            result = self._decision(now, "stop", "completed", "native_completed",
                                    completed=True)
        elif now - self.started >= self.config.hard_seconds:
            result = self._decision(now, "stop", "budget_stop", "hard_time_limit")
        elif now - self.last_progress >= self.config.no_progress_seconds:
            result = self._decision(now, "stop", "budget_stop", "no_progress_limit")
        elif request_requested and len(self.request_ids) >= self.config.max_requests:
            result = self._decision(now, "stop", "budget_stop", "request_limit")
        else:
            reason = ("soft_budget_progress_continuation" if self.progress_count else "soft_budget_waiting_within_idle_limit") if now-self.started >= self.config.soft_seconds else "within_soft_budget"
            return self._decision(now, "continue", "running", reason)
        self.events.append({"event": "terminal_decision", **result.to_dict()})
        if self.first_terminal is None:
            self.first_terminal = result
        self.terminal = result
        return result

    @_locked
    def begin_request(self, request_id, **conditions):
        """Admission bookkeeping only. Never sends or re-sends anything.

        Duplicate identity is observe_only, not permission for another request.
        The cap applies to starting the next request, not reading an in-flight
        response. Call evaluate while the last admitted request remains active.
        """
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("Request needs non-empty actual identity")
        result = self.evaluate(request_requested=False, **conditions)
        if result.action == "stop":
            return result
        if request_id in self.request_ids:
            return self._decision(self._now(), "observe_only", "running",
                                  "duplicate_request_not_admitted")
        result = self.evaluate(request_requested=True, **conditions)
        if result.action == "stop":
            return result
        self.request_ids.add(request_id)
        now = self._now()
        self.events.append({"event": "request_admitted", "request_id": request_id, "at": now})
        return self._decision(now, "continue", "running", "request_admitted", request_allowed=True)

    @_locked
    def snapshot(self):
        now = self._now()
        return {
            "config": asdict(self.config),
            "elapsed": now-self.started,
            "since_progress": now-self.last_progress,
            "request_ids": sorted(self.request_ids),
            "progress_count": self.progress_count,
            "terminal": None if self.terminal is None else self.terminal.to_dict(),
            "first_terminal": None if self.first_terminal is None else self.first_terminal.to_dict(),
            "scope": "budget_and_progress_facts_not_task_completion_or_semantic_success",
        }
