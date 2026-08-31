from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol


class ChatModel(Protocol):
    def chat(self, messages: list[dict], max_tokens: int = 256, temperature: float = 0.1) -> str:
        ...


@dataclass(frozen=True)
class SemanticWebIntentResult:
    kind: str
    value: str
    confidence: str
    reason: str = ""

    def to_command(self) -> dict[str, str] | None:
        if self.kind not in {"fetch", "search"}:
            return None
        if not self.value.strip():
            return None
        return {"kind": self.kind, "value": self.value.strip()}


SEMANTIC_WEB_INTENT_SYSTEM_PROMPT = """You classify whether a user request needs Phase-2 web access.

Return exactly one compact JSON object and no prose.

Allowed JSON:
{"kind":"none","value":"","confidence":"low|medium|high","reason":"short"}
{"kind":"fetch","value":"https://example.com","confidence":"low|medium|high","reason":"short"}
{"kind":"search","value":"search query","confidence":"low|medium|high","reason":"short"}

Rules:
- Use fetch only when the user provided a concrete URL and asks to access/read/open/summarize it.
- Use search when the user asks for current, latest, online, official, release, compatibility, version, support, documentation, or externally verifiable information but did not provide a URL.
- If the current request uses anaphora or underspecified phrases like "related projects", "this", "it", or "above", use the recent dialogue context only to rewrite a concrete search query.
- Use none for ordinary conversation, local project work, architecture discussion, writing, editing, or questions answerable without external evidence.
- Do not answer the user. Do not browse. Do not invent URLs.
"""


_EXTERNAL_INFO_HINTS = (
    "当前",
    "现在",
    "最新",
    "官网",
    "官方",
    "文档",
    "联网",
    "网上",
    "网络",
    "搜索",
    "查一下",
    "查找",
    "查询",
    "查证",
    "验证",
    "release",
    "releases",
    "version",
    "latest",
    "current",
    "official",
    "docs",
    "documentation",
    "compatibility",
    "compatible",
    "support",
    "supported",
    "web",
    "online",
)
_TECHNICAL_TARGET_HINTS = (
    "vllm",
    "qwen",
    "awq",
    "compressed-tensors",
    "wna16",
    "cuda",
    "transformers",
    "pytorch",
    "github",
    "模型",
    "backend",
    "后端",
    "兼容",
    "版本",
)


def should_consider_semantic_web_intent(user_input: str) -> bool:
    text = " ".join(str(user_input or "").split())
    if not text:
        return False
    lowered = text.lower()
    if "://" in lowered or "www." in lowered:
        return True
    if not any(hint in lowered for hint in _EXTERNAL_INFO_HINTS):
        return False
    strong_external_signal = any(
        hint in lowered
        for hint in (
            "最新",
            "官网",
            "官方",
            "联网",
            "网上",
            "网络",
            "搜索",
            "查证",
            "release",
            "latest",
            "current",
            "official",
            "docs",
            "documentation",
            "compatibility",
            "web",
            "online",
        )
    )
    return strong_external_signal or any(hint in lowered for hint in _TECHNICAL_TARGET_HINTS)


def parse_semantic_web_intent(
    model: ChatModel,
    user_input: str,
    *,
    recent_context: tuple[str, ...] | list[str] | None = None,
) -> SemanticWebIntentResult:
    clean_user_input = _safe_prompt_text(user_input)
    messages = [{"role": "system", "content": SEMANTIC_WEB_INTENT_SYSTEM_PROMPT}]
    context_lines = [_safe_prompt_text(item) for item in (recent_context or ()) if _safe_prompt_text(item)]
    if context_lines:
        messages.append(
            {
                "role": "user",
                "content": "Recent dialogue context for query clarification only:\n"
                + "\n".join(f"- {line}" for line in context_lines[-5:]),
            }
        )
    messages.append({"role": "user", "content": clean_user_input})
    response = model.chat(
        messages,
        max_tokens=160,
        temperature=0.1,
    )
    payload = _json_object_from_text(response)
    kind = str(payload.get("kind") or "none").strip().lower()
    if kind not in {"none", "fetch", "search"}:
        kind = "none"
    confidence = str(payload.get("confidence") or "low").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
    value = _clean_value(str(payload.get("value") or ""))
    if kind in {"fetch", "search"} and confidence == "low":
        kind = "none"
        value = ""
    if kind in {"fetch", "search"} and not value:
        kind = "none"
    return SemanticWebIntentResult(
        kind=kind,
        value=value,
        confidence=confidence,
        reason=str(payload.get("reason") or "").strip()[:160],
    )


def _json_object_from_text(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match is None:
            return {"kind": "none", "value": "", "confidence": "low", "reason": "no json object"}
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"kind": "none", "value": "", "confidence": "low", "reason": "invalid json object"}
    if not isinstance(value, dict):
        return {"kind": "none", "value": "", "confidence": "low", "reason": "json was not object"}
    return value


def _clean_value(value: str) -> str:
    return " ".join(_remove_unicode_surrogates(str(value or "")).strip(" \t\r\n`\"'").split())


def _safe_prompt_text(value: object) -> str:
    return " ".join(_remove_unicode_surrogates(str(value or "")).split())


def _remove_unicode_surrogates(value: str) -> str:
    return "".join(" " if 0xD800 <= ord(char) <= 0xDFFF else char for char in value)
