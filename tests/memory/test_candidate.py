from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from memory.candidate import (
    ALLOWED_CANDIDATE_STATES,
    ALLOWED_PROVENANCE_CLASSES,
    CandidateStructureReport,
    EvidenceReference,
    MemoryCandidate,
    ScopeHypothesis,
)

from runtime.events import Event
from runtime.runtime_objects import RuntimeObjectRecord, WorkflowArtifactRecord
from runtime.semantic_observation import SemanticObservation


class MemoryCandidateTests(unittest.TestCase):
    def build_scope(self, **dimensions: str) -> ScopeHypothesis:
        return ScopeHypothesis.from_mapping(
            summary="UAEA Phase-2B architecture / current validation context",
            dimensions=dimensions,
        )

    def build_candidate(
        self,
        *,
        claim: str,
        source_provenance: str,
        evidence_refs: list[EvidenceReference],
        scope: ScopeHypothesis,
        extraction_confidence: float,
        candidate_state: str = "open",
        validation_requirements: list[str] | None = None,
        proposed_validity: str = "",
        representation_facet_hint: str = "",
        relation_hint: str = "",
        evidence_summary: str = "",
    ) -> MemoryCandidate:
        return MemoryCandidate(
            claim=claim,
            source_provenance=source_provenance,
            evidence_references=tuple(evidence_refs),
            scope_hypothesis=scope,
            extraction_confidence=extraction_confidence,
            candidate_state=candidate_state,
            validation_requirements=tuple(validation_requirements or ()),
            proposed_validity=proposed_validity,
            representation_facet_hint=representation_facet_hint,
            relation_hint=relation_hint,
            evidence_summary=evidence_summary,
        )

    def test_candidate_validation_and_audit_payload_for_explicit_constraint(self):
        event = Event(
            session_id="session-1",
            event_type="conversation_event",
            objective="freeze phase1",
            result="success",
            metadata={"role": "user", "content_excerpt": "Phase-1 Runtime must remain frozen."},
        )
        candidate = self.build_candidate(
            claim="Phase-1 Runtime must remain frozen.",
            source_provenance="explicit",
            evidence_refs=[
                EvidenceReference(
                    source_kind="conversation_event",
                    source_id=event.event_id,
                    source_event_id=event.event_id,
                    summary="User explicitly requested Phase-1 freeze.",
                )
            ],
            scope=self.build_scope(project="UAEA", phase="Phase-2B", boundary="Phase-1 Runtime"),
            extraction_confidence=1.0,
            proposed_validity="Phase-1 / current architecture phase",
            representation_facet_hint="constraint",
            evidence_summary="Explicit user instruction recorded in conversation event.",
        )

        report = candidate.validate_structure()
        self.assertIsInstance(report, CandidateStructureReport)
        self.assertTrue(report.valid, report.issues)
        self.assertEqual(candidate.source_provenance, "explicit")
        self.assertEqual(candidate.candidate_state, "open")
        self.assertEqual(candidate.to_dict()["claim"], "Phase-1 Runtime must remain frozen.")
        self.assertEqual(candidate.to_dict()["scope_hypothesis"]["dimensions"]["boundary"], "Phase-1 Runtime")
        self.assertIn("explicit", ALLOWED_PROVENANCE_CLASSES)

    def test_inferred_preference_retains_inference_provenance(self):
        first = Event(
            session_id="session-2",
            event_type="conversation_event",
            objective="architecture review",
            result="success",
            metadata={"role": "user", "content_excerpt": "Please keep the architecture boundary clear."},
        )
        second = Event(
            session_id="session-2",
            event_type="conversation_event",
            objective="architecture review",
            result="success",
            metadata={"role": "user", "content_excerpt": "Do not mix implementation and boundary design."},
        )
        candidate = self.build_candidate(
            claim="User prefers architecture-first discussion before implementation.",
            source_provenance="inferred",
            evidence_refs=[
                EvidenceReference(source_kind="conversation_event", source_id=first.event_id, summary="Architecture boundary emphasis."),
                EvidenceReference(source_kind="conversation_event", source_id=second.event_id, summary="Implementation separation emphasis."),
            ],
            scope=self.build_scope(project="UAEA", phase="Phase-2B", subject="review style"),
            extraction_confidence=0.72,
            validation_requirements=["requires recurrence confirmation"],
            representation_facet_hint="preference",
        )

        report = candidate.validate_structure()
        self.assertTrue(report.valid, report.issues)
        self.assertEqual(candidate.source_provenance, "inferred")
        self.assertEqual(len(candidate.evidence_references), 2)
        self.assertEqual(candidate.validation_requirements, ("requires recurrence confirmation",))

    def test_benchmark_backed_fact_keeps_scope_and_condition(self):
        artifact = WorkflowArtifactRecord(
            workflow_id="wf-benchmark",
            content="Qwen2.5-14B-AWQ Phase-1 L0-L6 validation passed on current vLLM stack.",
            artifact_kind="benchmark_result",
            status="COMPLETE",
            finish_reason="stop",
            scope="Qwen2.5-14B-Instruct-AWQ / vLLM 0.26.0 / RTX 5090D 24GB",
            summary="Bounded Phase-1 validation passed.",
            metadata={"backend": "vllm", "model": "qwen25-14b-awq"},
        )
        candidate = self.build_candidate(
            claim="Qwen2.5-14B-Instruct-AWQ passed Phase-1 L0-L6 under the current vLLM stack.",
            source_provenance="measured",
            evidence_refs=[
                EvidenceReference(
                    source_kind="workflow_artifact",
                    source_id=artifact.artifact_id,
                    summary="Benchmark artifact records bounded validation pass.",
                )
            ],
            scope=self.build_scope(
                project="UAEA",
                phase="Phase-2A",
                backend="vLLM",
                model="Qwen2.5-14B-Instruct-AWQ",
                hardware="RTX 5090D 24GB",
                dependency="vLLM 0.26.0",
            ),
            extraction_confidence=0.94,
            proposed_validity="Only for current model/backend/hardware stack",
            representation_facet_hint="semantic",
        )

        report = candidate.validate_structure()
        self.assertTrue(report.valid, report.issues)
        self.assertEqual(candidate.source_provenance, "measured")
        self.assertEqual(candidate.policy_payload()["scope_hypothesis"]["dimensions"]["backend"], "vLLM")
        self.assertEqual(candidate.policy_payload()["scope_hypothesis"]["dimensions"]["model"], "Qwen2.5-14B-Instruct-AWQ")

    def test_failure_lesson_remains_distinct_from_raw_failure(self):
        raw_failure = RuntimeObjectRecord(
            object_type="execution_failure",
            owner="phase1-runtime",
            status="failed",
            metadata={"failure_layer": "backend", "observed": "first-token !", "stack": "DS14B compressed-tensors WNA16"},
        )
        observation = SemanticObservation(
            task="debug vLLM pathology",
            source_observation_ids=[raw_failure.object_id],
            understood_facts=["first-token pathology on DS14B compressed-tensors WNA16"],
            boundaries=["failure is stack-specific"],
            decisions=["reject DS14B compressed-tensors WNA16 for production"],
            confidence="high",
        )
        candidate = self.build_candidate(
            claim="DS14B compressed-tensors WNA16 is rejected for the current vLLM stack.",
            source_provenance="derived",
            evidence_refs=[
                EvidenceReference(source_kind="runtime_object", source_id=raw_failure.object_id, summary="Raw failure record."),
                EvidenceReference(source_kind="semantic_observation", source_id=observation.task, summary="Failure lesson abstraction."),
            ],
            scope=self.build_scope(project="UAEA", phase="Phase-2A", backend="vLLM", model="DS14B", hardware="RTX 5090D 24GB"),
            extraction_confidence=0.89,
            proposed_validity="Current vLLM 0.26.0 stack only",
            representation_facet_hint="failure lesson",
            relation_hint="reject current artifact",
        )

        report = candidate.validate_structure()
        self.assertTrue(report.valid, report.issues)
        self.assertEqual(candidate.source_provenance, "derived")
        self.assertEqual(candidate.relation_hint, "reject current artifact")
        self.assertEqual(candidate.to_dict()["representation_facet_hint"], "failure lesson")

    def test_supersession_candidate_keeps_relationship_hint_without_becoming_memory(self):
        previous_decision = RuntimeObjectRecord(
            object_type="architecture_decision",
            owner="phase2b-review",
            status="accepted",
            metadata={"decision": "DS14B production candidate"},
        )
        candidate = self.build_candidate(
            claim="Qwen2.5-14B-Instruct-AWQ supersedes DS14B compressed-tensors WNA16 as current production candidate.",
            source_provenance="derived",
            evidence_refs=[
                EvidenceReference(source_kind="runtime_object", source_id=previous_decision.object_id, summary="Earlier architecture decision."),
            ],
            scope=self.build_scope(project="UAEA", phase="Phase-2A", backend="vLLM", decision="model selection"),
            extraction_confidence=0.91,
            proposed_validity="Current model selection baseline",
            relation_hint="supersedes",
            representation_facet_hint="decision",
        )

        report = candidate.validate_structure()
        self.assertTrue(report.valid, report.issues)
        self.assertEqual(candidate.relation_hint, "supersedes")
        self.assertNotIn("memory_confidence", candidate.to_dict())
        self.assertIn(candidate.candidate_state, ALLOWED_CANDIDATE_STATES)

    def test_candidate_lifecycle_supports_defer_and_close_without_memory_promotion(self):
        candidate = self.build_candidate(
            claim="User preference may be to keep project review architecture-first.",
            source_provenance="inferred",
            evidence_refs=[
                EvidenceReference(source_kind="conversation_event", source_id="evt-1", summary="repeated preference hint"),
            ],
            scope=ScopeHypothesis.from_mapping(summary="UAEA / Phase-2B / review style"),
            extraction_confidence=0.55,
        )

        deferred = candidate.defer()
        closed = deferred.close()

        self.assertEqual(candidate.candidate_state, "open")
        self.assertEqual(deferred.candidate_state, "deferred")
        self.assertEqual(closed.candidate_state, "closed")
        self.assertIsInstance(closed, MemoryCandidate)

    def test_structure_validation_rejects_missing_evidence_and_scope(self):
        candidate = self.build_candidate(
            claim="Underspecified claim",
            source_provenance="explicit",
            evidence_refs=[],
            scope=ScopeHypothesis(),
            extraction_confidence=0.4,
        )

        report = candidate.validate_structure()
        self.assertFalse(report.valid)
        self.assertIn("evidence_references missing", report.issues)
        self.assertIn("scope_hypothesis missing", report.issues)

    def test_candidate_payload_survives_without_original_context(self):
        reference = EvidenceReference(
            source_kind="semantic_observation",
            source_id="semantic-123",
            source_event_id="event-123",
            location="boundaries[0]",
            summary="Artifact compatibility requires representation-level validation.",
        )
        candidate = self.build_candidate(
            claim="Artifact compatibility requires representation-level validation.",
            source_provenance="observed",
            evidence_refs=[reference],
            scope=self.build_scope(project="UAEA", phase="Phase-2B", subject="artifact compatibility"),
            extraction_confidence=0.87,
            representation_facet_hint="semantic",
        )

        payload = candidate.policy_payload()
        self.assertEqual(payload["evidence_references"][0]["source_id"], "semantic-123")
        self.assertEqual(payload["evidence_references"][0]["location"], "boundaries[0]")
        self.assertEqual(payload["claim"], "Artifact compatibility requires representation-level validation.")
        self.assertTrue(candidate.is_structurally_valid())


if __name__ == "__main__":
    unittest.main()
