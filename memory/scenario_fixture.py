from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .candidate import EvidenceReference, MemoryCandidate, ScopeHypothesis


@dataclass(frozen=True)
class FixtureEvaluationReport:
    fixture_id: str
    valid: bool
    issues: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metrics: Mapping[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "valid": self.valid,
            "issues": list(self.issues),
            "warnings": list(self.warnings),
            "metrics": dict(self.metrics),
        }


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_fixture(fixture: Mapping[str, Any]) -> FixtureEvaluationReport:
    fixture_id = str(fixture.get("fixture_id") or "")
    issues: list[str] = []
    warnings: list[str] = []

    turns = _list_of_dicts(fixture.get("turns"))
    candidates_data = _list_of_dicts(fixture.get("expected_candidates"))
    outcome = fixture.get("expected_outcome") if isinstance(fixture.get("expected_outcome"), Mapping) else {}
    non_memory_turn_ids = {str(value) for value in fixture.get("expected_non_memory_turn_ids", [])}
    retrieval_probes = _list_of_dicts(fixture.get("retrieval_probes"))

    turn_ids = [str(turn.get("turn_id") or "") for turn in turns]
    turn_id_set = {turn_id for turn_id in turn_ids if turn_id}
    if len(turn_ids) != len(turn_id_set):
        issues.append("turn_ids must be unique")
    if not turns:
        issues.append("turns missing")
    if not candidates_data:
        issues.append("expected_candidates missing")

    candidates: dict[str, MemoryCandidate] = {}
    for candidate_data in candidates_data:
        candidate_id = str(candidate_data.get("candidate_id") or "")
        if candidate_id in candidates:
            issues.append(f"candidate {candidate_id} duplicated")
            continue
        try:
            candidate = candidate_from_mapping(candidate_data)
        except (TypeError, ValueError, KeyError) as exc:
            issues.append(f"candidate {candidate_id or '<missing>'} cannot hydrate: {exc}")
            continue
        report = candidate.validate_structure()
        if not report.valid:
            issues.extend(f"candidate {candidate.candidate_id}: {issue}" for issue in report.issues)
        candidates[candidate.candidate_id] = candidate
        for reference in candidate.evidence_references:
            if reference.source_kind == "conversation_turn" and reference.source_id not in turn_id_set:
                issues.append(f"candidate {candidate.candidate_id} references missing turn {reference.source_id}")
            if reference.source_id in non_memory_turn_ids:
                issues.append(f"candidate {candidate.candidate_id} references non-memory turn {reference.source_id}")

    outcome_ids = _outcome_candidate_ids(outcome)
    missing_outcome_ids = sorted(outcome_ids.difference(candidates))
    if missing_outcome_ids:
        issues.append("expected_outcome references missing candidate ids: " + ", ".join(missing_outcome_ids))

    active_ids = _string_set(outcome.get("active_memory_candidate_ids", []))
    rejected_ids = _string_set(outcome.get("rejected_candidate_ids", []))
    if overlap := active_ids.intersection(rejected_ids):
        issues.append("candidate cannot be active and rejected: " + ", ".join(sorted(overlap)))

    upper_bound = _safe_int(outcome.get("memory_count_upper_bound"))
    if upper_bound and len(active_ids) > upper_bound:
        issues.append("active candidate count exceeds memory_count_upper_bound")
    if upper_bound and turns and upper_bound >= len(turns):
        issues.append("memory_count_upper_bound must be smaller than turn count")

    for probe in retrieval_probes:
        _evaluate_retrieval_probe(probe, candidates, issues, warnings)

    metrics = {
        "turn_count": len(turns),
        "candidate_count": len(candidates),
        "active_count": len(active_ids),
        "rejected_count": len(rejected_ids),
        "non_memory_turn_count": len(non_memory_turn_ids),
        "retrieval_probe_count": len(retrieval_probes),
    }
    return FixtureEvaluationReport(
        fixture_id=fixture_id,
        valid=not issues,
        issues=tuple(issues),
        warnings=tuple(warnings),
        metrics=metrics,
    )


def candidate_from_mapping(data: Mapping[str, Any]) -> MemoryCandidate:
    scope = data.get("scope_hypothesis")
    if not isinstance(scope, Mapping):
        raise ValueError("scope_hypothesis must be a mapping")
    references = []
    for reference in _list_of_dicts(data.get("evidence_references")):
        references.append(
            EvidenceReference(
                source_kind=str(reference.get("source_kind") or ""),
                source_id=str(reference.get("source_id") or ""),
                source_event_id=str(reference.get("source_event_id") or ""),
                location=str(reference.get("location") or ""),
                summary=str(reference.get("summary") or ""),
            )
        )
    return MemoryCandidate(
        candidate_id=str(data.get("candidate_id") or ""),
        claim=str(data.get("claim") or ""),
        source_provenance=str(data.get("source_provenance") or ""),
        evidence_references=tuple(references),
        scope_hypothesis=ScopeHypothesis.from_mapping(
            summary=str(scope.get("summary") or ""),
            dimensions=scope.get("dimensions") if isinstance(scope.get("dimensions"), Mapping) else {},
        ),
        extraction_confidence=float(data.get("extraction_confidence")),
        evidence_summary=str(data.get("evidence_summary") or ""),
        validation_requirements=tuple(str(value) for value in data.get("validation_requirements", [])),
        proposed_validity=str(data.get("proposed_validity") or ""),
        representation_facet_hint=str(data.get("representation_facet_hint") or ""),
        relation_hint=str(data.get("relation_hint") or ""),
    )


def _evaluate_retrieval_probe(
    probe: Mapping[str, Any],
    candidates: Mapping[str, MemoryCandidate],
    issues: list[str],
    warnings: list[str],
) -> None:
    query_id = str(probe.get("query_id") or "<missing>")
    expected_ids = _string_set(probe.get("expected_candidate_ids", []))
    if not expected_ids:
        issues.append(f"retrieval_probe {query_id} has no expected_candidate_ids")
        return
    missing = expected_ids.difference(candidates)
    if missing:
        issues.append(f"retrieval_probe {query_id} references missing candidate ids: {', '.join(sorted(missing))}")
        return
    required_scope_dimensions = [str(value) for value in probe.get("required_scope_dimensions", []) if str(value).strip()]
    for candidate_id in expected_ids:
        dimensions = dict(candidates[candidate_id].scope_hypothesis.dimensions)
        missing_dimensions = [dimension for dimension in required_scope_dimensions if dimension not in dimensions]
        if missing_dimensions:
            issues.append(
                f"retrieval_probe {query_id} candidate {candidate_id} missing required scope dimensions: "
                + ", ".join(missing_dimensions)
            )
        if not candidates[candidate_id].evidence_references:
            issues.append(f"retrieval_probe {query_id} candidate {candidate_id} has no evidence references")
    if not probe.get("required_uncertainty"):
        warnings.append(f"retrieval_probe {query_id} does not declare required uncertainty")


def _outcome_candidate_ids(outcome: Mapping[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in (
        "active_memory_candidate_ids",
        "dormant_or_low_priority_candidate_ids",
        "deferred_candidate_ids",
        "rejected_candidate_ids",
    ):
        ids.update(_string_set(outcome.get(key, [])))
    for edge in _list_of_dicts(outcome.get("supersession_edges")):
        candidate_id = str(edge.get("to_candidate_id") or "")
        if candidate_id:
            ids.add(candidate_id)
    return ids


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value if str(item).strip()}


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
