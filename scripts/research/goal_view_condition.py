"""Strict M3 Goal-view condition at the final Responses body, independent of prose.

prepare_goal_view is for the research bridge immediately after Host normalization.
Give it the independent Host view for that request. For a normal turn current_index
must be the slot attested by the Host renderer, adjusted for intervening inserts.
An invalid proof is ineligible for strict comparison. Never replay a failed arm.
"""
from collections import Counter
from hashlib import sha256
import json


TAG = "external_uaea.goal_hypotheses"
NATIVE_NAME = "uaeagoal_hypotheses"


def _wire_digest(request):
    # Same serializer as ProviderHistoryBridge when forwarding a transformed body.
    return sha256(json.dumps(request, ensure_ascii=False).encode("utf-8")).hexdigest()


def _inspect(request, expected_view):
    if isinstance(expected_view, str):
        expected_view = json.loads(expected_view)
    matches, unbound_xml, unbound_native, receipts = [], [], [], []
    issues = []
    for field in ("input", "previous_input_messages"):
        if field not in request and field == "previous_input_messages":
            continue
        items = request.get(field)
        if not isinstance(items, list):
            issues.append(f"{field}_not_explicit_items")
            continue
        calls = {item.get("call_id"): (i, item.get("name")) for i, item in enumerate(items)
                 if isinstance(item, dict) and item.get("type") == "function_call"
                 and isinstance(item.get("call_id"), str) and item["call_id"]}
        counts = Counter(item.get("call_id") for item in items
                         if isinstance(item, dict) and item.get("type") == "function_call"
                         and isinstance(item.get("call_id"), str))
        for pos, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            kind = item.get("type", "message")
            ref = {"field": field, "index": pos, "item_id": item.get("id")}
            if kind == "function_call_output":
                cid = item.get("call_id")
                paired = isinstance(cid, str) and counts[cid] == 1 and (
                    calls[cid][0] < pos and item.get("name") in (None, calls[cid][1]))
                if paired and calls[cid][1] == "goal_hypothesis":
                    receipts.append({**ref, "call_id": cid})
                elif item.get("name") == NATIVE_NAME and not paired:
                    # A suspicious carrier only. Its owner/turn cannot be inferred
                    # from a tool-like name. The normalizer handles proven owners.
                    unbound_native.append(ref)
                continue
            if kind != "message" or item.get("role") not in ("user", "developer"):
                continue
            content = item.get("content")
            # A string/partial envelope is not Host render evidence. Preserve it,
            # but don't certify a clean comparison if it opens the reserved tag.
            if isinstance(content, str):
                if content.lstrip().startswith(f"<{TAG}>"):
                    unbound_xml.append(ref)
                continue
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict) or not isinstance(part.get("text"), str):
                    continue
                text = part["text"].strip()
                start, end = f"<{TAG}>", f"</{TAG}>"
                if not text.startswith(start):
                    continue
                if not text.endswith(end):
                    unbound_xml.append(ref)
                    continue
                try:
                    view = json.loads(text[len(start):-len(end)])
                except ValueError:
                    view = None
                # Only the exact post-normalization envelope is eligible for OFF.
                # Every other candidate-shaped item survives and disqualifies the pair.
                if (field == "input" and item.get("role") == "user"
                        and set(item) == {"role", "content"} and len(content) == 1
                        and set(part) == {"type", "text"} and part["type"] == "input_text"
                        and isinstance(view, dict) and view == expected_view):
                    matches.append(pos)
                else:
                    unbound_xml.append(ref)
    if request.get("previous_response_id"):
        issues.append("server_history_not_auditable_from_this_body")
    if unbound_xml:
        issues.append("unbound_xml_candidate_carrier")
    if unbound_native:
        issues.append("unbound_native_candidate_carrier")
    return {"current_xml_indices": matches, "unbound_xml": unbound_xml,
            "unbound_native": unbound_native, "historical_goal_receipts": receipts,
            "reasons": issues}


def _score(request, arm, expected_view, compact):
    if arm not in ("on", "off"):
        raise ValueError("arm must be on or off")
    proof = _inspect(request, expected_view)
    required = 1 if arm == "on" and not compact else 0
    if len(proof["current_xml_indices"]) != required:
        proof["reasons"].append("unexpected_current_view_count")
    proof.update(arm=arm, compact=compact, expected_current_views=required,
                 body_sha256=_wire_digest(request), valid=not proof["reasons"])
    return proof


