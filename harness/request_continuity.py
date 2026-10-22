"""User input lineage on Phase-1 records; no request interpreter or executor."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


REQUEST_OPERATIONS = frozenset({"retain", "append", "replace", "cancel"})


def parse_request_operation(text: str) -> str:
    """Explicit user controls only. Ordinary language remains uninterpreted."""
    if not text.startswith("/request "):
        return "retain"
    parts = text.split(maxsplit=2)
    operation = parts[1] if len(parts) > 1 else ""
    if (operation not in {"append", "replace", "cancel"}
            or (operation != "cancel" and len(parts) != 3)
            or (operation == "cancel" and len(parts) != 2)):
        raise ValueError("Use /request append <text>, /request replace <text>, or /request cancel")
    return operation


def request_inputs(store, workflow_id: str):
    return [item for item in store.objects
            if item.object_type == "workflow_request_input" and item.owner == workflow_id]


def retain_request_input(store, workflow_id: str, *, input_id: str, text: str,
                         provenance: Mapping[str, Any], operation: str = "retain"):
    from runtime.runtime_objects import RuntimeObjectRecord, utc_now

    if operation not in REQUEST_OPERATIONS:
        raise ValueError("Unsupported request operation")
    records = request_inputs(store, workflow_id)
    existing = next((item for item in records if item.object_id == input_id), None)
    if existing is not None:
        return existing
    if operation in {"replace", "cancel"}:
        for item in records:
            if item.status in {"retained", "context_only"}:
                item.status = "superseded" if operation == "replace" else "cancelled"
                item.metadata["ended_by_input_id"] = input_id
                item.updated_at = utc_now()
    controls = [item for item in records if item.metadata["operation"] != "retain"]
    cancelled = bool(controls and controls[-1].metadata["operation"] == "cancel")
    status = ("cancelled" if operation == "cancel" else "context_only"
              if operation == "retain" and cancelled else "retained")
    item = RuntimeObjectRecord(
        object_type="workflow_request_input", object_id=input_id, owner=workflow_id,
        status=status, source_event_ids=[str(provenance.get("event_id") or input_id)],
        metadata={"text": text, "input_id": input_id, "operation": operation,
                  "authority_level": "interpretation", "provenance": deepcopy(dict(provenance))},
    )
    store.objects.append(item)
    return item


def request_snapshot(store, workflow_id: str) -> dict[str, Any]:
    inputs = request_inputs(store, workflow_id)
    retained = [item for item in inputs if item.status == "retained"]
    controls = [item for item in inputs if item.metadata["operation"] != "retain"]
    cancelled = bool(controls and controls[-1].metadata["operation"] == "cancel")
    return {
        "state": "cancelled" if cancelled else "retained" if retained else "empty",
        "fulfillment": "not_established",
        "inputs": [item.to_dict() for item in inputs],
        "retained_input_ids": [item.object_id for item in retained],
    }
