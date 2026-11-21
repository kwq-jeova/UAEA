"""Bind Codex additional-context items to Host publications before replacing them.

The private rollout carries the origin marker that is omitted from the provider
wire. Input from either side alone is insufficient. Never edit the rollout.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from threading import Lock


# These are untrusted additionalContext keys actually published by UAEA.
# Codex derives the tool label by removing punctuation from the key.
KEYS = ("uaea.goal_hypotheses", "uaea.retained_user_requests",
        "uaea.semantic_interpretations", "uaea.semantic_state_projection")
NAMES = {key.replace(".", ""): key for key in KEYS}


def _bounded(value: str) -> str:
    # Codex 0.170 truncate_middle_with_token_budget: 1,000 approximate tokens,
    # using UTF-8 boundaries and four bytes per approximate token.
    raw = value.encode("utf-8")
    if len(raw) <= 4000:
        return value
    marker = f"…{(len(raw) - 4000 + 3) // 4} tokens truncated…"
    return raw[:2000].decode("utf-8", "ignore") + marker + raw[-2000:].decode("utf-8", "ignore")


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _key(item):
    if not isinstance(item, dict) or item.get("type") != "function_call_output":
        return None
    if item.get("namespace") != "agent" or item.get("call_id") is not None:
        return None
    return NAMES.get(item.get("name")) if isinstance(item.get("name"), str) else None


def _publication(blocks):
    result = {}
    for key in KEYS:
        entry = blocks.get(key)
        if isinstance(entry, dict) and entry.get("kind") == "untrusted" and isinstance(entry.get("value"), str):
            result[key] = _digest(_bounded(entry["value"]))
    return result


def _wire_digest(item):
    return _digest(json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


@dataclass(frozen=True)
class _Origin:
    turn: str | None
    digest: str
    context_output: bool
    message_kind: str | None


class NativeContextIndex:
    """One index per trusted Thread and rollout. Only operate on provider copies."""

    def __init__(self, path: Path | None, thread_id: str):
        self.path = path
        self.thread_id = thread_id
        self._publications = {}
        self._verified = {}
        self._lock = Lock()
        self._entries = {}
        self._offset = 0
        self._inode = None
        self._mtime = None
        self._turn = None

    def register_publication(self, turn_id, blocks):
        """Optional sealed Host witness for an earlier Turn of this Thread.

        Caller must verify Thread, Turn and Host source before registration.
        Values are the unbounded, original published blocks, never model text.
        """
        if not isinstance(turn_id, str) or not turn_id:
            raise ValueError("Host publication requires its original Turn")
        witness = _publication(blocks)
        with self._lock:
            existing = self._publications.get(turn_id)
            if existing is not None and existing != witness:
                raise ValueError("Conflicting archived Host publication")
            self._publications[turn_id] = witness

    def _refresh(self):
        """Index only appended complete lines of this Harness-owned rollout."""
        if self.path is None:
            return "rollout_unavailable"
        try:
            with self.path.open("rb") as stream:
                info = os.fstat(stream.fileno())
                inode = (info.st_dev, info.st_ino)
                if (inode != self._inode or info.st_size < self._offset
                        or (info.st_size == self._offset and info.st_mtime_ns != self._mtime)):
                    self._entries.clear()
                    self._verified.clear()
                    self._offset = 0
                    self._inode = inode
                    self._turn = None
                if not self._offset:
                    line = stream.readline()
                    if not line.endswith(b"\n"):
                        return "rollout_header_incomplete"
                    first = json.loads(line)
                    if first.get("type") != "session_meta" or first["payload"].get("id") != self.thread_id:
                        return "rollout_thread_mismatch"
                    self._offset = stream.tell()
                else:
                    stream.seek(self._offset)
                while self._offset < info.st_size:
                    # Limit the read to the file snapshot obtained above. A
                    # concurrent append belongs to the next refresh.
                    raw = stream.readline(info.st_size - self._offset)
                    if not raw.endswith(b"\n"):
                        break
                    row = json.loads(raw)
                    payload = row.get("payload", {})
                    kind = row.get("type")
                    if kind == "session_meta":
                        return "multiple_rollout_sessions"
                    if kind == "event_msg":
                        if payload.get("type") == "task_started":
                            self._turn = payload.get("turn_id")
                        elif payload.get("type") in ("task_complete", "turn_aborted"):
                            self._turn = None
                    if kind == "response_item" and isinstance(payload.get("id"), str):
                        uid = payload["id"]
                        if uid in self._entries:
                            self._entries[uid] = None
                        else:
                            # The caller receives only the wire payload, not these
                            # trusted Native annotations. Bind both during indexing.
                            origin = payload.get("internal_chat_message_metadata_passthrough") or {}
                            kinds = origin.get("content_item_kinds")
                            marker = row.get("metadata") or {}
                            wire = {k: v for k, v in payload.items() if k != "internal_chat_message_metadata_passthrough"}
                            self._entries[uid] = _Origin(
                                self._turn if self._turn and origin.get("turn_id") == self._turn else None,
                                _wire_digest(wire), marker.get("additional_context_tool_output") is True,
                                kinds[0] if isinstance(kinds, list) and len(kinds) == 1 else None,
                            )
                    self._offset = stream.tell()
                self._mtime = info.st_mtime_ns
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return "rollout_unavailable_or_invalid"
        return ""

    def xml_source(self, item, key):
        """Classify a complete XML message only by matching its trusted rollout row."""
        uid = item.get("id")
        if not isinstance(uid, str) or item.get("type", "message") != "message":
            return "unknown"
        with self._lock:
            if self._refresh():
                return "unknown"
            origin = self._entries.get(uid)
            if not origin or not origin.turn or origin.digest != _wire_digest(item):
                return "unknown"
            if origin.message_kind == "additional_content." + key:
                return "host"
            if origin.message_kind == "user.text":
                return "user"
            return "unknown"

    def normalize(self, request, blocks):
        """Return (transport projection, per-item classifications). Unknowns survive."""
        fields = ("input", "previous_input_messages")
        suspects = [(field, n, item, _key(item)) for field in fields
                    if isinstance(request.get(field), list)
                    for n, item in enumerate(request[field]) if _key(item)]
        if not suspects:
            return request, []
        metadata = request.get("client_metadata") or {}
        current = None
        if isinstance(metadata, dict) and metadata.get("thread_id") == self.thread_id:
            if isinstance(metadata.get("turn_id"), str):
                current = metadata["turn_id"]
        wanted = {item["id"] for _, _, item, _ in suspects if isinstance(item.get("id"), str) and item["id"]}
        # Include non-context records in duplicate checks. A real tool receipt with
        # a conflicting identity must survive and the comparison must flag ambiguity.
        counts = {f: Counter(x["id"] for x in request[f] if isinstance(x, dict) and isinstance(x.get("id"), str))
                  for f in fields if isinstance(request.get(f), list)}
        # A cross-field copy is legitimate only if both occurrences agree.
        seen = {}
        conflicted = set()
        for field in counts:
            for entry in request[field]:
                uid = entry.get("id") if isinstance(entry, dict) else None
                if isinstance(uid, str) and uid in wanted and seen.setdefault(uid, entry) != entry:
                    conflicted.add(uid)
        remove = {field: set() for field in fields}
        decisions = []
        witness = _publication(blocks)
        with self._lock:
            unavailable = self._refresh()
            for field, n, item, key in suspects:
                uid = item.get("id")
                record = self._entries.get(uid) if isinstance(uid, str) and not unavailable else None
                origin = record.turn if record else None
                relation = "unknown" if not (origin and current) else ("current" if origin == current else "historical")
                reason = None
                if not current:
                    reason = "request_thread_or_turn_unbound"
                elif not record or not origin or not record.context_output:
                    reason = unavailable or "native_origin_unverified"
                elif counts[field][uid] != 1 or uid in conflicted or record.digest != _wire_digest(item) or not isinstance(item.get("output"), str):
                    reason = "native_item_identity_conflict"
                else:
                    signature = (origin, key, _digest(item["output"]))
                    archived = self._publications.get(origin, {})
                    already_bound = self._verified.get(uid)
                    if already_bound is not None and already_bound != signature:
                        reason = "native_item_identity_conflict"
                    elif (already_bound != signature and archived.get(key) != signature[2]
                          and not (relation == "current" and witness.get(key) == signature[2])):
                        reason = ("historical_publication_unavailable" if relation == "historical"
                                  else "current_publication_mismatch")
                    else:
                        self._verified[uid] = signature
                        remove[field].add(n)
                decisions.append({"key": key, "item_id": uid, "origin_turn_id": origin, "relation": relation,
                                  "status": "unresolved" if reason else "removed", "reason": reason or "verified_host_publication",
                                  "field": field, "index": n})
        projected = dict(request)
        for field, indices in remove.items():
            if indices:
                projected[field] = [x for i, x in enumerate(request[field]) if i not in indices]
        return projected, decisions
