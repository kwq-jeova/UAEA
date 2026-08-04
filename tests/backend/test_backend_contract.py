from __future__ import annotations

import json
import socket
import unittest
from unittest.mock import patch

from backend.lmf_backend import LMFBackend
from backend.mock_backend import MockBackend
from backend.model_client import ModelBackend, ModelClient
from backend.models import InferenceRequest
from phase2.runtime_factory import build_agent


class FakeHTTPResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class BackendContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = InferenceRequest(
            task_type="semantic_observation",
            messages=[{"role": "user", "content": "evaluate section one"}],
            max_tokens=128,
        )

    def assert_success_contract(self, backend: ModelBackend, expected_backend: str) -> None:
        response = backend.generate(self.request)

        self.assertTrue(response.ok)
        self.assertIsInstance(response.text, str)
        self.assertTrue(response.text)
        self.assertEqual(response.backend, expected_backend)
        self.assertTrue(response.model)
        self.assertEqual(response.finish_reason, "stop")
        self.assertGreaterEqual(response.usage.total_tokens, response.usage.completion_tokens)
        self.assertGreaterEqual(response.latency_ms, 0.0)

    def test_mock_backend_normal_response_follows_contract(self):
        backend = MockBackend("deterministic semantic result")

        self.assert_success_contract(backend, "mock")
        self.assertEqual(backend.requests, [self.request])

    @patch("backend.lmf_backend.urllib.request.urlopen")
    def test_lmf_backend_normal_response_follows_contract(self, urlopen):
        urlopen.return_value = FakeHTTPResponse(
            {
                "choices": [{"message": {"content": "lmf result"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            }
        )
        backend = LMFBackend("http://127.0.0.1:8000/v1", "test-model")

        self.assert_success_contract(backend, "lmf")

    def test_mock_failure_modes_are_structured(self):
        for mode in ("timeout", "unavailable", "invalid_response"):
            with self.subTest(mode=mode):
                response = MockBackend(failure_mode=mode).generate(self.request)
                self.assertFalse(response.ok)
                self.assertEqual(response.error.code, mode)
                self.assertEqual(response.finish_reason, "error")

    @patch("backend.lmf_backend.urllib.request.urlopen", side_effect=socket.timeout("timed out"))
    def test_lmf_timeout_matches_controlled_failure_contract(self, _urlopen):
        response = LMFBackend("http://127.0.0.1:8000/v1", "test-model").generate(self.request)

        self.assertFalse(response.ok)
        self.assertEqual(response.error.code, "timeout")
        self.assertTrue(response.error.retryable)

    @patch("backend.lmf_backend.urllib.request.urlopen")
    def test_lmf_invalid_response_is_structured(self, urlopen):
        urlopen.return_value = FakeHTTPResponse({"unexpected": True})

        response = LMFBackend("http://127.0.0.1:8000/v1", "test-model").generate(self.request)

        self.assertFalse(response.ok)
        self.assertEqual(response.error.code, "invalid_response")

    def test_model_client_converts_backend_failure_for_frozen_runtime(self):
        client = ModelClient(MockBackend(failure_mode="timeout"))

        with self.assertRaisesRegex(RuntimeError, "timed out"):
            client.chat([{"role": "user", "content": "continue"}])

    def test_backend_switching_does_not_change_frozen_agent_construction(self):
        mock_backend = MockBackend("planner response")
        mock_agent, _, _ = build_agent(backend=mock_backend)
        lmf_agent, _, _ = build_agent()

        self.assertIs(mock_agent.model.backend, mock_backend)
        self.assertIsInstance(lmf_agent.model.backend, LMFBackend)
        self.assertEqual(type(mock_agent), type(lmf_agent))


if __name__ == "__main__":
    unittest.main()
