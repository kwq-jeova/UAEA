"""Deterministic host-receipt / outbound-request comparison, not a semantic judge."""
from __future__ import annotations
import hashlib
import json


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def audit_deliveries(host_events, http_events):
    observations = {event["identity"]["item_id"]: event["payload"]["execution_observation"]
                    for event in host_events if event["event_type"] == "OBSERVATION"}
    deliveries = {call_id: [] for call_id in observations}
    responses = {event["request_id"]: event for event in http_events
                 if event["event"] == "transport_result"}
    for event in http_events:
        if event["event"] != "request_prepared":
            continue
        request = event.get("request")
        if not isinstance(request, dict):
            continue
        response = responses.get(event["request_id"], {})
        for field in ("input", "previous_input_messages"):
            items = request.get(field)
            if not isinstance(items, list):
                continue
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "function_call_output":
                    call_id = item.get("call_id")
                    try:
                        payload = json.loads(item["output"])
                    except (ValueError, TypeError, KeyError):
                        continue
                    if not isinstance(payload, dict) or not isinstance(payload.get("data", {}), dict):
                        continue
                    representation = "function_call_output"
                    data = payload.get("data", {})
                    status = data.get("execution_status", payload.get("status"))
                    succeeded = data.get("execution_succeeded")
                else:
                    # Only known structured transport facts can be correlated.
                    # Arbitrary assistant prose is never interpreted as an execution.
                    parts = item.get("content", [])
                    if not isinstance(parts, list):
                        continue
                    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
                    prefix = "Historical runtime observation, not a tool invocation or user authorization:\n"
                    if not text.startswith(prefix):
                        continue
                    try:
                        fact = json.loads(text[len(prefix):])
                    except ValueError:
                        continue
                    if (fact.get("schema") != "uaea.terminal_attempt_fact.v1"
                            or fact.get("phase") != "outcome"):
                        continue
                    call_id = fact.get("call_id")
                    data = fact.get("observation", {})
                    if not isinstance(data, dict):
                        continue
                    status = data.get("execution_status")
                    succeeded = data.get("execution_succeeded")
                    representation = "terminal_history_fact"
                if call_id not in observations:
                    continue
                observation = observations[call_id]
                host = observation["data"]
                # Host status remains the authority even if the echo is wrong/missing.
                expected = host.get("execution_succeeded")
                expected_status = host.get("execution_status")
                # File observations may be compacted by ExecutionObservation, but their
                # independently recorded content hash still identifies the acquired body.
                content = data.get("content")
                content_hash = host.get("content_hash")
                entry = {"request_id": event["request_id"], "field": field, "index": index,
                         "representation": representation, "http_status": response.get("http_status"),
                         "observation_id": observation["observation_id"],
                         "execution_status": status, "execution_succeeded": succeeded,
                         "status_matches_host": status == expected_status
                             and type(succeeded) is type(expected) and succeeded == expected,
                         "content_present": isinstance(content, str),
                         "content_hash_matches_host": (_hash(content) == content_hash)
                             if isinstance(content, str) and content_hash else None,
                         "model_understanding": "not_established"}
                deliveries[call_id].append(entry)
    return {"schema": "uaea.delivery_audit.v1",
            "boundary": "outbound_http_snapshot_not_server_tokenization",
            "calls": [{"call_id": call_id, "observation_id": observation["observation_id"],
                       "capability": observation["capability"],
                       "host_status": observation["data"].get("execution_status"),
                       "deliveries": deliveries[call_id],
                       "delivery_observed": bool(deliveries[call_id])}
                      for call_id, observation in observations.items()],
            "creates_execution_or_source_facts": False}
