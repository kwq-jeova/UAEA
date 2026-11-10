"""Observable source/claim links. Never a natural-language truth or authority engine."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA = "uaea.evidence_provenance.v0"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def retained_source_index(steps, workflow_id: str, *, max_entries: int = 32,
                          max_bytes: int = 6000) -> dict[str, Any]:
    """Bounded lookup references, not recovered content or a semantic ranking.

    Only Host acquisition receipts in this Workflow supply identities. Native
    echoes, summaries and assistant citations cannot populate this index. The
    existing web.fetch verifies the saved bytes again when a reference is read.
    """
    entries, conflicts = {}, set()
    rejected = 0
    for step in steps:
        if step.workflow_id != workflow_id or step.capability != "web.fetch":
            continue
        receipt = step.action.get("host_execution_receipt") or {}
        result = receipt.get("result") if isinstance(receipt, Mapping) else None
        data = result.get("data") if isinstance(result, Mapping) else None
        if not isinstance(data, Mapping) or data.get("execution_succeeded") is not True:
            continue
        excerpt = data.get("source_excerpt")
        sid, url, version = (data.get(k) for k in ("access_event_id", "url", "content_sha256"))
        if (not isinstance(excerpt, Mapping) or not isinstance(sid, str) or not sid
                or not isinstance(url, str) or not url.startswith(("https://", "http://"))
                or not isinstance(version, str) or not re.fullmatch(r"[0-9a-f]{64}", version)
                or excerpt.get("source_event_id") != sid
                or excerpt.get("content_sha256") != version
                or not isinstance(excerpt.get("text"), str)
                or digest(excerpt["text"]) != excerpt.get("text_sha256")):
            rejected += 1
            continue
        identity = {"source_event_id": sid, "url": url, "content_sha256": version}
        old = entries.get(sid)
        if old and any(old.get(k) != identity[k] for k in identity):
            conflicts.add(sid)
        harness = step.action.get("harness")
        identity["turn_id"] = harness.get("turn_id", "") if isinstance(harness, Mapping) else ""
        entries.pop(sid, None)
        entries[sid] = identity
    candidates = [e for sid, e in reversed(list(entries.items())) if sid not in conflicts]
    index = {
        "workflow_id": workflow_id, "entries": [], "total_sources": len(candidates),
        "omitted_sources": len(candidates), "invalid_receipts": rejected,
        "conflicting_identities": len(conflicts),
        "scope": "host_acquisition_references_not_current_content_or_semantic_support",
        "read_with": "web_fetch(url, source_event_id, start_char=0, max_chars<=3000)",
        "availability": "snapshot_revalidated_on_read; missing_or_changed_remains_unknown",
    }
    for entry in candidates:
        if len(index["entries"]) == max_entries:
            break
        index["entries"].append(entry)
        index["omitted_sources"] -= 1
        if len(json.dumps(index, ensure_ascii=False).encode()) > max_bytes:
            index["entries"].pop()
            index["omitted_sources"] += 1
    return index



def _verified_delivery(step) -> dict | None:
    """Verify a result echo against acquisition; hashes prove bytes, not meaning."""
    delivery = step.action.get("source_delivery")
    if not isinstance(delivery, dict) or delivery.get("basis") != "tool_result_echo":
        return None
    receipt = step.action.get("host_execution_receipt") or {}
    result = receipt.get("result") if isinstance(receipt, Mapping) else None
    acquired = result.get("data") if isinstance(result, Mapping) else None
    if not isinstance(acquired, Mapping):
        return None
    original, supplied = acquired.get("source_excerpt"), delivery.get("source_excerpt")
    if not isinstance(original, Mapping) or not isinstance(supplied, Mapping):
        return None
    text, source_text = supplied.get("text"), original.get("text")
    if (step.capability != "web.fetch" or acquired.get("execution_succeeded") is not True
            or not isinstance(text, str) or not text or not isinstance(source_text, str)
            or digest(source_text) != original.get("text_sha256")
            or digest(text) != supplied.get("text_sha256")
            or not source_text.startswith(text)
            or not isinstance(acquired.get("access_event_id"), str) or not acquired["access_event_id"]
            or not acquired.get("content_sha256")
            or supplied.get("content_sha256") != acquired["content_sha256"]
            or original.get("content_sha256") != acquired["content_sha256"]
            or supplied.get("source_event_id") != acquired.get("access_event_id")
            or original.get("source_event_id") != acquired.get("access_event_id")):
        return None
    keys = ("start_char", "extracted_text_chars", "extracted_text_sha256")
    if any(supplied.get(k) != original.get(k) for k in keys):
        return None
    start, end, total = (supplied.get(k) for k in ("start_char", "end_char", "extracted_text_chars"))
    if (any(type(v) is not int for v in (start, end, total)) or not 0 <= start < end <= total
            or end != start + len(text) or not supplied.get("extracted_text_sha256")):
        return None
    return supplied


def record_source_delivery(step, result: Mapping, *, provenance: Mapping) -> bool:
    """Attach first verifiable supplied fragment to the existing Step, never its receipt."""
    if step.action.get("source_delivery") is not None:
        return False  # Duplicate echoes do not add a new delivery or overwrite history.
    data = result.get("data")
    if not isinstance(data, Mapping):
        return False
    if (result.get("capability") != "web.fetch" or data.get("execution_succeeded") is not True
            or not isinstance(data.get("source_excerpt"), dict)):
        return False
    candidate = {
        "basis": "tool_result_echo", "source_excerpt": deepcopy(data["source_excerpt"]),
        "provenance": deepcopy(dict(provenance)), "model_understanding": "not_established",
    }
    step.action["source_delivery"] = candidate
    if _verified_delivery(step) is None:
        step.action.pop("source_delivery")
        return False
    return True


def source_reading_progress(steps, source_event_id: str, content_sha256: str) -> dict:
    """Exact historical supply coverage for one acquired snapshot version."""
    delivered = []
    for step in steps:
        excerpt = _verified_delivery(step)
        if (excerpt and excerpt["source_event_id"] == source_event_id
                and excerpt["content_sha256"] == content_sha256):
            delivered.append(excerpt)
    if not delivered:
        return {"state": "not_established", "saved_text_fully_supplied": None}
    versions = {(e["extracted_text_sha256"], e["extracted_text_chars"]) for e in delivered}
    if len(versions) != 1:
        return {"state": "version_conflict", "saved_text_fully_supplied": None}
    merged = []
    for start, end in sorted((e["start_char"], e["end_char"]) for e in delivered):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    total = delivered[0]["extracted_text_chars"]
    complete = merged == [[0, total]]
    cursor = merged[0][1] if merged and merged[0][0] == 0 else 0
    return {
        "state": "historical_tool_supply", "supplied_ranges": merged[:8],
        "omitted_range_count": max(0, len(merged)-8),
        "supplied_chars": sum(end-start for start, end in merged),
        "saved_text_fully_supplied": complete, "next_unsupplied_start_char": None if complete else cursor,
        "scope": "saved_extracted_text_not_full_page_or_semantic_support",
    }

def source_inventory(steps) -> list[dict[str, Any]]:
    """Accept host-recorded Step outcomes, never assistant text or model source lists."""
    sources = []
    for step in steps:
        outcome = step.action.get("outcome", {})
        if not outcome.get("execution_succeeded"):
            continue
        common = {"capability": step.capability, "observation_id": outcome.get("observation_id"),
                  "call_id": step.action.get("harness", {}).get("call_id"),
                  "turn_id": step.action.get("harness", {}).get("turn_id"),
                  "execution_grounded": True, "content_supported": "not_assessed"}
        if step.capability == "web.search":
            for index, hit in enumerate(outcome.get("citable_candidates", [])):
                sources.append({**common, "source_id": hit.get("source_id") or
                                f"{outcome.get('access_event_id') or common['observation_id']}:result:{index}",
                                "url": hit.get("url"), "scope": "search_discovery",
                                "page_fetch_observed": False, "excerpt_supplied": False})
            continue
        document = outcome.get("document_source")
        if (document and "host_execution_receipt" in step.action
                and digest(document["acquired_excerpt"]) == document["acquired_excerpt_sha256"]):
            sources.append({**common, **deepcopy(document),
                            "source_id": outcome["observation_id"],
                            "url": None, "scope": "document_section" if step.capability.endswith("read_section")
                                              else "document_response",
                            "page_fetch_observed": False, "excerpt_supplied": False,
                            "document_identity": "host_capability_receipt",
                            "content_sha256": document["content_hash"]})
            continue
        ref = outcome.get("evidence_reference") or {}
        source_id = outcome.get("access_event_id") or ref.get("source_id")
        if not outcome.get("result_available") or not source_id:
            continue
        delivered = _verified_delivery(step)
        excerpt = delivered or outcome.get("source_excerpt") or {}
        text = excerpt.get("text")
        # Shared acquisition is not delivery. A verified echo may prove a shorter
        # fragment, without upgrading the unseen remainder of the acquisition.
        intact = ((delivered is not None or outcome.get("excerpt_delivery") != "not_established")
                  and isinstance(text, str) and bool(text)
                  and excerpt.get("source_event_id") == source_id
                  and digest(text) == excerpt.get("text_sha256")
                  and bool(outcome.get("content_sha256"))
                  and excerpt.get("content_sha256") == outcome.get("content_sha256"))
        sources.append({**common, "source_id": source_id, "url": outcome.get("source_url"),
                        "scope": "page_response" if step.capability == "web.fetch" else "capability_result",
                        "page_fetch_observed": step.capability == "web.fetch",
                        "content_sha256": outcome.get("content_sha256"),
                        "excerpt_supplied": intact, "excerpt": text if intact else None,
                        "excerpt_sha256": digest(text) if intact else None,
                        "document_identity": "not_semantically_verified"})
    return sources


def ground_claim(sources: list[dict], *, text: str, source_ids=(), urls=(), paths=(),
                 execution_claim: Mapping | None = None, quote: str | None = None,
                 prior_model_output_ids=()) -> dict[str, Any]:
    """Explicit observable fields only; callers must label who asserted the claim.

    Matching a source, fetch, or exact quotation does not establish entailment,
    relevance, correctness, full-page reading, or request fulfillment.
    """
    for values in (source_ids, urls, paths):
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError("Source references must be nonempty strings")
    wanted_ids, wanted_urls, wanted_paths = set(source_ids), set(urls), set(paths)
    linked = [s for s in sources if s["source_id"] in wanted_ids or s.get("url") in wanted_urls
              or (s.get("path") and s["path"] in wanted_paths)
              or (s.get("resolved_path") and s["resolved_path"] in wanted_paths)]
    matched_ids = {s["source_id"] for s in linked}
    matched_urls = {s.get("url") for s in linked}
    execution = {"status": "not_asserted", "observation_ids": []}
    if execution_claim is not None:
        url, source_id, path = execution_claim.get("url"), execution_claim.get("source_id"), execution_claim.get("path")
        matches = [s for s in sources if (url or source_id or path)
                   and (not url or s.get("url") == url)
                   and (not source_id or s["source_id"] == source_id)
                    and (not path or path in {s.get("path"), s.get("resolved_path")})
                   and execution_claim.get("operation") == s["capability"]]
        execution = {"status": "supported" if matches else "not_established",
                     "scope": "capability_observation_only_not_reading_comprehension_or_entailment",
                     "observation_ids": sorted({s["observation_id"] for s in matches})}
    exact = [s["source_id"] for s in linked if quote and s.get("excerpt_supplied")
             and quote in s["excerpt"]]
    acquired_matches = [s["source_id"] for s in linked if quote
                        and isinstance(s.get("acquired_excerpt"), str)
                        and quote in s["acquired_excerpt"]]
    return {"schema": SCHEMA, "text_sha256": digest(text), "origin": "model_output",
            "source_evidence": False,
            "source_linked": {"status": "linked" if linked else "not_linked",
                              "source_ids": sorted(matched_ids),
                              "unresolved_source_ids": sorted(wanted_ids - matched_ids),
                              "unresolved_urls": sorted(wanted_urls - matched_urls)},
            "execution_grounded": execution,
            "linked_source_facts": [{k: s[k] for k in
                ("source_id", "scope", "page_fetch_observed", "excerpt_supplied")}
                for s in linked],
            "quote_match": {"status": ("exact_in_supplied_excerpt" if exact else
                                      "not_found_in_supplied_excerpt") if quote is not None else "not_requested",
                            "source_ids": exact},
            "acquired_quote_match": {"status": "exact_in_acquired_excerpt" if acquired_matches
                                             else "not_established",
                                     "source_ids": acquired_matches,
                                     "does_not_establish_model_delivery_or_entailment": True},
            "content_supported": "not_assessed_requires_semantic_judgment",
            "historical_model_output_refs": list(prior_model_output_ids),
            "history_confers_source_authority": False,
            "workflow_completion_established": False}


def explicit_urls(text: str) -> list[str]:
    """Citation syntax only; no natural-language assertion/entailment classifier."""
    return list(dict.fromkeys(re.findall(r'https?://[^\s<>"\]\)]+', text)))


def record_model_output(store, workflow_id: str, *, text: str, event_id: str,
                        turn_id: str, raw_reference: Mapping | None = None,
                        origin_kind: str = "model_output") -> dict:
    from runtime.runtime_objects import RuntimeObjectRecord
    steps = [s for s in store.step_runs if s.workflow_id == workflow_id]
    report = ground_claim(source_inventory(steps), text=text, urls=explicit_urls(text))
    identity = f"model-output:{workflow_id}:{turn_id}:{digest(text)}"
    existing = next((x for x in store.objects if x.object_id == identity), None)
    if existing is None:
        existing = RuntimeObjectRecord(
            object_id=identity, object_type="model_output_claim", owner=workflow_id,
            status="unverified", source_event_ids=[event_id] if event_id else [],
            metadata={"text": text, "text_sha256": digest(text), "turn_id": turn_id,
                       "grounding_at_output": report, "authority_level": "interpretation",
                       "origin_kind": origin_kind if origin_kind in {"model_output", "compaction_derived"} else "model_output",
                      "execution_assertions": "not_extracted_from_prose",
                      "raw_references": []})
        store.objects.append(existing)
    if raw_reference and dict(raw_reference) not in existing.metadata["raw_references"]:
        existing.metadata["raw_references"].append(dict(raw_reference))
    return deepcopy(existing.to_dict())


def provenance_snapshot(store, workflow_id: str) -> dict:
    steps = [s for s in store.step_runs if s.workflow_id == workflow_id]
    outputs = [x for x in store.objects if x.object_type == "model_output_claim" and x.owner == workflow_id]
    sources = source_inventory(steps)
    return {"schema": SCHEMA, "sources": sources,
            "model_outputs": [deepcopy(x.to_dict()) for x in outputs],
            "summary": {"search_discoveries": sum(s["scope"] == "search_discovery" for s in sources),
                        "fetch_observations": sum(s["page_fetch_observed"] for s in sources),
                        "document_observations": sum(s["scope"] in {"document_section", "document_response"} for s in sources),
                        "supplied_excerpts": sum(s["excerpt_supplied"] for s in sources),
                        "model_outputs": len(outputs),
                        "outputs_with_unresolved_urls": sum(bool(
                            x.metadata["grounding_at_output"]["source_linked"]["unresolved_urls"]) for x in outputs),
                        "model_output_is_source_evidence": False,
                        "content_support": "not_assessed",
                        "workflow_completion_established": False}}
