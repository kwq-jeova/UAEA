from __future__ import annotations

from .runner import WorkloadCase


def uaea_phase2a_workloads() -> list[WorkloadCase]:
    return [
        WorkloadCase(
            case_id="planner_request",
            category="planner",
            messages=[
                {"role": "system", "content": "Return one structured action proposal."},
                {"role": "user", "content": "Read README sections 1-3 and evaluate each."},
            ],
            max_tokens=1024,
        ),
        WorkloadCase(
            case_id="semantic_observation",
            category="semantic_observation",
            messages=[
                {"role": "system", "content": "Produce a structured semantic observation."},
                {"role": "user", "content": "Evaluate the supplied execution observation."},
            ],
            max_tokens=2048,
        ),
        WorkloadCase(
            case_id="artifact_extraction",
            category="artifact",
            messages=[
                {"role": "system", "content": "Create a reusable workflow artifact summary."},
                {"role": "user", "content": "Summarize the completed section evaluations."},
            ],
            max_tokens=2048,
        ),
    ]
