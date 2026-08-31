from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping
from uuid import uuid4


ALLOWED_PROVENANCE_CLASSES = frozenset(
    {
        "explicit",
        "inferred",
        "observed",
        "measured",
        "derived",
        "external",
    }
)

ALLOWED_CANDIDATE_STATES = frozenset(
    {
        "open",
        "deferred",
        "closed",
    }
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _normalized_pairs(values: Mapping[str, object] | Iterable[tuple[object, object]] | None) -> tuple[tuple[str, str], ...]:
    if values is None:
        return ()
    items: list[tuple[str, str]] = []
    if isinstance(values, Mapping):
        iterable = values.items()
    else:
        iterable = values
    for key, value in iterable:
        key_text = _clean_text(key)
        value_text = _clean_text(value)
        if key_text and value_text:
            items.append((key_text, value_text))
    items.sort(key=lambda pair: pair[0])
    return tuple(items)


@dataclass(frozen=True)
class EvidenceReference:
    source_kind: str
    source_id: str
    source_event_id: str = ""
    location: str = ""
    summary: str = ""

    def validate_structure(self) -> list[str]:
        issues: list[str] = []
        if not _clean_text(self.source_kind):
            issues.append("evidence.source_kind missing")
        if not _clean_text(self.source_id):
            issues.append("evidence.source_id missing")
        return issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_kind": _clean_text(self.source_kind),
            "source_id": _clean_text(self.source_id),
            "source_event_id": _clean_text(self.source_event_id),
            "location": _clean_text(self.location),
            "summary": _clean_text(self.summary),
        }


@dataclass(frozen=True)
class ScopeHypothesis:
    summary: str = ""
    dimensions: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(
        cls,
        summary: str = "",
        dimensions: Mapping[str, object] | Iterable[tuple[object, object]] | None = None,
    ) -> "ScopeHypothesis":
        return cls(summary=_clean_text(summary), dimensions=_normalized_pairs(dimensions))

    def validate_structure(self) -> list[str]:
        issues: list[str] = []
        if not self.is_meaningful():
            issues.append("scope_hypothesis missing")
        return issues

    def is_meaningful(self) -> bool:
        return bool(_clean_text(self.summary) or self.dimensions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": _clean_text(self.summary),
            "dimensions": {key: value for key, value in self.dimensions},
        }


@dataclass(frozen=True)
class CandidateStructureReport:
    candidate_id: str
    valid: bool
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "valid": self.valid,
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class MemoryCandidate:
    claim: str
    source_provenance: str
    evidence_references: tuple[EvidenceReference, ...]
    scope_hypothesis: ScopeHypothesis
    extraction_confidence: float
    candidate_id: str = field(default_factory=lambda: str(uuid4()))
    candidate_state: str = "open"
    evidence_summary: str = ""
    validation_requirements: tuple[str, ...] = field(default_factory=tuple)
    proposed_validity: str = ""
    representation_facet_hint: str = ""
    relation_hint: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim", _clean_text(self.claim))
        object.__setattr__(self, "source_provenance", _clean_text(self.source_provenance).lower())
        object.__setattr__(self, "candidate_state", _clean_text(self.candidate_state).lower())
        object.__setattr__(self, "candidate_id", _clean_text(self.candidate_id) or str(uuid4()))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references or ()))
        object.__setattr__(self, "validation_requirements", tuple(_clean_text(item) for item in self.validation_requirements if _clean_text(item)))
        object.__setattr__(self, "evidence_summary", _clean_text(self.evidence_summary))
        object.__setattr__(self, "proposed_validity", _clean_text(self.proposed_validity))
        object.__setattr__(self, "representation_facet_hint", _clean_text(self.representation_facet_hint))
        object.__setattr__(self, "relation_hint", _clean_text(self.relation_hint))
        object.__setattr__(self, "created_at", _clean_text(self.created_at) or utc_now())
        object.__setattr__(self, "updated_at", _clean_text(self.updated_at) or utc_now())
        try:
            object.__setattr__(self, "extraction_confidence", float(self.extraction_confidence))
        except (TypeError, ValueError):
            object.__setattr__(self, "extraction_confidence", float("nan"))

    def validate_structure(self) -> CandidateStructureReport:
        issues: list[str] = []
        if not _clean_text(self.candidate_id):
            issues.append("candidate_id missing")
        if not _clean_text(self.claim):
            issues.append("claim missing")
        if self.source_provenance not in ALLOWED_PROVENANCE_CLASSES:
            issues.append("source_provenance invalid or missing")
        if not self.evidence_references:
            issues.append("evidence_references missing")
        else:
            for index, reference in enumerate(self.evidence_references):
                for issue in reference.validate_structure():
                    issues.append(f"evidence_references[{index}].{issue}")
        issues.extend(self.scope_hypothesis.validate_structure())
        if not _is_valid_confidence(self.extraction_confidence):
            issues.append("extraction_confidence invalid")
        if self.candidate_state not in ALLOWED_CANDIDATE_STATES:
            issues.append("candidate_state invalid")
        return CandidateStructureReport(
            candidate_id=self.candidate_id,
            valid=not issues,
            issues=tuple(issues),
        )

    def is_structurally_valid(self) -> bool:
        return self.validate_structure().valid

    def with_state(self, candidate_state: str) -> "MemoryCandidate":
        return replace(self, candidate_state=_clean_text(candidate_state).lower(), updated_at=utc_now())

    def defer(self) -> "MemoryCandidate":
        return self.with_state("deferred")

    def close(self) -> "MemoryCandidate":
        return self.with_state("closed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "claim": self.claim,
            "source_provenance": self.source_provenance,
            "evidence_references": [reference.to_dict() for reference in self.evidence_references],
            "scope_hypothesis": self.scope_hypothesis.to_dict(),
            "extraction_confidence": self.extraction_confidence,
            "candidate_state": self.candidate_state,
            "evidence_summary": self.evidence_summary,
            "validation_requirements": list(self.validation_requirements),
            "proposed_validity": self.proposed_validity,
            "representation_facet_hint": self.representation_facet_hint,
            "relation_hint": self.relation_hint,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def policy_payload(self) -> dict[str, Any]:
        return self.to_dict()


def _is_valid_confidence(value: object) -> bool:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return False
    if confidence != confidence:
        return False
    return 0.0 <= confidence <= 1.0
