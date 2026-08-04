from __future__ import annotations

import unittest

from backend.interface import InferenceMetadata, InferenceRequest, InferenceResult, TokenUsage
from backend.phase1_bridge import Phase1ModelClientBridge
from backend.transformers_backend import TransformersBackend
from benchmark.inference.runner import InferenceBenchmarkRunner, WorkloadCase


class FakePhase1Client:
    model_name = "fake-transformers-model"

    def __init__(self) -> None:
        self.last_finish_reason = None
        self.last_usage = None
        self.calls = []

    def chat(self, messages, max_tokens=256, temperature=0.1):
        self.calls.append((messages, max_tokens, temperature))
        self.last_finish_reason = "stop"
        self.last_usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }
        return "backend response"


class FakeBackend:
    backend_name = "fake"
    model_name = "fake-model"

    def generate(self, request: InferenceRequest) -> InferenceResult:
        return InferenceResult(
            content="bridge response",
            metadata=InferenceMetadata(
                backend=self.backend_name,
                model=self.model_name,
                finish_reason="stop",
                usage=TokenUsage(11, 7, 18),
                latency_ms=12.0,
                tokens_per_second=20.0,
            ),
        )


class BackendContractTests(unittest.TestCase):
    def test_transformers_backend_wraps_phase1_chat_client(self):
        client = FakePhase1Client()
        backend = TransformersBackend(client)

        result = backend.generate(
            InferenceRequest(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=64,
                temperature=0.2,
            )
        )

        self.assertEqual(result.content, "backend response")
        self.assertEqual(result.metadata.backend, "transformers")
        self.assertEqual(result.metadata.model, client.model_name)
        self.assertEqual(result.metadata.finish_reason, "stop")
        self.assertEqual(result.metadata.usage.total_tokens, 15)
        self.assertEqual(client.calls[0][1:], (64, 0.2))

    def test_phase1_bridge_preserves_frozen_model_client_contract(self):
        bridge = Phase1ModelClientBridge(FakeBackend())

        content = bridge.chat([{"role": "user", "content": "hello"}], max_tokens=32)

        self.assertEqual(content, "bridge response")
        self.assertEqual(bridge.last_finish_reason, "stop")
        self.assertEqual(bridge.last_usage["total_tokens"], 18)

    def test_inference_runner_keeps_physical_metrics_outside_backend_contract(self):
        samples = InferenceBenchmarkRunner().run(
            FakeBackend(),
            [WorkloadCase("planner", "planner", [{"role": "user", "content": "plan"}])],
        )

        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].backend, "fake")
        self.assertIsNone(samples[0].sm_utilization_percent)
        self.assertIsNone(samples[0].kv_cache_used_mb)


if __name__ == "__main__":
    unittest.main()
