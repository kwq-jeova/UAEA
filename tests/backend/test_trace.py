from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.mock_backend import MockBackend
from backend.models import InferenceRequest
from backend.trace import JsonlTraceSink, TracingBackend
from benchmark.inference.runner import InferenceBenchmarkRunner, WorkloadCase


class DummyMetricsCollector:
    def sample(self) -> dict[str, float | None]:
        return {
            "sm_utilization_percent": None,
            "vram_used_mb": None,
            "kv_cache_used_mb": None,
        }


class TraceLayerTests(unittest.TestCase):
    def test_tracing_backend_emits_jsonl_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "traces.jsonl"
            sink = JsonlTraceSink(trace_path)
            backend = TracingBackend(MockBackend("trace response"), sink, {"model_artifact": "mock-artifact"})

            response = backend.generate(
                InferenceRequest(
                    messages=[{"role": "system", "content": "Answer directly."}, {"role": "user", "content": "hello"}],
                    task_type="chat_answer",
                    max_tokens=32,
                    temperature=0.0,
                    request_id="case-001",
                    trace_context={"phase": "chat_answer"},
                )
            )

            self.assertTrue(response.ok)
            payload = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(payload), 1)
            record = payload[0]
            self.assertEqual(record["request_id"], "case-001")
            self.assertEqual(record["phase"], "chat_answer")
            self.assertEqual(record["model_artifact"], "mock-artifact")
            self.assertEqual(record["backend"], "mock")
            self.assertEqual(record["generation_config"]["max_tokens"], 32)
            self.assertEqual(record["generation_config"]["temperature"], 0.0)
            self.assertEqual(record["finish_reason"], "stop")
            self.assertGreaterEqual(record["output_tokens"], 1)

    def test_inference_benchmark_runner_passes_case_metadata_to_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "benchmark-traces.jsonl"
            sink = JsonlTraceSink(trace_path)
            runner = InferenceBenchmarkRunner(DummyMetricsCollector(), trace_sink=sink)
            backend = MockBackend("benchmark response")
            samples = runner.run(
                backend,
                [
                    WorkloadCase(
                        case_id="L0-01",
                        category="chat_answer",
                        messages=[{"role": "user", "content": "Explain UAEA."}],
                        max_tokens=48,
                        trace_context={"model_artifact": "benchmark-artifact"},
                    )
                ],
            )

            self.assertEqual(len(samples), 1)
            payload = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(payload), 1)
            record = payload[0]
            self.assertEqual(record["case_id"], "L0-01")
            self.assertEqual(record["phase"], "chat_answer")
            self.assertEqual(record["model_artifact"], "benchmark-artifact")
            self.assertEqual(record["backend"], "mock")


if __name__ == "__main__":
    unittest.main()
