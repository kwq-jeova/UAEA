from __future__ import annotations

import json
from copy import deepcopy
import unittest
from pathlib import Path

from memory.candidate import EvidenceReference, MemoryCandidate, ScopeHypothesis
from memory.scenario_fixture import evaluate_fixture


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = PROJECT_ROOT / "data" / "memory_test_fixtures" / "long_context_mixed_100.json"


class MemoryArchitectureFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_fixture_models_one_hundred_mixed_turns(self):
        turns = self.fixture["turns"]
        self.assertEqual(len(turns), 100)
        categories = {turn["category"] for turn in turns}
        for expected in {
            "goal",
            "explicit_constraint",
            "preference_signal",
            "technical_fact",
            "failure",
            "failure_lesson",
            "supersession",
            "unresolved_issue",
            "rejected_candidate",
            "noise",
        }:
            self.assertIn(expected, categories)

    def test_expected_candidates_are_structurally_valid_memory_candidates(self):
        for candidate_data in self.fixture["expected_candidates"]:
            with self.subTest(candidate_id=candidate_data["candidate_id"]):
                candidate = self._candidate_from_fixture(candidate_data)
                report = candidate.validate_structure()
                self.assertTrue(report.valid, report.issues)
                self.assertNotIn("memory_confidence", candidate.to_dict())
                self.assertNotIn("final_validity", candidate.to_dict())
                self.assertNotIn("truth_value", candidate.to_dict())

    def test_candidate_evidence_references_trace_to_fixture_turns(self):
        turn_ids = {turn["turn_id"] for turn in self.fixture["turns"]}
        for candidate_data in self.fixture["expected_candidates"]:
            with self.subTest(candidate_id=candidate_data["candidate_id"]):
                for reference in candidate_data["evidence_references"]:
                    self.assertEqual(reference["source_kind"], "conversation_turn")
                    self.assertIn(reference["source_id"], turn_ids)
                    self.assertIn(reference["source_event_id"], turn_ids)

    def test_fixture_keeps_memory_structure_smaller_than_context(self):
        outcome = self.fixture["expected_outcome"]
        candidate_ids = {candidate["candidate_id"] for candidate in self.fixture["expected_candidates"]}
        outcome_ids = set()
        for key in (
            "active_memory_candidate_ids",
            "dormant_or_low_priority_candidate_ids",
            "deferred_candidate_ids",
            "rejected_candidate_ids",
        ):
            outcome_ids.update(outcome[key])
        self.assertTrue(outcome_ids.issubset(candidate_ids))
        self.assertLessEqual(len(outcome["active_memory_candidate_ids"]), outcome["memory_count_upper_bound"])
        self.assertLess(outcome["memory_count_upper_bound"], len(self.fixture["turns"]))

    def test_noise_turns_do_not_become_expected_candidates(self):
        noise_turns = set(self.fixture["expected_non_memory_turn_ids"])
        evidence_turns = {
            reference["source_id"]
            for candidate in self.fixture["expected_candidates"]
            for reference in candidate["evidence_references"]
        }
        self.assertTrue(noise_turns)
        self.assertTrue(noise_turns.isdisjoint(evidence_turns))

    def test_fixture_exercises_required_real_cases(self):
        by_id = {candidate["candidate_id"]: candidate for candidate in self.fixture["expected_candidates"]}
        expected = {
            "C001": ("explicit", "constraint"),
            "C003": ("inferred", "preference"),
            "C004": ("measured", "semantic"),
            "C005": ("derived", "failure lesson"),
            "C006": ("derived", "decision"),
        }
        for candidate_id, (provenance, facet) in expected.items():
            with self.subTest(candidate_id=candidate_id):
                candidate = by_id[candidate_id]
                self.assertEqual(candidate["source_provenance"], provenance)
                self.assertEqual(candidate["representation_facet_hint"], facet)

    def test_fixture_passes_black_box_evaluator(self):
        report = evaluate_fixture(self.fixture)

        self.assertTrue(report.valid, report.issues)
        self.assertEqual(report.metrics["turn_count"], 100)
        self.assertEqual(report.metrics["candidate_count"], len(self.fixture["expected_candidates"]))
        self.assertEqual(report.metrics["retrieval_probe_count"], 5)

    def test_black_box_evaluator_detects_scope_loss(self):
        fixture = deepcopy(self.fixture)
        candidate = next(item for item in fixture["expected_candidates"] if item["candidate_id"] == "C005")
        candidate["scope_hypothesis"]["dimensions"].pop("artifact")

        report = evaluate_fixture(fixture)

        self.assertFalse(report.valid)
        self.assertTrue(
            any("retrieval_probe Q-B candidate C005 missing required scope dimensions: artifact" in issue for issue in report.issues),
            report.issues,
        )

    def test_rejected_candidate_remains_candidate_not_memory(self):
        outcome = self.fixture["expected_outcome"]
        self.assertIn("C009", outcome["rejected_candidate_ids"])
        self.assertNotIn("C009", outcome["active_memory_candidate_ids"])
        rejected = next(candidate for candidate in self.fixture["expected_candidates"] if candidate["candidate_id"] == "C009")
        self.assertEqual(rejected["claim"], "All AWQ models are unreliable.")
        self.assertIn("Reject or constrain", rejected["validation_requirements"][0])

    def test_supersession_is_expected_outcome_not_candidate_authority(self):
        outcome = self.fixture["expected_outcome"]
        edge = outcome["supersession_edges"][0]
        candidate = next(candidate for candidate in self.fixture["expected_candidates"] if candidate["candidate_id"] == edge["to_candidate_id"])
        self.assertEqual(candidate["relation_hint"], "supersedes")
        hydrated = self._candidate_from_fixture(candidate)
        self.assertEqual(hydrated.relation_hint, "supersedes")
        self.assertNotIn("superseded_by", hydrated.to_dict())

    def _candidate_from_fixture(self, candidate_data: dict[str, object]) -> MemoryCandidate:
        scope = candidate_data["scope_hypothesis"]
        assert isinstance(scope, dict)
        return MemoryCandidate(
            candidate_id=str(candidate_data["candidate_id"]),
            claim=str(candidate_data["claim"]),
            source_provenance=str(candidate_data["source_provenance"]),
            evidence_references=tuple(
                EvidenceReference(
                    source_kind=str(reference["source_kind"]),
                    source_id=str(reference["source_id"]),
                    source_event_id=str(reference.get("source_event_id", "")),
                    location=str(reference.get("location", "")),
                    summary=str(reference.get("summary", "")),
                )
                for reference in candidate_data["evidence_references"]
            ),
            scope_hypothesis=ScopeHypothesis.from_mapping(
                summary=str(scope.get("summary", "")),
                dimensions=scope.get("dimensions", {}),
            ),
            extraction_confidence=float(candidate_data["extraction_confidence"]),
            evidence_summary=str(candidate_data.get("evidence_summary", "")),
            validation_requirements=tuple(candidate_data.get("validation_requirements", ())),
            proposed_validity=str(candidate_data.get("proposed_validity", "")),
            representation_facet_hint=str(candidate_data.get("representation_facet_hint", "")),
            relation_hint=str(candidate_data.get("relation_hint", "")),
        )


if __name__ == "__main__":
    unittest.main()
