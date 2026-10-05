from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


AUDIT_SCHEMA = "uaea.semantic_promotion_shadow_audit.v0"


def build_promotion_audit(
    snapshot: Mapping[str, Any],
    *,
    stage: str,
    additional_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe existing surfaces; never infer intent, grant authority, or mutate state."""
    projection = _mapping(snapshot.get("last_projection"))
    transport_kind = "UNKNOWN"
    if additional_context is not None:
        entry = _mapping(additional_context.get("uaea.semantic_state_projection"))
        transport_kind = str(entry.get("kind") or "UNKNOWN")
        value = entry.get("value")
        if isinstance(value, str):
            projection = _mapping(json.loads(value))
        else:
            projection = {}

    effective_ids = snapshot.get("effective_semantic_item_ids")
    membership_known = isinstance(effective_ids, list)
    effective_ids = set(effective_ids or [])
    bindings = projection.get("semantic_bindings")
    projection_membership_known = isinstance(bindings, list)
    projected_ids = {item.get("item_id") for item in bindings or []}
    current_constraints = snapshot.get("constraints") or []
    projected_constraints = projection.get("constraints") or []
    interpretation_entry = _mapping((additional_context or {}).get("uaea.semantic_interpretations"))
    interpretation_context = (
        _mapping(json.loads(interpretation_entry["value"]))
        if isinstance(interpretation_entry.get("value"), str) else {}
    )
    interpretation_bindings = interpretation_context.get("interpretations")
    interpretation_ids = {item.get("item_id") for item in interpretation_bindings or []}
    items = []
    for record in snapshot.get("semantic_items") or []:
        record = _mapping(record)
        metadata = _mapping(record.get("metadata"))
        provenance = _mapping(metadata.get("provenance"))
        value = str(metadata.get("value") or "")
        item_id = str(record.get("object_id") or "")
        kind = str(metadata.get("kind") or "")
        strength = str(metadata.get("strength") or "")
        effective = item_id in effective_ids if membership_known else None
        current_value_present = kind == "capability_constraint" and value in current_constraints
        projected_value_present = kind == "capability_constraint" and value in projected_constraints
        constraint_surface = current_value_present and effective if membership_known else None
        in_projection = (projected_value_present and item_id in projected_ids
                         if projection_membership_known else None)
        notices = []
        if (constraint_surface or in_projection) and not metadata.get("promotion_basis"):
            notices.append("PROMOTION_BASIS_NOT_RECORDED")
        if strength == "soft" and (constraint_surface or in_projection):
            notices.append("SOFT_ITEM_IN_CONSTRAINT_SURFACE")
        if in_projection and transport_kind == "application":
            notices.append("CONSTRAINT_IN_APPLICATION_CONTEXT")
        if current_value_present and not membership_known:
            notices.append("VALUE_ON_CONSTRAINT_SURFACE_MEMBERSHIP_UNKNOWN")
        items.append({
            "semantic_item_id": item_id,
            "kind": kind,
            "value_sha256": _digest(value),
            "declared_strength": strength,
            "declared_authority_level": metadata.get("authority_level", "UNKNOWN"),
            "lifecycle_status": record.get("status"),
            "owner": record.get("owner"),
            "scope": metadata.get("scope"),
            "effective_member": effective,
            "value_in_current_constraints": current_value_present,
            "value_in_last_projection_constraints": projected_value_present,
            "in_current_constraint_surface": constraint_surface,
            "in_last_projection_constraint_surface": in_projection,
            "in_interpretation_projection": (
                item_id in interpretation_ids if isinstance(interpretation_bindings, list) else None
            ),
            "promotion_basis": "RECORDED" if metadata.get("promotion_basis") else "NOT_RECORDED",
            "promotion_reference": {
                key: value for key, value in _mapping(metadata.get("promotion_basis")).items()
                if key in {"type", "input_id", "key"}
            },
            "source": {
                "producer_label": provenance.get("source"),
                "identity": {key: provenance.get(key, "") for key in (
                    "thread_id", "turn_id", "item_id", "event_id", "input_id",
                )},
                "raw_event_reference": {
                    key: reference for key, reference in
                    _mapping(provenance.get("raw_event_reference")).items()
                    if key in {"path", "artifact", "line", "raw_index", "method", "run_id"}
                },
                "excerpt_sha256": _digest(str(provenance.get("source_text_excerpt") or "")),
            },
            "superseded_by": metadata.get("superseded_by", ""),
            "lifecycle_reason": metadata.get("lifecycle_reason", ""),
            "notices": notices,
        })

    decisions = []
    for decision in snapshot.get("action_decisions") or []:
        decision = _mapping(decision)
        authorization = _mapping(decision.get("authorization"))
        decisions.append({
            "validation_boundary": "semantic_state_action_validation",
            "thread_id": decision.get("thread_id"),
            "turn_id": decision.get("turn_id"),
            "call_id": decision.get("call_id"),
            "capability": decision.get("capability"),
            "valid": decision.get("valid"),
            "effective_state_id": decision.get("effective_state_id"),
            "constraint_snapshot_item_ids": [
                item.get("object_id") for item in decision.get("semantic_items") or []
            ],
            "authorization_state": authorization.get("state", "unknown"),
            "authorization_subject": (
                "fallback_permission" if decision.get("capability") == "web.search" else "UNKNOWN"
            ),
            "conflict_count": len(decision.get("conflicts") or []),
            "policy_time": "at_attempt",
        })

    return {
        "schema": AUDIT_SCHEMA,
        "mode": "SHADOW_ONLY",
        "stage": stage,
        "thread_id": snapshot.get("thread_id"),
        "turn_id": "" if stage == "PRE_TURN" else snapshot.get("last_turn_id", ""),
        "prior_turn_id": snapshot.get("last_turn_id", "") if stage == "PRE_TURN" else "",
        "input_id": snapshot.get("current_input_id", ""),
        "task_id": snapshot.get("task_id"),
        "effective_state_id": snapshot.get("effective_state_id"),
        "effective_membership_known": membership_known,
        "projection": {
            "effective_state_id": projection.get("effective_state_id"),
            "projection_id": (snapshot.get("projection_ids") or [""])[-1],
            "transport_kind": transport_kind,
            "interpretation_transport_kind": interpretation_entry.get("kind", "UNKNOWN"),
            "delivery": "PREPARED_NOT_CONFIRMED" if additional_context is not None else "UNKNOWN",
            "item_membership_known": projection_membership_known,
            "payload_sha256": _digest(json.dumps(projection, ensure_ascii=False, sort_keys=True)),
            "is_current_effective_state": (
                projection.get("effective_state_id") == snapshot.get("effective_state_id")
                if projection.get("effective_state_id") else None
            ),
        },
        "items": items,
        "observed_validation_decisions": decisions,
        "limits": {
            "intent_correctness": "NOT_EVALUATED",
            "authority_warrant": "NOT_EVALUATED",
            "constraint_surface_is_not_enforcement_proof": True,
            "validation_snapshot_is_not_per_item_enforcement_proof": True,
            "validation_acceptance_is_not_execution_proof": True,
            "last_projection_is_not_current_policy": True,
            "provenance_is_not_correctness": True,
            "grants_authority": False,
            "changes_model_context": False,
        },
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest()
