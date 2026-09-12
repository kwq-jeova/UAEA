from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from runtime.action_normalizer import ActionNormalizer  # noqa: E402
from runtime.action_request import ActionRequest  # noqa: E402
from runtime.agent_runtime import Agent  # noqa: E402
from runtime.capability import CapabilityMetadata, ToolResult  # noqa: E402
from runtime.ledger import LedgerStub  # noqa: E402
from runtime.sandbox import Sandbox  # noqa: E402
from runtime.semantic_observation import ExecutionObservation  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402


class CapabilityContractTests(unittest.TestCase):
    def test_action_request_serializes_minimal_boundary(self):
        request = ActionRequest(
            capability="web.search",
            parameters={"query": "Claude runtime structure"},
            goal_ref="goal-1",
            continuation_ref="turn-2",
        )

        data = request.to_dict()

        self.assertEqual(data["capability"], "web.search")
        self.assertEqual(data["parameters"], {"query": "Claude runtime structure"})
        self.assertEqual(data["goal_ref"], "goal-1")
        self.assertEqual(data["continuation_ref"], "turn-2")
        self.assertTrue(data["request_id"])

    def test_document_fs_and_mock_external_share_capability_observation_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            (sandbox_root / "README.md").write_text(
                "# Fixture\n\n## First\n\nsection body\n",
                encoding="utf-8",
            )
            (sandbox_root / "notes.txt").write_text("notes", encoding="utf-8")
            registry = ToolRegistry(Sandbox(root, sandbox_root), LedgerStub(root / "traces"))

            def external_operation(arguments: dict, objective: str) -> ToolResult:
                return ToolResult(
                    True,
                    "mock external operation completed",
                    {
                        "operation_id": "mock-op-1",
                        "received": dict(arguments),
                        "objective": objective,
                        "external_ref": "mock://external/mock-op-1",
                    },
                )

            registry.register_capability(
                CapabilityMetadata(
                    name="mock.external_operation",
                    tool_name="mock_external_operation",
                    version="0.1",
                    permission="external",
                    produces_observation=True,
                    context_cost="low",
                    future_phase="test",
                ),
                external_operation,
            )

            cases = [
                ("document.read_section", {"path": "README.md", "section_index": 1}, "read_section"),
                ("fs.list", {"path": "."}, "list_files"),
                ("mock.external_operation", {"target": "fixture"}, "mock_external_operation"),
            ]
            observations = []
            for capability, arguments, tool_name in cases:
                result = registry.execute_capability(capability, arguments, f"execute {capability}")
                observations.append(ExecutionObservation.from_tool_result(tool_name, result))

        self.assertEqual([item.capability for item in observations], [case[0] for case in cases])
        self.assertEqual([item.tool_name for item in observations], [case[2] for case in cases])
        self.assertTrue(all(item.status == "success" for item in observations))

    def test_phase1_builtin_read_file_uses_capability_registration_boundary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            (sandbox_root / "README.md").write_text("# Local fixture\n\nhello", encoding="utf-8")
            registry = ToolRegistry(Sandbox(root, sandbox_root), LedgerStub(root / "traces"))

            result = registry.execute_capability(
                "document.read_file",
                {"path": "README.md"},
                "read README",
            )
            observation = ExecutionObservation.from_tool_result("read_file", result)

        self.assertTrue(result.ok)
        self.assertIn("document.read_file", registry.capability_names)
        self.assertEqual(registry.capability_to_tool["document.read_file"], "read_file")
        self.assertEqual(registry.tool_to_capability["read_file"], "document.read_file")
        self.assertEqual(result.data["capability"], "document.read_file")
        self.assertEqual(result.data["tool"], "read_file")
        self.assertEqual(observation.capability, "document.read_file")
        self.assertEqual(observation.status, "success")

    def test_custom_capability_can_register_without_agent_or_model_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))

            def echo(arguments: dict, objective: str) -> ToolResult:
                return ToolResult(True, "echoed", {"text": arguments.get("text"), "objective": objective})

            registry.register_capability(
                CapabilityMetadata(
                    name="example.echo",
                    tool_name="echo",
                    version="0.1",
                    permission="read",
                    produces_observation=True,
                    context_cost="low",
                    future_phase="test",
                ),
                echo,
            )

            result = registry.execute_capability("example.echo", {"text": "hello"}, "echo task")
            observation = ExecutionObservation.from_tool_result("echo", result)

        self.assertTrue(result.ok)
        self.assertEqual(result.data["capability"], "example.echo")
        self.assertEqual(result.data["tool"], "echo")
        self.assertEqual(observation.capability, "example.echo")
        self.assertEqual(observation.tool_name, "echo")

    def test_action_normalizer_accepts_registered_capability_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            registry.register_capability(
                CapabilityMetadata(
                    name="example.echo",
                    tool_name="echo",
                    version="0.1",
                    permission="read",
                    produces_observation=True,
                    context_cost="low",
                    future_phase="test",
                ),
                lambda arguments, objective: ToolResult(True, "echoed", dict(arguments)),
            )
            normalizer = ActionNormalizer(
                tool_names=registry.names,
                capability_names=registry.capability_names,
                capability_to_tool=registry.capability_to_tool,
                tool_to_capability=registry.tool_to_capability,
            )

            normalized = normalizer.normalize_object(
                {
                    "type": "capability_action",
                    "capability": "example.echo",
                    "arguments": {"text": "hello"},
                    "after_observation": "answer_with_observation",
                }
            )

        self.assertIsNotNone(normalized)
        assert normalized is not None
        self.assertEqual(normalized.action, "tool_then_answer")
        self.assertEqual(normalized.capability, "example.echo")
        self.assertEqual(normalized.tool, "echo")
        self.assertEqual(normalized.arguments, {"text": "hello"})

    def test_duplicate_capability_registration_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))

            with self.assertRaises(ValueError):
                registry.register_capability(
                    CapabilityMetadata(
                        name="document.read_file",
                        tool_name="other_read_file",
                        version="0.1",
                        permission="read",
                        produces_observation=True,
                        context_cost="low",
                        future_phase="test",
                    ),
                    lambda arguments, objective: ToolResult(True, "ok", {}),
                )

    def test_agent_can_execute_pre_registered_mock_external_capability_without_file_fs_special_case(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            (sandbox_root / "README.md").write_text("# Fixture\n\ncontent", encoding="utf-8")
            ledger = LedgerStub(root / "traces")
            registry = ToolRegistry(Sandbox(root, sandbox_root), ledger)
            captured_arguments: list[dict] = []

            def external_operation(arguments: dict, objective: str) -> ToolResult:
                captured_arguments.append(dict(arguments))
                return ToolResult(
                    True,
                    "mock external operation completed",
                    {
                        "operation_id": "mock-op-1",
                        "received": dict(arguments),
                        "external_ref": "mock://external/mock-op-1",
                    },
                )

            registry.register_capability(
                CapabilityMetadata(
                    name="mock.external_operation",
                    tool_name="mock_external_operation",
                    version="0.1",
                    permission="external",
                    produces_observation=True,
                    context_cost="low",
                    future_phase="test",
                ),
                external_operation,
            )
            model = FakeCapabilityModel()
            agent = Agent(model, registry, ledger)

            response = agent.handle("Run the mock external operation for README.md and explain the result.")
            events = [json.loads(line) for line in ledger.path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(captured_arguments, [{"target": "README.md"}])
        self.assertIn("Mock external operation completed.", response)
        self.assertIn("mock.external_operation", model.action_prompt)
        tool_events = [event for event in events if event["event_type"] == "tool_event"]
        execution_events = [event for event in events if event["event_type"] == "execution_observation_event"]
        self.assertEqual(tool_events[-1]["metadata"]["tool_name"], "mock_external_operation")
        self.assertEqual(tool_events[-1]["metadata"]["output"]["capability"], "mock.external_operation")
        self.assertEqual(execution_events[-1]["metadata"]["capability"], "mock.external_operation")
        self.assertEqual(execution_events[-1]["metadata"]["tool_name"], "mock_external_operation")
        self.assertEqual(agent.last_execution_observation.capability, "mock.external_operation")

    def test_agent_accepts_capability_registered_after_initialization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            ledger = LedgerStub(root / "traces")
            registry = ToolRegistry(Sandbox(root, sandbox_root), ledger)
            model = FakeLateRegisteredCapabilityModel()
            agent = Agent(model, registry, ledger)
            captured_arguments: list[dict] = []

            def late_operation(arguments: dict, objective: str) -> ToolResult:
                captured_arguments.append(dict(arguments))
                return ToolResult(
                    True,
                    "late operation completed",
                    {
                        "operation_id": "late-op-1",
                        "received": dict(arguments),
                    },
                )

            registry.register_capability(
                CapabilityMetadata(
                    name="mock.late_operation",
                    tool_name="mock_late_operation",
                    version="0.1",
                    permission="external",
                    produces_observation=True,
                    context_cost="low",
                    future_phase="test",
                ),
                late_operation,
            )

            response = agent.handle("Run the mock.late_operation capability.")
            events = [json.loads(line) for line in ledger.path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(captured_arguments, [{"target": "late"}])
        self.assertIn("Late registered operation completed.", response)
        self.assertIn("mock.late_operation", model.action_prompt)
        tool_events = [event for event in events if event["event_type"] == "tool_event"]
        execution_events = [event for event in events if event["event_type"] == "execution_observation_event"]
        self.assertEqual(tool_events[-1]["metadata"]["tool_name"], "mock_late_operation")
        self.assertEqual(tool_events[-1]["metadata"]["output"]["capability"], "mock.late_operation")
        self.assertEqual(execution_events[-1]["metadata"]["capability"], "mock.late_operation")
        self.assertEqual(execution_events[-1]["metadata"]["tool_name"], "mock_late_operation")
        self.assertEqual(agent.last_execution_observation.capability, "mock.late_operation")


class FakeCapabilityModel:
    def __init__(self) -> None:
        self.calls: list[list[dict]] = []
        self.action_prompt = ""
        self.last_finish_reason = "stop"

    def chat(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.0) -> str:
        self.calls.append(messages)
        system = str(messages[0].get("content") or "")
        if "semantic action planner" in system:
            self.action_prompt = "\n".join(str(message.get("content") or "") for message in messages)
            return json.dumps(
                {
                    "type": "capability_action",
                    "capability": "mock.external_operation",
                    "arguments": {"target": "README.md"},
                    "after_observation": "answer_with_observation",
                    "reason_summary": "Run a pre-registered non-file external capability.",
                    "goal_hypothesis": "Validate generic capability execution.",
                    "goal_confidence": "high",
                    "goal_status": "inferred",
                },
                ensure_ascii=False,
            )
        if "Use the provided Execution Observation as factual evidence." in system:
            return (
                "Answer:\n"
                "Mock external operation completed.\n\n"
                "Semantic Observation:\n"
                "Task:\n"
                "Validate generic capability execution.\n\n"
                "Understood Facts:\n"
                "- mock.external_operation returned a successful ToolResult.\n\n"
                "Key Points:\n"
                "- The execution was not a document or filesystem capability.\n\n"
                "Principles:\n"
                "- Runtime validates and executes capability actions.\n\n"
                "Boundaries:\n"
                "- This is a deterministic test capability, not Web or Memory.\n\n"
                "Risks:\n"
                "- Agent-facing capability visibility still depends on initialization-time registration.\n\n"
                "Decisions:\n"
                "- Treat the result as an ExecutionObservation.\n\n"
                "Open Questions:\n"
                "- None for this test.\n\n"
                "Evidence:\n"
                "- source: mock.external_operation\n\n"
                "Confidence:\n"
                "high"
            )
        return "Fallback response."


class FakeLateRegisteredCapabilityModel:
    def __init__(self) -> None:
        self.calls: list[list[dict]] = []
        self.action_prompt = ""
        self.last_finish_reason = "stop"

    def chat(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.0) -> str:
        self.calls.append(messages)
        system = str(messages[0].get("content") or "")
        if "semantic action planner" in system:
            self.action_prompt = "\n".join(str(message.get("content") or "") for message in messages)
            return json.dumps(
                {
                    "type": "capability_action",
                    "capability": "mock.late_operation",
                    "arguments": {"target": "late"},
                    "after_observation": "answer_with_observation",
                    "reason_summary": "Run a capability registered after Agent initialization.",
                    "goal_hypothesis": "Validate late capability visibility.",
                    "goal_confidence": "high",
                    "goal_status": "inferred",
                },
                ensure_ascii=False,
            )
        if "Use the provided Execution Observation as factual evidence." in system:
            return (
                "Answer:\n"
                "Late registered operation completed.\n\n"
                "Semantic Observation:\n"
                "Task:\n"
                "Validate late capability visibility.\n\n"
                "Understood Facts:\n"
                "- mock.late_operation returned a successful ToolResult.\n\n"
                "Key Points:\n"
                "- Agent refreshed its action normalizer from the current registry.\n\n"
                "Principles:\n"
                "- Capability visibility and action validation should share the same registry state.\n\n"
                "Boundaries:\n"
                "- This does not change Agent.handle or ModelClient.\n\n"
                "Risks:\n"
                "- Runtime workflow policy is still narrower than single capability execution.\n\n"
                "Decisions:\n"
                "- Accept the late registered capability action.\n\n"
                "Open Questions:\n"
                "- None for this test.\n\n"
                "Evidence:\n"
                "- source: mock.late_operation\n\n"
                "Confidence:\n"
                "high"
            )
        return "Fallback response."


if __name__ == "__main__":
    unittest.main()
