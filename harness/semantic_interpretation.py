"""Observable model interpretations; source validation is not semantic approval.

No model invocation, natural-language extraction, promotion, or execution occurs here.
The host must supply the request identity and observable model event identity.
"""
from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

from runtime.runtime_objects import RuntimeObjectRecord
from .request_continuity import request_inputs

SCHEMA = "uaea.semantic_interpretation.v1"
ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["intent", "constraint", "preference", "ambiguity"]},
        "key": {"type": "string", "maxLength": 120},
        "value": {"type": ["string", "boolean"], "maxLength": 1000},
        "proposed_scope": {"type": "string", "enum": ["turn", "task", "cross_task", "explicit_until_revoked"]},
        "start": {"type": "integer", "minimum": 0},
        "end": {"type": "integer", "minimum": 0},
        "quote": {"type": "string", "maxLength": 2000},
    },
    "required": ["kind", "key", "value", "proposed_scope", "start", "end", "quote"],
    "additionalProperties": False,
}
INTERPRETATION_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": ITEM_SCHEMA, "maxItems": 16}},
    "required": ["items"],
    "additionalProperties": False,
}
# Optional final-message transport. It cannot authorize earlier actions in that turn.
FINAL_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "interpretation": INTERPRETATION_SCHEMA,
    },
    "required": ["answer", "interpretation"],
    "additionalProperties": False,
}


def request_record(store, workflow_id: str, input_id: str):
    record = next((item for item in request_inputs(store, workflow_id)
                   if item.object_id == input_id), None)
    if record is None:
        raise ValueError("Unknown request identity")
    text = record.metadata["text"]
    if record.metadata.get("raw_text_sha256") != sha256(text.encode("utf-8")).hexdigest():
        raise ValueError("Original request integrity is not established")
    return record


def record_interpretation(store, workflow_id: str, input_id: str,
                          payload: Mapping[str, Any], *, model_event_id: str):
    request = request_record(store, workflow_id, input_id)
    if request.status != "retained" or not model_event_id:
        raise ValueError("Interpretation requires a retained request and model event")
    if not isinstance(payload, Mapping) or set(payload) != {"items"}:
        raise ValueError("Interpretation accepts items only; authority is host-owned")
    items = payload["items"]
    if not isinstance(items, list) or len(items) > 16:
        raise ValueError("Invalid interpretation items")
    text = request.metadata["text"]
    for item in items:
        if not isinstance(item, dict) or set(item) != set(ITEM_SCHEMA["required"]):
            raise ValueError("Invalid interpretation item fields")
        if item["kind"] not in ITEM_SCHEMA["properties"]["kind"]["enum"]:
            raise ValueError("Invalid interpretation kind")
        if item["proposed_scope"] not in ITEM_SCHEMA["properties"]["proposed_scope"]["enum"]:
            raise ValueError("Invalid proposed scope")
        for key, limit in (("key", 120), ("quote", 2000)):
            if not isinstance(item[key], str) or not item[key] or len(item[key]) > limit:
                raise ValueError("Invalid interpretation text")
        if not (isinstance(item["value"], str) and len(item["value"]) <= 1000
                or type(item["value"]) is bool):
            raise ValueError("Invalid interpretation value")
        start, end = item["start"], item["end"]
        if (type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(text) or text[start:end] != item["quote"]):
            raise ValueError("Quote is not an exact span of the original request")
    # Never pass model items through user_directive_basis/has_execution_authority.
    existing = next((x for x in store.objects if x.object_type == "semantic_interpretation"
                     and x.owner == workflow_id
                     and x.metadata["model_event_id"] == model_event_id), None)
    if existing:
        if existing.metadata["input_id"] != input_id or existing.metadata["items"] != items:
            raise ValueError("Model event identity reused with different interpretation")
        return existing
    record = RuntimeObjectRecord(
        object_type="semantic_interpretation", owner=workflow_id, status="candidate",
        source_object_ids=[input_id], source_event_ids=[model_event_id],
        metadata={"schema": SCHEMA, "input_id": input_id, "model_event_id": model_event_id,
                  "items": deepcopy(items), "source": "model",
                  "authority_level": "interpretation", "semantic_correctness": "not_established",
                  "quote_verified": True},
    )
    store.objects.append(record)
    return record


def record_final_output(store, workflow_id: str, input_id: str, text: str, *,
                        model_event_id: str):
    """Explicit structured transport only; arbitrary assistant prose is not parsed."""
    payload = json.loads(text)
    if (not isinstance(payload, dict) or set(payload) != {"answer", "interpretation"}
            or not isinstance(payload["answer"], str)):
        raise ValueError("Expected the negotiated structured final output")
    candidate = record_interpretation(store, workflow_id, input_id,
                                      payload["interpretation"], model_event_id=model_event_id)
    return payload["answer"], candidate
