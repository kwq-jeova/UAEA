from __future__ import annotations

import json
import socket
import unittest
import urllib.error
from unittest.mock import patch

from backend.lmf_backend import LMFBackend
from backend.model_client import ModelClient
from backend.models import InferenceRequest, InferenceResponse


class FakeHTTPResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


class RecordingBackend:
    backend_name = "recording"
    model_name = "recording-model"

    def __init__(self, response: InferenceResponse) -> None:
        self.response = response
        self.requests = []

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        self.requests.append(request)
        return self.response


class LMFBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = LMFBackend("http://127.0.0.1:8000/v1", "test-model", timeout_seconds=3)
        self.request = InferenceRequest(
            task_type="semantic_observation",
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=128,
            temperature=0.2,
        )

    @patch("backend.lmf_backend.urllib.request.urlopen")
    def test_converts_openai_compatible_response(self, urlopen):
        urlopen.return_value = FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {"content": "model response"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 4,
                    "total_tokens": 16,
                },
            }
        )

        response = self.backend.generate(self.request)

        self.assertTrue(response.ok)
        self.assertEqual(response.text, "model response")
        self.assertEqual(response.backend, "lmf")
        self.assertEqual(response.usage.total_tokens, 16)
        sent_request = urlopen.call_args.args[0]
        sent_payload = json.loads(sent_request.data.decode("utf-8"))
        self.assertEqual(sent_payload["max_tokens"], 128)
        self.assertEqual(sent_payload["temperature"], 0.2)

    @patch("backend.lmf_backend.urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused"))
    def test_api_unavailable_returns_controlled_error(self, _urlopen):
        response = self.backend.generate(self.request)

        self.assertFalse(response.ok)
        self.assertEqual(response.error.code, "unavailable")
        self.assertTrue(response.error.retryable)

    @patch("backend.lmf_backend.urllib.request.urlopen", side_effect=socket.timeout("timed out"))
    def test_timeout_returns_controlled_error(self, _urlopen):
        response = self.backend.generate(self.request)

        self.assertFalse(response.ok)
        self.assertEqual(response.error.code, "timeout")
        self.assertIn("timed out", response.error.message)

    @patch("backend.lmf_backend.urllib.request.urlopen")
    def test_invalid_response_returns_controlled_error(self, urlopen):
        urlopen.return_value = FakeHTTPResponse({"unexpected": True})

        response = self.backend.generate(self.request)

        self.assertFalse(response.ok)
        self.assertEqual(response.error.code, "invalid_response")

    def test_model_client_exposes_generate_and_phase1_chat_contract(self):
        backend = RecordingBackend(
            InferenceResponse(
                text="ok",
                backend="recording",
                model="recording-model",
                finish_reason="stop",
            )
        )
        client = ModelClient(backend)

        text = client.chat([{"role": "user", "content": "hello"}], max_tokens=32)

        self.assertEqual(text, "ok")
        self.assertEqual(client.last_finish_reason, "stop")
        self.assertEqual(backend.requests[0].task_type, "phase1_runtime")

    def test_model_client_raises_runtime_error_for_phase1_failure_path(self):
        response = self.backend._error_response(0.0, "timeout", "Model API request timed out.", True)
        client = ModelClient(RecordingBackend(response))

        with self.assertRaisesRegex(RuntimeError, "timed out"):
            client.chat([{"role": "user", "content": "hello"}])


if __name__ == "__main__":
    unittest.main()
