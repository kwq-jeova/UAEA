from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from .event_normalizer import (
    CANCELLED,
    ERROR,
    TURN_COMPLETED,
    HarnessEventNormalizer,
    TrajectoryEvent,
)


MAX_FILENAME_SEGMENT = 96
TERMINAL_EVENT_TYPES = {TURN_COMPLETED, ERROR, CANCELLED}


@dataclass(frozen=True)
class TrajectoryWriteResult:
    events: tuple[TrajectoryEvent, ...]
    paths: tuple[Path, ...]


@dataclass
class TrajectoryWriterStats:
    run_id: str
    event_count: int = 0
    file_count: int = 0
    paths: set[Path] = field(default_factory=set)
    event_types: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "event_count": self.event_count,
            "file_count": len(self.paths),
            "paths": [str(path) for path in sorted(self.paths)],
            "event_types": dict(sorted(self.event_types.items())),
        }


class HarnessTrajectoryWriter:
    """Write append-only normalized UAEA trajectory events as JSONL diagnostics."""

    def __init__(
        self,
        root: Path | str,
        *,
        run_id: str,
        split_by_thread: bool = False,
        normalizer: HarnessEventNormalizer | None = None,
        include_raw: bool = True,
    ) -> None:
        self.root = Path(root)
        self.run_id = _safe_segment(run_id)
        self.split_by_thread = split_by_thread
        self.normalizer = normalizer or HarnessEventNormalizer()
        self.include_raw = include_raw
        self.stats = TrajectoryWriterStats(run_id=self.run_id)
        self.root.mkdir(parents=True, exist_ok=True)
        self._handles: dict[Path, Any] = {}
        self._lock = threading.Lock()
        self._raw_index = 0
        self._thread_segments: dict[str, str] = {}
        self._used_thread_segments: dict[str, str] = {}
        self._request_threads: dict[str, str] = {}
        self._turn_threads: dict[str, str] = {}

    def write_raw_event(
        self,
        raw_event: Mapping[str, Any],
        *,
        raw_event_reference: Mapping[str, Any] | None = None,
    ) -> TrajectoryWriteResult:
        with self._lock:
            reference = dict(raw_event_reference or {})
            reference.setdefault("run_id", self.run_id)
            reference.setdefault("raw_index", self._raw_index)
            self._raw_index += 1
            events = self.normalizer.normalize(
                raw_event,
                raw_event_reference=reference,
            )
            paths: list[Path] = []
            written_events: list[TrajectoryEvent] = []
            for event in events:
                event = self._resolve_event_identity(event)
                written_events.append(event)
                row = (
                    json.dumps(
                        event.to_dict(include_raw=self.include_raw),
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n"
                )
                event_paths = self._paths_for(event)
                for path in event_paths:
                    handle = self._handle_for(path)
                    handle.write(row)
                    if event.event_type in TERMINAL_EVENT_TYPES:
                        handle.flush()
                    paths.append(path)
                self.stats.event_count += 1
                self.stats.paths.update(event_paths)
                self.stats.event_types[event.event_type] = (
                    self.stats.event_types.get(event.event_type, 0) + 1
                )
            self.stats.file_count = len(self.stats.paths)
            return TrajectoryWriteResult(events=tuple(written_events), paths=tuple(paths))

    def close(self) -> None:
        with self._lock:
            for handle in self._handles.values():
                handle.flush()
                handle.close()
            self._handles.clear()

    @property
    def canonical_path(self) -> Path:
        return self.root / f"{self.run_id}.trajectory.jsonl"

    def thread_path(self, thread_id: str) -> Path:
        return self.root / f"{self.run_id}.{self._thread_segment(thread_id)}.trajectory.jsonl"

    def _paths_for(self, event: TrajectoryEvent) -> tuple[Path, ...]:
        canonical = self.canonical_path
        if not self.split_by_thread:
            return (canonical,)
        return (canonical, self.thread_path(event.thread_id or "unknown-thread"))

    def _resolve_event_identity(self, event: TrajectoryEvent) -> TrajectoryEvent:
        if event.event_type == "PRE_TURN_CONTEXT" and event.thread_id and event.event_id:
            self._request_threads.setdefault(event.event_id, event.thread_id)

        thread_id = event.thread_id
        if not thread_id and event.turn_id:
            thread_id = self._turn_threads.get(event.turn_id, "")
        if not thread_id and event.event_id:
            thread_id = self._request_threads.get(event.event_id, "")
        if thread_id and event.turn_id:
            self._turn_threads.setdefault(event.turn_id, thread_id)
        if thread_id and thread_id != event.thread_id:
            identity = dict(event.raw_event_reference)
            identity.setdefault("identity_backfill", "writer_request_or_turn_mapping")
            return replace(
                event,
                thread_id=thread_id,
                raw_event_reference=identity,
            )
        return event

    def _thread_segment(self, thread_id: str) -> str:
        value = thread_id or "unknown-thread"
        existing = self._thread_segments.get(value)
        if existing is not None:
            return existing
        base = _safe_segment(value)
        segment = base
        owner = self._used_thread_segments.get(segment)
        if owner is not None and owner != value:
            suffix = _short_hash(value)
            max_base = max(1, MAX_FILENAME_SEGMENT - len(suffix) - 1)
            segment = f"{base[:max_base].rstrip('._-')}_{suffix}"
        self._thread_segments[value] = segment
        self._used_thread_segments[segment] = value
        return segment

    def _handle_for(self, path: Path) -> Any:
        handle = self._handles.get(path)
        if handle is None:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("a", encoding="utf-8")
            self._handles[path] = handle
        return handle

    def __enter__(self) -> "HarnessTrajectoryWriter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


def _safe_segment(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    safe = safe.strip("._") or "trajectory"
    if len(safe) <= MAX_FILENAME_SEGMENT:
        return safe
    suffix = _short_hash(value)
    max_prefix = max(1, MAX_FILENAME_SEGMENT - len(suffix) - 1)
    return f"{safe[:max_prefix].rstrip('._-')}_{suffix}"


def _short_hash(value: str) -> str:
    return sha256(value.encode("utf-8", errors="replace")).hexdigest()[:10]
