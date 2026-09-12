from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from runtime.agent_runtime import Agent  # noqa: E402
from runtime.ledger import LedgerStub  # noqa: E402
from runtime.sandbox import Sandbox  # noqa: E402
from runtime.semantic_observation import ExecutionObservation, SemanticObservation  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402


class FakeTurnRelationModel:
    def __init__(self) -> None:
        self.calls: list[list[dict]] = []
        self.last_finish_reason = "stop"

    def chat(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.0) -> str:
        self.calls.append(messages)
        system = str(messages[0].get("content") or "")
        if "Use the cached Semantic Observation" in system:
            return "Previous-context answer from cached observation."
        if "ordinary questions directly" in system:
            return "Direct answer path."
        if "semantic action planner" in system:
            return '{"type": "answer", "reason": "fallback"}'
        return "Fallback model response."


class TurnRelationTests(unittest.TestCase):
    def _agent_with_prior_observation(self, capability: str = "web.search") -> Agent:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        sandbox_root = root / "sandbox"
        sandbox_root.mkdir()
        agent = Agent(
            FakeTurnRelationModel(),
            ToolRegistry(Sandbox(root, sandbox_root), LedgerStub(root / "traces")),
            LedgerStub(root / "traces"),
        )
        execution_observation = ExecutionObservation(
            observation_id="obs-1",
            capability=capability,
            tool_name=capability.replace(".", "_"),
            status="success",
            message="prior capability completed",
            data={"capability": capability, "summary": "prior result"},
        )
        semantic_observation = SemanticObservation(
            task="prior task",
            source_observation_ids=["obs-1"],
            understood_facts=["Prior execution produced a bounded observation."],
            key_points=["The next turn may refer to this result."],
            confidence="medium",
        )
        agent.last_execution_observation = execution_observation
        agent.last_semantic_observation = semantic_observation
        agent.context_manager.set_execution_context(
            execution_observation.capability,
            execution_observation.status,
            execution_observation.message,
            execution_observation.observation_id,
        )
        agent.context_manager.set_semantic_context(semantic_observation.compact_summary())
        return agent

    def tearDown(self) -> None:
        tmp = getattr(self, "tmp", None)
        if tmp is not None:
            tmp.cleanup()

    def test_challenge_followup_uses_previous_observation_not_direct_answer(self):
        agent = self._agent_with_prior_observation("web.search")

        response = agent.handle("任何相关的网页都没有吗？")

        self.assertEqual(response, "Previous-context answer from cached observation.")
        self.assertEqual(agent.context_manager.turn_relation.relation, "challenge")
        self.assertEqual(agent.context_manager.turn_relation.target_ref, "execution_observation:obs-1")
        self.assertEqual(agent.runtime_snapshot()["turn_relation"]["relation"], "challenge")
        self.assertIn("Turn Relation Context:", agent.context_manager.planner_context_text("检查上下文"))
        model = agent.model
        self.assertEqual(len(model.calls), 1)
        self.assertIn("Use the cached Semantic Observation", model.calls[0][0]["content"])

    def test_reference_followup_is_capability_agnostic(self):
        agent = self._agent_with_prior_observation("mock.external_operation")

        response = agent.handle("这个结果还有其他可能吗？")

        self.assertEqual(response, "Previous-context answer from cached observation.")
        self.assertEqual(agent.context_manager.turn_relation.relation, "challenge")
        self.assertEqual(agent.context_manager.turn_relation.target_ref, "execution_observation:obs-1")


if __name__ == "__main__":
    unittest.main()
