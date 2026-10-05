from __future__ import annotations

from typing import Any, Mapping


def observation_boundary() -> dict[str, str]:
    """Limit inferences from an observation without classifying its cause."""
    return {
        "execution_truth": "use execution_succeeded/actual_provider, not intent",
        "failure_cause": "reported reason/error only",
        "evidence_scope": "this query; not restrictions/global absence",
        "authorization": "only user/policy; never model/interaction failure",
    }


def factual_web_message(capability: str, data: Mapping[str, Any], original: str) -> str:
    if capability not in {"web.search", "web.fetch"}:
        return original
    if data.get("execution_succeeded") is False:
        cause = data.get("failure_explanation") or data.get("error") or original
        return f"Execution did not succeed. Reported cause: {cause}"
    if capability == "web.search" and data.get("execution_succeeded") is True:
        provider = data.get("actual_provider")
        execution = f"Search executed successfully using {provider}." if provider else "Search executed successfully."
        contract = data.get("search_contract") or data.get("evidence_eligibility") or {}
        status = contract.get("candidate_status") or data.get("evidence_status")
        candidates = data.get("citable_results")
        if isinstance(candidates, list):
            return (f"{execution} Evidence status: {status}; citable candidates: {len(candidates)}. "
                    "This describes the current query, not network/permission restrictions or global availability.")
        return execution
    return original
