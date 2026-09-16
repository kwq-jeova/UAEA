from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .event_normalizer import CANCELLED, ERROR, TURN_COMPLETED


TERMINAL_EVENT_TYPES = {TURN_COMPLETED, ERROR, CANCELLED}


class TrajectoryReadError(ValueError):
    pass


@dataclass(frozen=True)
class TrajectoryRecord:
    sequence: int
    event_type: str
    identity: dict[str, str]
    payload: dict[str, Any]
    provenance: dict[str, Any]
    raw_event_reference: dict[str, Any]
    raw_event: dict[str, Any]
    row: dict[str, Any]

    @property
    def thread_id(self) -> str:
        return self.identity.get("thread_id", "")

    @property
    def turn_id(self) -> str:
        return self.identity.get("turn_id", "")

    @property
    def item_id(self) -> str:
        return self.identity.get("item_id", "")

    @property
    def event_id(self) -> str:
        return self.identity.get("event_id", "")


@dataclass
class TurnTimeline:
    thread_id: str
    turn_id: str
    events: list[TrajectoryRecord] = field(default_factory=list)
    terminal_events: list[TrajectoryRecord] = field(default_factory=list)

    @property
    def terminal_state(self) -> str:
        if not self.terminal_events:
            return ""
        return self.terminal_events[-1].event_type


@dataclass
class TrajectoryReadResult:
    path: Path
    records: list[TrajectoryRecord]
    issues: list[str] = field(default_factory=list)

    def project_by_thread(self) -> dict[str, list[TrajectoryRecord]]:
        turn_threads = _turn_thread_index(self.records)
        threads: dict[str, list[TrajectoryRecord]] = {}
        for record in self.records:
            thread_id = record.thread_id or turn_threads.get(record.turn_id) or "unknown-thread"
            threads.setdefault(thread_id, []).append(record)
        return threads

    def reconstruct_turns(self) -> dict[tuple[str, str], TurnTimeline]:
        turn_threads = _turn_thread_index(self.records)
        timelines: dict[tuple[str, str], TurnTimeline] = {}
        for record in self.records:
            if not record.turn_id:
                continue
            key = (record.thread_id or turn_threads.get(record.turn_id) or "unknown-thread", record.turn_id)
            timeline = timelines.setdefault(
                key,
                TurnTimeline(thread_id=key[0], turn_id=key[1]),
            )
            timeline.events.append(record)
            if record.event_type in TERMINAL_EVENT_TYPES:
                timeline.terminal_events.append(record)
        return timelines


@dataclass
class TrajectoryValidationResult:
    ok: bool
    issues: list[str]
    timelines: dict[tuple[str, str], TurnTimeline]


def read_trajectory_jsonl(
    path: Path | str,
    *,
    allow_truncated_final_line: bool = False,
) -> TrajectoryReadResult:
    trajectory_path = Path(path)
    records: list[TrajectoryRecord] = []
    issues: list[str] = []
    lines = trajectory_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            is_final = index == len(lines)
            if allow_truncated_final_line and is_final:
                issues.append(f"ignored malformed final line {index}: {exc.msg}")
                break
            raise TrajectoryReadError(f"malformed JSONL line {index}: {exc.msg}") from exc
        records.append(_record_from_row(row, index))
    return TrajectoryReadResult(path=trajectory_path, records=records, issues=issues)


def validate_trajectory_records(
    records: Iterable[TrajectoryRecord],
) -> TrajectoryValidationResult:
    record_list = list(records)
    issues: list[str] = []
    last_sequence: int | None = None
    for index, record in enumerate(record_list, start=1):
        if last_sequence is not None and record.sequence <= last_sequence:
            issues.append(f"sequence is not strictly increasing at row {index}")
        last_sequence = record.sequence
        if not record.event_type:
            issues.append(f"missing event_type at row {index}")
        if not record.event_id:
            issues.append(f"missing event_id at row {index}")
        if not isinstance(record.raw_event_reference, dict):
            issues.append(f"missing raw_event_reference at row {index}")
        if not isinstance(record.raw_event, dict):
            issues.append(f"missing raw_event at row {index}")

    result = TrajectoryReadResult(path=Path(""), records=record_list)
    timelines = result.reconstruct_turns()
    for key, timeline in timelines.items():
        if not timeline.events:
            issues.append(f"empty timeline for {key}")
    return TrajectoryValidationResult(ok=not issues, issues=issues, timelines=timelines)


def _record_from_row(row: Mapping[str, Any], line_number: int) -> TrajectoryRecord:
    identity = row.get("identity")
    if not isinstance(identity, Mapping):
        raise TrajectoryReadError(f"missing identity at line {line_number}")
    sequence = row.get("sequence")
    if not isinstance(sequence, int):
        raise TrajectoryReadError(f"missing integer sequence at line {line_number}")
    event_type = row.get("event_type")
    if not isinstance(event_type, str):
        raise TrajectoryReadError(f"missing event_type at line {line_number}")
    payload = row.get("payload")
    provenance = row.get("provenance")
    raw_event_reference = row.get("raw_event_reference")
    raw_event = row.get("raw_event")
    return TrajectoryRecord(
        sequence=sequence,
        event_type=event_type,
        identity={key: str(value or "") for key, value in dict(identity).items()},
        payload=dict(payload) if isinstance(payload, Mapping) else {},
        provenance=dict(provenance) if isinstance(provenance, Mapping) else {},
        raw_event_reference=(
            dict(raw_event_reference) if isinstance(raw_event_reference, Mapping) else {}
        ),
        raw_event=dict(raw_event) if isinstance(raw_event, Mapping) else {},
        row=dict(row),
    )


def _turn_thread_index(records: Iterable[TrajectoryRecord]) -> dict[str, str]:
    index: dict[str, str] = {}
    for record in records:
        if record.turn_id and record.thread_id:
            index.setdefault(record.turn_id, record.thread_id)
    return index
