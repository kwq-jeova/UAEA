from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "runtime" / "phase1-runtime"))
from harness.generation_diagnostics import GenerationDiagnostics  # noqa: E402


class GenerationDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "generation.jsonl"
        self.recorder = GenerationDiagnostics(self.path)
        self.addCleanup(self.recorder.close)

    def rows(self):
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]

    def test_full_parser_result_and_input_identity_unchanged(self):
        request = SimpleNamespace(request_id="resp-full")
        result = SimpleNamespace(tools_called=True, tool_calls=[object()], content="hello")
        text = 'hello<tool_call>{"name":"web_search","arguments":{"query":"AI"}}</tool_call>'
        received = []

        def parser(instance, model_output, request):
            received.append((model_output, request))
            return result

        wrapped = self.recorder.parser_wrapper(parser, streaming=False)
        self.assertIs(wrapped(object(), text, request), result)
        self.assertIs(received[0][0], text)
        self.assertIs(received[0][1], request)
        rows = self.rows()
        self.assertEqual(rows[0]["response_id"], "resp-full")
        self.assertIn('<tool_call>{"name":"web_search"', rows[0]["fragment"])
        self.assertEqual(rows[1]["tool_call_count"], 1)
        self.assertTrue(rows[1]["tools_called"])

    def test_swallowed_json_error_is_observed_without_replacing_outcome(self):
        logger = logging.getLogger("uaea-test-hermes")
        handler = self.recorder.error_handler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        result = SimpleNamespace(tools_called=False, tool_calls=[], content="promise")

        def parser(instance, model_output, request):
            try:
                json.loads("\n")
            except json.JSONDecodeError:
                logger.exception("test parser error")
            return result

        actual = self.recorder.parser_wrapper(parser, streaming=False)(
            object(), "promise<tool_call>\n", SimpleNamespace(request_id="resp-bad"))
        self.assertIs(actual, result)
        rows = self.rows()
        error = next(row for row in rows if row["stage"] == "hermes_error")
        self.assertEqual(error["exception_type"], "JSONDecodeError")
        self.assertEqual(error["json_error_position"], 1)
        self.assertTrue(rows[-1]["parser_error_observed"])
        self.assertFalse(rows[-1]["tools_called"])

    def test_raised_exception_and_none_are_not_suppressed(self):
        exc = ValueError("original")

        def parser(instance, model_output, request):
            raise exc

        with self.assertRaises(ValueError) as caught:
            self.recorder.parser_wrapper(parser, streaming=False)(object(), "", object())
        self.assertIs(caught.exception, exc)
        self.assertEqual(self.rows()[-1]["stage"], "parser_raised")

        def streaming(instance, previous_text, current_text, delta_text, request):
            return None

        self.assertIsNone(self.recorder.parser_wrapper(streaming, streaming=True)(
            object(), "<tool_", "<tool_call>", "call>", SimpleNamespace(request_id="resp-none")))
        self.assertTrue(self.rows()[-1]["returned_none"])
        self.assertEqual(self.rows()[-2]["previous_chars"], 6)

    def test_generation_finish_reason_and_chunk_boundaries(self):
        class Context:
            _accumulated_text = ""

        calls = []

        def append(context, output):
            calls.append(output)
            context._accumulated_text += output.outputs[0].text

        wrapped = self.recorder.generation_wrapper(append, streaming=True)
        context = Context()
        for text, reason in [("promise<tool_", None), ("call>\n", "stop")]:
            output = SimpleNamespace(request_id="resp-raw_0", finished=bool(reason), outputs=[
                SimpleNamespace(text=text, token_ids=[1, 2], finish_reason=reason, stop_reason=151645)])
            wrapped(context, output)
            self.assertIs(calls[-1], output)
        rows = self.rows()
        final = rows[-1]
        self.assertEqual(final["stage"], "generation_finished")
        self.assertEqual(final["finish_reason"], "stop")
        self.assertEqual(final["stop_reason"], 151645)
        self.assertEqual(final["chunk_count"], 2)
        self.assertEqual(final["tool_start_tags"], 1)
        self.assertEqual(final["tool_end_tags"], 0)
        self.assertEqual(rows[0]["char_end"], rows[1]["char_start"])
        self.assertNotIn("prompt", str(rows))

    def test_redaction_precedes_truncation_and_handles_partial_secrets(self):
        secret = "test-credential-not-for-output"
        with patch.dict(os.environ, {"SERPAPI_KEY": secret}):
            recorder = GenerationDiagnostics(Path(self.tmp.name) / "secrets.jsonl", fragment_chars=128)
        self.addCleanup(recorder.close)
        text = '<tool_call>{"api_key":"' + secret + '","url":"https://user:pw@serpapi.com/search.json?api_key=' + secret + '"}'
        recorder.record("hermes_input", **recorder.fragment(text + ("x " * 300)))
        content = recorder.path.read_text(encoding="utf-8")
        self.assertNotIn(secret, content)
        self.assertNotIn("user:pw", content)
        self.assertNotIn("?api_key=", content)
        self.assertTrue(json.loads(content)["fragment_truncated"])
        partial = recorder.redact('<tool_call>{"api_key":"partial')
        self.assertNotIn("partial", partial)
        self.assertNotIn("mytoken", recorder.redact("Authorization: Bearer mytoken"))
        self.assertNotIn("a" * 64, recorder.redact("a" * 64))
        text = "Authorization: " + "q" * 300
        self.assertNotIn("q" * 30, recorder.fragment(text)["fragment"])

    def test_limit_is_explicit_append_only_and_preserves_execution(self):
        path = Path(self.tmp.name) / "limited.jsonl"
        recorder = GenerationDiagnostics(path, max_bytes=2048)
        self.addCleanup(recorder.close)
        for _ in range(15):
            recorder.record("sample", text="a " * 300)
        prefix = path.read_bytes()
        self.assertLessEqual(len(prefix), 2048)
        self.assertEqual(json.loads(prefix.splitlines()[-1])["stage"], "diagnostic_limit")
        recorder.record("ignored")
        self.assertEqual(prefix, path.read_bytes())
        self.recorder.record("first")
        original = self.path.read_bytes()
        self.recorder.close()
        reopened = GenerationDiagnostics(self.path)
        self.addCleanup(reopened.close)
        reopened.record("second")
        self.assertTrue(self.path.read_bytes().startswith(original))

    def test_diagnostic_io_failure_does_not_change_parser_return(self):
        result = object()
        self.recorder.close()

        def parser(instance, model_output, request):
            return result

        self.assertIs(self.recorder.parser_wrapper(parser, streaming=False)(object(), "text", object()), result)

    def test_chunk_limit_and_per_generation_isolation(self):
        class Context:
            _accumulated_text = ""

        self.recorder.max_chunks = 1

        def append(context, output):
            context._accumulated_text += output.outputs[0].text

        wrapped = self.recorder.generation_wrapper(append, streaming=True)
        for identifier in ("resp-one_0", "resp-two_0"):
            context = Context()
            for final in (False, True):
                wrapped(context, SimpleNamespace(request_id=identifier, finished=final, outputs=[
                    SimpleNamespace(text="x", token_ids=[], finish_reason="length" if final else None, stop_reason=None)]))
        rows = self.rows()
        finals = [row for row in rows if row["stage"] == "generation_finished"]
        self.assertEqual(len(finals), 2)
        self.assertTrue(all(row["chunk_count"] == 2 and row["chunk_metadata_truncated"] for row in finals))

    @unittest.skipUnless(os.environ.get("UAEA_TEST_REAL_HERMES") == "1", "Optional installed-vLLM CPU parser test")
    def test_installed_hermes_full_and_streaming_observer_equivalence(self):
        from vllm.tool_parsers.hermes_tool_parser import Hermes2ProToolParser, logger

        handler = self.recorder.error_handler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        request = SimpleNamespace(request_id="resp-installed-test")
        valid = '<tool_call>{"name":"web_search","arguments":{"query":"AI","provider":"google","allow_fallback":false}}</tool_call>'

        def normalized(result):
            data = result.model_dump() if result else None
            for tool in (data or {}).get("tool_calls") or []:
                tool.pop("id", None)
            return data

        for text in ("ordinary response", "promise<tool_call>\n", valid):
            plain, observed = Hermes2ProToolParser(object()), Hermes2ProToolParser(object())
            expected = plain.extract_tool_calls(text, request)
            actual = self.recorder.parser_wrapper(Hermes2ProToolParser.extract_tool_calls, streaming=False)(observed, text, request)
            self.assertEqual(normalized(actual), normalized(expected))
        error = next(row for row in self.rows() if row["stage"] == "hermes_error")
        self.assertEqual(error["json_error_position"], 1)
        plain, observed = Hermes2ProToolParser(object()), Hermes2ProToolParser(object())
        previous = ""
        for delta in ("<tool_", 'call>{"name":"web_', 'search","arguments":', '{"query":"AI"}}', "</tool_call>"):
            current = previous + delta
            args = (previous, current, delta, [], [], [], request)
            expected = plain.extract_tool_calls_streaming(*args)
            actual = self.recorder.parser_wrapper(Hermes2ProToolParser.extract_tool_calls_streaming, streaming=True)(observed, *args)
            self.assertEqual(normalized(actual), normalized(expected))
            previous = current

    @unittest.skipUnless(os.environ.get("UAEA_TEST_REAL_HERMES") == "1", "Optional installed-vLLM CPU generation test")
    def test_installed_response_context_records_raw_before_parser(self):
        from vllm.entrypoints.openai.responses.context import SimpleContext
        from vllm.outputs import CompletionOutput, RequestOutput
        from vllm.tool_parsers.hermes_tool_parser import Hermes2ProToolParser, logger

        context = SimpleContext()
        append = self.recorder.generation_wrapper(SimpleContext.append_output, streaming=True)
        for text, final in (("promise<tool_", False), ("call>\n", True)):
            completion = CompletionOutput(index=0, text=text, token_ids=[1], cumulative_logprob=None,
                                          logprobs=None, finish_reason="stop" if final else None, stop_reason=151645 if final else None)
            output = RequestOutput(request_id="resp-cpu_0", prompt="PROMPT_MUST_NOT_BE_LOGGED",
                                   prompt_token_ids=[1], prompt_logprobs=None, outputs=[completion], finished=final)
            append(context, output)
        self.assertEqual(context.final_output.outputs[0].text, "promise<tool_call>\n")
        handler = self.recorder.error_handler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        parser = Hermes2ProToolParser(object())
        result = self.recorder.parser_wrapper(Hermes2ProToolParser.extract_tool_calls, streaming=False)(
            parser, context.final_output.outputs[0].text, SimpleNamespace(request_id="resp-cpu"))
        self.assertFalse(result.tools_called)
        rows = self.rows()
        finished = next(row for row in rows if row["stage"] == "generation_finished")
        parser_input = next(row for row in rows if row["stage"] == "hermes_input")
        self.assertEqual(finished["fragment"], parser_input["fragment"])
        self.assertEqual(finished["stop_reason"], 151645)
        self.assertEqual(finished["engine_request_id"], parser_input["response_id"] + "_0")
        self.assertTrue(rows[-1]["parser_error_observed"])
        self.assertNotIn("PROMPT_MUST_NOT_BE_LOGGED", self.path.read_text())


if __name__ == "__main__":
    unittest.main()
