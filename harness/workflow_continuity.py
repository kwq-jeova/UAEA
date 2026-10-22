"""Factual bookkeeping on existing Phase-1 Workflow/Step records, not an executor."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

from .request_continuity import request_snapshot


def record_attempt(store, workflow_id: str, *, call_id: str, turn_id: str,
                   tool: str, arguments: Any, provenance: Mapping[str, Any],
                   user_request: str = "", input_id: str = ""):
    if not call_id:
        return None
    step = next((item for item in store.step_runs
                 if item.workflow_id == workflow_id
                 and item.action.get("harness", {}).get("call_id") == call_id
                 and item.action["harness"].get("turn_id") == turn_id), None)
    if step is None:
        request_ids = request_snapshot(store, workflow_id)["retained_input_ids"]
        step = store.record_step(
            {"arguments": deepcopy(arguments),
             "harness": {"call_id": call_id, "turn_id": turn_id, "sources": [],
                         "user_request": user_request, "input_id": input_id,
                         "request_context_input_ids": request_ids}},
            status="proposed", workflow_id=workflow_id, tool=tool,
        )
        step.started_at = ""
        step.completed_at = ""
    source = deepcopy(dict(provenance))
    sources = step.action["harness"]["sources"]
    if source not in sources:
        sources.append(source)
    return step


def record_outcome(step, observation: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    data = result.get("data") if isinstance(result.get("data"), Mapping) else {}
    succeeded = data.get("execution_succeeded")
    if not isinstance(succeeded, bool):
        succeeded = observation["status"] == "success"
    execution_status = str(data.get("execution_status") or result.get("status")
                           or observation["status"])
    step.status = ("completed" if succeeded else "rejected"
                   if execution_status in {"validation_failed", "rejected"} else "failed")
    step.capability = str(observation["capability"])
    step.execution_observation_id = str(observation["observation_id"])
    step.completed_at = datetime.now(timezone.utc).isoformat()
    contract = data.get("search_contract") or data.get("evidence_eligibility") or {}
    evidence_status = str(data.get("evidence_status") or contract.get("candidate_status") or "")
    candidates = data.get("citable_results") or []
    candidates = [deepcopy(item) for item in candidates if isinstance(item, Mapping)]
    step.action["outcome"] = {
        "execution_status": execution_status,
        "execution_succeeded": succeeded,
        "http_attempted": data.get("http_attempted"),
        "requested_provider": data.get("requested_provider"),
        "actual_provider": data.get("actual_provider"),
        "evidence_status": evidence_status if succeeded else "not_evaluated",
        "result_available": bool(data.get("result_available", succeeded)),
        "citable_count": len(candidates) if succeeded and evidence_status == "relevant" else 0,
        "citable_candidates": candidates if succeeded and evidence_status == "relevant" else [],
        "reason": data.get("reason"),
        "retryable": data.get("retryable"),
        "observation_id": step.execution_observation_id,
        "source_url": data.get("url"),
        "access_event_id": data.get("access_event_id"),
        "evidence_reference": deepcopy(data.get("evidence_reference")),
    }


def workflow_snapshot(store, workflow_id: str, receipts: list[dict]) -> dict[str, Any]:
    workflow = next((item for item in store.workflow_runs if item.workflow_id == workflow_id), None)
    steps = [item for item in store.step_runs if item.workflow_id == workflow_id]
    initial_request = workflow.source_user_intent if workflow else ""
    # Historical origin, not an inferred active request or a supersession decision.
    origin = next((item.action["harness"] for item in steps
                   if item.action["harness"].get("user_request")
                   and item.action["harness"]["user_request"] != initial_request), {})
    return {
        "workflow_id": workflow_id,
        "initial_request": initial_request,
        "status": workflow.status if workflow else "unknown",
        "completion_established": False,
        "attempts": [item.to_dict() for item in steps],
        "turn_receipts": [deepcopy(item) for item in receipts if item["workflow_id"] == workflow_id],
        "source_coverage": source_coverage(steps),
        "request_continuity": request_snapshot(store, workflow_id),
        "last_action_request": {key: deepcopy(value) for key, value in steps[-1].action["harness"].items()
                                if key in {"user_request", "input_id", "call_id", "turn_id"}} if steps else {},
        "action_request_origin": {key: deepcopy(value) for key, value in origin.items()
                                  if key in {"user_request", "input_id", "call_id", "turn_id"}},
        "unresolved": [
            {"call_id": item.action["harness"]["call_id"], "scope": "attempt", "blocks_workflow": False,
             "state": (
                "outcome_not_observed" if "outcome" not in item.action else
                "evidence_insufficient" if item.action["outcome"]["evidence_status"] in
                {"low_relevance", "uncertain"} else "result_unavailable"
                if not item.action["outcome"]["result_available"] else "attempt_not_successful")}
            for item in steps if "outcome" not in item.action or item.status != "completed"
            or not item.action["outcome"]["result_available"]
            or item.action["outcome"]["evidence_status"] in {"low_relevance", "uncertain"}
        ],
    }


def source_coverage(steps) -> dict[str, Any]:
    """Eligible discovery URLs joined to actual fetch outcomes, not a requirement set."""
    sources: dict[str, dict[str, Any]] = {}
    for step in steps:
        outcome = step.action.get("outcome", {})
        if step.capability != "web.search" or not outcome.get("execution_succeeded"):
            continue
        if outcome.get("evidence_status") != "relevant":
            continue
        for candidate in outcome.get("citable_candidates", []):
            url = candidate.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                continue
            source = sources.setdefault(url, {"url": url, "title": candidate.get("title", ""),
                                              "discovered_by": [], "fetch_attempts": []})
            source["discovered_by"].append({
                "call_id": step.action["harness"]["call_id"],
                "turn_id": step.action["harness"]["turn_id"],
                "observation_id": outcome["observation_id"],
                "access_event_id": outcome.get("access_event_id"),
            })
    other_fetches = []
    for step in steps:
        if step.tool != "web_fetch" and step.capability != "web.fetch":
            continue
        arguments = step.action.get("arguments", {})
        url = arguments.get("url") if isinstance(arguments, Mapping) else None
        outcome = step.action.get("outcome", {})
        attempt = {"call_id": step.action["harness"]["call_id"],
                   "turn_id": step.action["harness"]["turn_id"],
                   "state": step.status,
                   "outcome_observed": bool(outcome),
                   "execution_status": outcome.get("execution_status"),
                   "result_available": bool(outcome.get("execution_succeeded")
                                            and outcome.get("result_available")),
                   "observation_id": outcome.get("observation_id"),
                   "access_event_id": outcome.get("access_event_id"),
                   "source_url": outcome.get("source_url")}
        if url in sources:
            sources[url]["fetch_attempts"].append(attempt)
        else:
            other_fetches.append({"requested_url": url, **attempt})
    for source in sources.values():
        attempts = source["fetch_attempts"]
        # A failed retry does not erase an already retained page observation.
        source["fetch_state"] = ("fetched" if any(a["result_available"] for a in attempts) else
                                 "pending" if any(not a["outcome_observed"] and a["state"] == "proposed"
                                                  for a in attempts) else
                                 "failed" if attempts else "unattempted")
    counts = {state: sum(source["fetch_state"] == state for source in sources.values())
              for state in ("fetched", "failed", "pending", "unattempted")}
    return {"unit": "url", "discovered": len(sources), **counts,
            "sources": list(sources.values()), "other_fetches": other_fetches}


def turn_receipt(store, workflow_id: str, turn_id: str, terminal: str) -> dict[str, Any]:
    steps = [item for item in store.step_runs if item.workflow_id == workflow_id
             and item.action.get("harness", {}).get("turn_id") == turn_id]
    return {"workflow_id": workflow_id, "turn_id": turn_id, "terminal": terminal,
            "attempts": len(steps), "successful": sum(item.status == "completed" for item in steps),
            "outcomes_observed": sum("outcome" in item.action for item in steps)}


def execution_projection(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {"completion_established": False}
    coverage = snapshot.get("source_coverage", {})
    if coverage.get("discovered"):
        projection["source_coverage"] = {
            key: coverage[key] for key in ("unit", "discovered", "fetched", "failed", "pending", "unattempted")
        }
        projection["source_coverage"].update({
            "sources": [{"url": source["url"], "fetch_state": source["fetch_state"]}
                        for source in coverage["sources"]], "omitted_sources": 0,
        })
    receipts = snapshot["turn_receipts"]
    if receipts:
        projection["previous_turn"] = {key: value for key, value in receipts[-1].items()
                                       if key in {"turn_id", "terminal", "attempts"}}
    if snapshot["attempts"]:
        searches = [step for step in snapshot["attempts"] if step["tool"] == "web_search"]
        if searches:
            search = searches[-1]
            arguments = search["action"].get("arguments")
            query = arguments.get("query") if isinstance(arguments, Mapping) else None
            if isinstance(query, str):
                projection["last_search_action"] = {
                    "call_id": search["action"]["harness"]["call_id"], "query": query,
                    "task_alignment": "not_evaluated",
                }
        step = snapshot["attempts"][-1]
        identity = step["action"]["harness"]
        outcome = step["action"].get("outcome", {})
        projection["last_attempt"] = {
            "call_id": identity["call_id"], "turn_id": identity["turn_id"],
            "capability": step["capability"] or step["tool"], "state": step["status"],
            **{key: outcome[key] for key in ("execution_status", "execution_succeeded", "http_attempted",
                                           "result_available") if key in outcome},
        }
        if step["capability"] == "web.search":
            projection["last_attempt"].update({key: outcome[key] for key in
                                               ("actual_provider", "evidence_status", "citable_count")
                                               if key in outcome})
        candidates = outcome.get("citable_candidates") or []
        if candidates:
            projection["candidate"] = {key: candidates[0][key] for key in
                                       ("title", "url", "source_id", "web_source_id", "access_event_id")
                                       if key in candidates[0]}
    return projection