def prepare_goal_view(request, arm, *, expected_view, compact=False, current_index=None):
    """Apply the opt-in ablation to the normalized Host copy only; report any residue."""
    before = _inspect(request, expected_view)
    eligible = before["current_xml_indices"]
    outgoing = request
    removed = False
    correct_slot = ((current_index is None and compact) or
                    (type(current_index) is int and eligible == [current_index]))
    if arm == "off" and not compact and correct_slot and len(eligible) == 1:
        pos = eligible[0]
        outgoing = {**request, "input": request["input"][:pos] + request["input"][pos + 1:]}
        removed = True
    proof = _score(outgoing, arm, expected_view, compact)
    if not compact and len(eligible) != 1:
        proof["reasons"].append("baseline_current_view_missing_or_duplicated")
    if not correct_slot:
        proof["reasons"].append("renderer_slot_mismatch")
    proof.update(pre_toggle_current_indices=eligible, current_renderer_item_removed=removed,
                 goal_view_removed=removed and not proof["reasons"],
                 valid=not proof["reasons"], stage="prepared")
    return outgoing, proof


def verify_goal_view_transport(request, audit_rows, request_id, arm, *, expected_view, compact=False):
    """Bind visibility to this exact forwarded body and completed HTTP exchange."""
    proof = _score(request, arm, expected_view, compact)
    records = [r for r in audit_rows if r.get("request_id") == request_id] if request_id else []
    prepared = [r for r in records if r.get("event") == "request_prepared"]
    started = [r for r in records if r.get("event") == "transport_started"]
    results = [r for r in records if r.get("event") == "transport_result"]
    if len(prepared) != 1 or prepared[0].get("forwarded_bytes_sha256") != proof["body_sha256"]:
        proof["reasons"].append("forwarded_body_unverified")
    if not (len(started) == len(results) == 1 and started[0].get("http_status") == 200
            and results[0].get("http_status") == 200 and results[0].get("response_complete") is True
            and not results[0].get("transport_error")):
        proof["reasons"].append("transport_incomplete_or_unverified")
    proof.update(request_id=request_id, valid=not proof["reasons"], stage="transport",
                 strict_off_verified=(arm == "off" and not compact and not proof["reasons"]))
    return proof


def verify_captured_turn(folder, arm):
    """Score every actual HTTP exchange in one capture, including tool continuations."""
    from pathlib import Path
    folder = Path(folder)
    def read_rows(name):
        return [json.loads(line) for line in (folder / name).read_text().splitlines() if line]
    audit = read_rows("model-http-audit.jsonl")
    publications = read_rows("provider-history-decisions.jsonl")
    prepared = [r for r in audit if r["event"] == "request_prepared"]
    results = []
    if not prepared:
        raise ValueError("No prepared HTTP body")
    for prefix in ("projection-proof-", "actual-projected-request-"):
        files = {p.name for p in folder.glob(prefix + "*.json")}
        if files != {f"{prefix}{n}.json" for n in range(1, len(prepared) + 1)}:
            raise ValueError("Capture and HTTP request counts differ: " + prefix)
    for n, record in enumerate(prepared, 1):
        body = json.loads((folder / f"actual-projected-request-{n}.json").read_text())
        before = json.loads((folder / f"projection-proof-{n}.json").read_text())
        owners = [r for r in publications if r.get("provider_request_sequence") == record["sequence"]
                  and r.get("source") == "published_host_snapshot"]
        if len(owners) != 1 or owners[0]["kind"] not in {
            "host_context_restored", "host_context_deferred_for_compaction"
        }:
            raise ValueError("Missing or ambiguous Host publication")
        compact = owners[0]["kind"] == "host_context_deferred_for_compaction"
        if not compact:
            # GoalIntegration serializes this block with json.dumps(ensure_ascii=False).
            # Bind the retained expected view to the Host even when OFF removes its bytes.
            host_digest = owners[0].get("goal_value_sha256")
            if not host_digest or _wire_digest(before["expected_view"]) != host_digest:
                raise ValueError("Expected view differs from the Host publication")
        proof = verify_goal_view_transport(body, audit, record["request_id"], arm,
                                           expected_view=before["expected_view"], compact=compact)
        if before.get("valid") is not True or before.get("arm") != arm or before.get("compact") != compact:
            proof["reasons"].append("preparation_invalid_or_mismatched")
            proof.update(valid=False, strict_off_verified=False)
        results.append(proof)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Verify captured Goal-view exposure from the final HTTP bodies.")
    parser.add_argument("folder")
    parser.add_argument("arm", choices=("on", "off"))
    args = parser.parse_args()
    try:
        checks = verify_captured_turn(args.folder, args.arm)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Unscorable capture: {exc}\n")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    raise SystemExit(0 if all(row["valid"] for row in checks) else 1)
