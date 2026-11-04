"""Observable source/claim links. Never a natural-language truth or authority engine."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Any, Mapping

SCHEMA = "uaea.evidence_provenance.v0"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        excerpt = outcome.get("source_excerpt") or {}
        text = excerpt.get("text")
        # A truncated/rewritten projection cannot prove that the original excerpt was supplied.
        intact = (outcome.get("excerpt_delivery") != "not_established"
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
