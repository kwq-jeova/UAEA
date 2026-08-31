from __future__ import annotations

import unittest

from phase2.web_intent import parse_semantic_web_intent, should_consider_semantic_web_intent


class WebIntentTests(unittest.TestCase):
    def test_prefilter_accepts_external_current_technical_request(self):
        self.assertTrue(should_consider_semantic_web_intent("当前 vLLM 对 Qwen2.5 AWQ 兼容性怎么样"))
        self.assertTrue(should_consider_semantic_web_intent("latest vLLM AWQ compatibility"))

    def test_prefilter_rejects_ordinary_project_discussion(self):
        self.assertFalse(should_consider_semantic_web_intent("继续推进当前模块实现"))
        self.assertFalse(should_consider_semantic_web_intent("解释一下这个架构边界"))

    def test_semantic_parser_accepts_search_json(self):
        model = FakeChatModel('{"kind":"search","value":"vLLM Qwen2.5 AWQ compatibility","confidence":"high","reason":"current external info"}')

        intent = parse_semantic_web_intent(model, "当前 vLLM 对 Qwen2.5 AWQ 兼容性怎么样")

        self.assertEqual(intent.to_command(), {"kind": "search", "value": "vLLM Qwen2.5 AWQ compatibility"})
        self.assertEqual(model.calls[0]["max_tokens"], 160)

    def test_semantic_parser_rejects_low_confidence_web_action(self):
        model = FakeChatModel('{"kind":"search","value":"vLLM","confidence":"low","reason":"unclear"}')

        intent = parse_semantic_web_intent(model, "现在继续")

        self.assertIsNone(intent.to_command())
        self.assertEqual(intent.kind, "none")

    def test_semantic_parser_extracts_json_object_from_wrapped_response(self):
        model = FakeChatModel('Result:\n{"kind":"none","value":"","confidence":"medium","reason":"local task"}')

        intent = parse_semantic_web_intent(model, "解释本地代码")

        self.assertIsNone(intent.to_command())
        self.assertEqual(intent.confidence, "medium")


class FakeChatModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict] = []

    def chat(self, messages: list[dict], max_tokens: int = 256, temperature: float = 0.1) -> str:
        self.calls.append({"messages": messages, "max_tokens": max_tokens, "temperature": temperature})
        return self.response


if __name__ == "__main__":
    unittest.main()
