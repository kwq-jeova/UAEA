from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.runtime_objects import RuntimeObjectRecord, RuntimeObjectStore, utc_now


SCOPES = {"turn", "task", "cross_task", "explicit_until_revoked"}
_PRIORITY = {"cross_task": 0, "explicit_until_revoked": 0, "task": 1, "turn": 2}


@dataclass(frozen=True)
class EffectiveSemanticState:
    resolution_id: str
    items: tuple[RuntimeObjectRecord, ...]

    @property
    def constraints(self) -> list[str]:
        return [str(item.metadata["value"]) for item in self.items
                if item.metadata["kind"] == "capability_constraint"]

    def values(self, kind: str) -> list[str]:
        return [str(item.metadata["value"]) for item in self.items
                if item.metadata["kind"] == kind]


class ScopedSemanticResolver:
    """Semantic metadata/lifecycle extension of Phase-1 object records."""

    def __init__(self, store: RuntimeObjectStore) -> None:
        self.store = store

    def bind(
        self, *, kind: str, key: str, value: str, scope: str, owner: str,
        provenance: Mapping[str, Any], strength: str = "hard",
    ) -> RuntimeObjectRecord:
        if scope not in SCOPES:
            raise ValueError(f"Unsupported semantic scope: {scope}")
        record = RuntimeObjectRecord(
            object_type="semantic_item", owner=owner, status="active",
            source_event_ids=[str(provenance.get("event_id") or "")],
            metadata={"kind": kind, "key": key, "value": value, "scope": scope,
                      "strength": strength, "provenance": dict(provenance)},
        )
        for previous in self.items():
            if (previous.status == "active" and previous.owner == owner
                    and previous.metadata["scope"] == scope
                    and previous.metadata["key"] == key):
                previous.status = "superseded"
                previous.metadata["superseded_by"] = record.object_id
                previous.updated_at = utc_now()
        self.store.objects.append(record)
        return record

    def items(self) -> list[RuntimeObjectRecord]:
        return [item for item in self.store.objects if item.object_type == "semantic_item"]

    def expire_turn(self, input_id: str) -> None:
        for item in self.items():
            if (item.status == "active" and item.metadata["scope"] == "turn"
                    and item.owner == input_id):
                self._expire(item, "turn_terminal_boundary")

    def revoke_constraints(self, *, owner: str, provenance: Mapping[str, Any]) -> None:
        for item in self.items():
            if (item.status == "active" and item.owner == owner
                    and item.metadata["kind"] == "capability_constraint"):
                self._expire(item, "explicit_revocation")
                item.metadata["revocation_provenance"] = dict(provenance)

    def resolve(self, *, task_id: str, input_id: str) -> EffectiveSemanticState:
        chosen: dict[str, RuntimeObjectRecord] = {}
        for item in self.items():
            if item.status != "active":
                continue
            scope = item.metadata["scope"]
            if scope == "turn" and item.owner != input_id:
                self._expire(item, "turn_scope_changed")
                continue
            if scope == "task" and item.owner != task_id:
                self._expire(item, "task_owner_inactive")
                continue
            key = str(item.metadata["key"])
            previous = chosen.get(key)
            if previous is None or _PRIORITY[scope] >= _PRIORITY[previous.metadata["scope"]]:
                chosen[key] = item
        items = tuple(chosen.values())
        identity = json.dumps([task_id, input_id, [item.object_id for item in items]])
        resolution_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        return EffectiveSemanticState(resolution_id, items)

    @staticmethod
    def _expire(item: RuntimeObjectRecord, reason: str) -> None:
        item.status = "expired"
        item.metadata["lifecycle_reason"] = reason
        item.updated_at = utc_now()
