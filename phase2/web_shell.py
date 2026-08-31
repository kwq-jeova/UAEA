from __future__ import annotations

import sqlite3
import re
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from memory.sqlite_store import connect, initialize
from phase2.web_adapter import WebAccessResult, WebAdapter
from phase2.web_context import ProjectionLimits, project_web_access_events
from phase2.web_intent import ChatModel, parse_semantic_web_intent, should_consider_semantic_web_intent


@dataclass(frozen=True)
class WebShellResult:
    response: str
    used_web: bool = False
    access_event_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_block: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    intent_source: str = ""


class RuntimeAgent(Protocol):
    def handle(self, user_input: str) -> str:
        ...


class Phase2WebShell:
    def __init__(
        self,
        agent: RuntimeAgent,
        *,
        db_path: Path | str,
        snapshot_root: Path | str,
        adapter: WebAdapter | None = None,
        projection_limits: ProjectionLimits | None = None,
        intent_model: ChatModel | None = None,
        enable_semantic_intent: bool = True,
        context_turn_limit: int = 5,
    ) -> None:
        self.agent = agent
        self.db_path = Path(db_path)
        self.snapshot_root = Path(snapshot_root)
        self.adapter = adapter or WebAdapter(snapshot_root=self.snapshot_root)
        self.projection_limits = projection_limits or ProjectionLimits()
        self.intent_model = intent_model
        self.enable_semantic_intent = enable_semantic_intent
        self.context_turn_limit = max(0, int(context_turn_limit))
        self._recent_user_inputs: list[str] = []
        self._last_search_query = ""

    def handle(self, user_input: str) -> WebShellResult:
        try:
            command, intent_source = self._resolve_web_request(user_input)
            if command is None:
                return WebShellResult(response=self.agent.handle(user_input))
            if command["kind"] == "capability":
                return WebShellResult(response=_web_capability_response(), intent_source=intent_source)
            try:
                with closing(connect(self.db_path)) as connection:
                    initialize(connection)
                    access_result = self._execute_web_command(connection, command)
                    projection = project_web_access_events(
                        connection,
                        [access_result.access_event_id],
                        limits=self.projection_limits,
                    )
                visible_event_ids = access_result.related_access_event_ids or (access_result.access_event_id,)
                runtime_input = self._runtime_input(user_input, projection.evidence_block())
                response = self.agent.handle(runtime_input)
                return WebShellResult(
                    response=response,
                    used_web=True,
                    access_event_ids=visible_event_ids,
                    evidence_block=projection.evidence_block(),
                    metrics=projection.metrics(),
                    error=access_result.error,
                    intent_source=intent_source,
                )
            except Exception as exc:
                return WebShellResult(
                    response=f"Web capability failed before Runtime handoff: {exc}",
                    used_web=True,
                    error=str(exc),
                    intent_source=intent_source,
                )
        finally:
            self._remember_user_input(user_input)

    def _execute_web_command(self, connection: sqlite3.Connection, command: dict[str, str]) -> WebAccessResult:
        if command["kind"] == "fetch":
            return self.adapter.fetch_url(connection, command["value"])
        if command["kind"] == "search":
            result = self.adapter.search(connection, command["value"])
            self._last_search_query = command["value"]
            return result
        raise ValueError(f"unsupported web command: {command['kind']}")

    def _resolve_web_request(self, user_input: str) -> tuple[dict[str, str] | None, str]:
        explicit_command = parse_web_command(user_input)
        if explicit_command is not None:
            return explicit_command, "explicit"
        refinement_command = self._search_refinement_command(user_input)
        if refinement_command is not None:
            return refinement_command, "deterministic:refinement"
        command = parse_web_request(user_input)
        if command is not None:
            if command["kind"] == "search" and _search_query_needs_context(command["value"]):
                semantic_command, semantic_source = self._semantic_web_command(user_input)
                if semantic_command is not None:
                    return semantic_command, semantic_source
                contextual_command = self._contextual_search_command(command["value"])
                if contextual_command is not None:
                    return contextual_command, "deterministic:context"
            return command, "deterministic"
        semantic_command, semantic_source = self._semantic_web_command(user_input)
        if semantic_command is not None:
            return semantic_command, semantic_source
        if semantic_source:
            return None, semantic_source
        return None, ""

    def _search_refinement_command(self, user_input: str) -> dict[str, str] | None:
        if not _is_search_refinement_request(user_input):
            return None
        query = _refine_search_query(
            self._last_search_query,
            user_input,
            recent_context=tuple(self._recent_user_inputs),
        )
        if not query:
            return None
        return {"kind": "search", "value": query}

    def _semantic_web_command(self, user_input: str) -> tuple[dict[str, str] | None, str]:
        if not self.enable_semantic_intent or self.intent_model is None:
            return None, ""
        if not should_consider_semantic_web_intent(user_input):
            return None, ""
        try:
            intent = parse_semantic_web_intent(
                self.intent_model,
                user_input,
                recent_context=tuple(self._recent_user_inputs),
            )
        except Exception:
            return None, "semantic:error"
        command = intent.to_command()
        if command is None:
            return None, f"semantic:{intent.kind}:{intent.confidence}"
        return command, f"semantic:{intent.kind}:{intent.confidence}"

    def _remember_user_input(self, user_input: str) -> None:
        clean = _safe_single_line_text(user_input)
        if not clean or self.context_turn_limit <= 0:
            return
        self._recent_user_inputs.append(clean[:500])
        if len(self._recent_user_inputs) > self.context_turn_limit:
            self._recent_user_inputs = self._recent_user_inputs[-self.context_turn_limit :]

    def _contextual_search_command(self, query: str) -> dict[str, str] | None:
        anchor = _recent_context_search_anchor(tuple(self._recent_user_inputs))
        if not anchor:
            return None
        return {"kind": "search", "value": f"{anchor} {_search_query_descriptor(query)}".strip()}

    def _runtime_input(self, original_user_input: str, evidence_block: str) -> str:
        return "\n\n".join(
            [
                "Use the bounded external web evidence below to answer the user's request.",
                "Do not treat the evidence as Memory or absolute truth. Preserve visible source uncertainty.",
                evidence_block,
                f"User request:\n{original_user_input}",
            ]
        )


_URL_PATTERN = re.compile(r"(https?://[^\s<>()\[\]{}]+|www\.[^\s<>()\[\]{}]+)", re.IGNORECASE)
_TRAILING_URL_PUNCTUATION = ".,;:!?，。；：！？、）)]}\"'"
_FETCH_KEYWORDS = (
    "访问",
    "打开",
    "读取",
    "抓取",
    "查看",
    "看看",
    "分析这个链接",
    "fetch",
    "open",
    "read this url",
)
_SEARCH_KEYWORDS = (
    "联网搜索",
    "网上搜索",
    "网络搜索",
    "搜索",
    "检索",
    "查一下",
    "查询",
    "查找",
    "找一下",
    "帮我查",
    "web search",
    "search",
    "look up",
    "find online",
)
_UNDERSPECIFIED_SEARCH_MARKERS = (
    "相关项目",
    "相关内容",
    "相关资料",
    "相关信息",
    "这个项目",
    "这个问题",
    "这方面",
    "上面",
    "前面",
    "刚才",
    "它",
    "this",
    "it",
    "that",
    "related project",
    "related projects",
    "related content",
)
_SEARCH_REFINEMENT_MARKERS = (
    "去除",
    "不要",
    "不在要求",
    "不再要求",
    "无需",
    "不用",
    "其次",
    "换成",
    "改成",
    "最好是",
    "优先",
    "英文",
    "海外",
    "国外",
    "论坛",
    "without",
    "remove",
    "prefer",
    "english",
    "overseas",
    "foreign",
    "forum",
)
_CAPABILITY_MARKERS = (
    "你可以访问互联网吗",
    "你可以连接互联网吗",
    "你能访问互联网吗",
    "你能连接互联网吗",
    "你能联网吗",
    "你可以搜索吗",
    "你能搜索吗",
    "你会搜索吗",
    "可以联网吗",
    "能联网吗",
    "可以搜索吗",
    "能搜索吗",
    "can you access the internet",
    "can you browse",
    "can you search",
    "internet access",
    "web access",
)


def parse_web_request(user_input: str) -> dict[str, str] | None:
    command = parse_web_command(user_input)
    if command is not None:
        return command
    text = str(user_input or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if any(marker in lowered for marker in _CAPABILITY_MARKERS):
        return {"kind": "capability", "value": ""}
    url = _first_url(text)
    if url and (_has_keyword(lowered, _FETCH_KEYWORDS) or text.startswith(url)):
        return {"kind": "fetch", "value": url}
    search_query = _search_query_from_text(text)
    if search_query:
        return {"kind": "search", "value": search_query}
    search_refinement = _search_refinement_query_from_text(text)
    if search_refinement:
        return {"kind": "search", "value": search_refinement}
    return None


def parse_web_command(user_input: str) -> dict[str, str] | None:
    text = str(user_input or "").strip()
    if not text.startswith("/web "):
        return None
    rest = text[len("/web ") :].strip()
    if rest.startswith("fetch "):
        value = rest[len("fetch ") :].strip()
        if not value:
            raise ValueError("/web fetch requires a URL")
        return {"kind": "fetch", "value": value}
    if rest.startswith("search "):
        value = rest[len("search ") :].strip()
        if not value:
            raise ValueError("/web search requires a query")
        return {"kind": "search", "value": value}
    raise ValueError("supported web commands: /web fetch <url>, /web search <query>")


def _first_url(text: str) -> str:
    match = _URL_PATTERN.search(text)
    if match is None:
        return ""
    return match.group(1).rstrip(_TRAILING_URL_PUNCTUATION)


def _has_keyword(lowered_text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in lowered_text for keyword in keywords)


def _search_query_from_text(text: str) -> str:
    lowered = text.lower()
    matches = [
        (lowered.find(keyword), keyword)
        for keyword in _SEARCH_KEYWORDS
        if lowered.find(keyword) >= 0 and not _is_reported_search_reference(lowered, lowered.find(keyword), keyword)
    ]
    if not matches:
        return ""
    _, keyword = min(matches, key=lambda item: item[0])
    start = lowered.find(keyword) + len(keyword)
    query = text[start:].strip(" ：:，,。.!！?？\t\r\n")
    query = _strip_polite_search_suffixes(query)
    return " ".join(query.split())


def _is_reported_search_reference(lowered_text: str, index: int, keyword: str) -> bool:
    prefix = lowered_text[max(0, index - 8) : index]
    suffix = lowered_text[index + len(keyword) : index + len(keyword) + 4]
    if suffix.startswith("的") and any(marker in prefix for marker in ("你", "刚才", "之前", "上次")):
        return True
    if any(marker in lowered_text for marker in ("你搜索的", "你搜的", "刚才搜索的", "之前搜索的", "搜索的都是")):
        return True
    return False


def _search_refinement_query_from_text(text: str) -> str:
    clean = _safe_single_line_text(text)
    if not clean:
        return ""
    lowered = clean.lower()
    refinement_markers = ("最好是", "优先", "换成", "改成", "不要", "不是", "more", "prefer", "instead")
    source_markers = ("海外论坛", "国外论坛", "英文论坛", "reddit", "stackoverflow", "github discussion", "forum")
    if not any(marker in lowered for marker in refinement_markers):
        return ""
    if not any(marker in lowered for marker in source_markers):
        return ""
    head = re.split(r"[，,。.!！?？;；]", clean, maxsplit=1)[0]
    if "海外论坛" in head or "国外论坛" in head:
        return "海外论坛"
    if "英文论坛" in head:
        return "英文论坛"
    if "reddit" in lowered:
        return "reddit discussions"
    if "stackoverflow" in lowered:
        return "stackoverflow discussions"
    if "github discussion" in lowered:
        return "github discussions"
    if "forum" in lowered:
        return "forums"
    return head


def _is_search_refinement_request(text: str) -> bool:
    clean = _safe_single_line_text(text)
    if not clean:
        return False
    lowered = clean.lower()
    if not any(marker in lowered for marker in _SEARCH_REFINEMENT_MARKERS):
        return False
    return any(
        marker in lowered
        for marker in (
            "你搜索",
            "搜索的时候",
            "搜索时",
            "我的要求",
            "关键词",
            "论文支撑",
            "英文",
            "海外",
            "国外",
            "论坛",
            "search query",
            "when searching",
        )
    )


def _refine_search_query(base_query: str, user_input: str, *, recent_context: tuple[str, ...]) -> str:
    base = _safe_single_line_text(base_query)
    request = _safe_single_line_text(user_input)
    lowered = request.lower()
    if not base:
        anchor = _recent_context_search_anchor(recent_context)
        base = f"{anchor} related projects".strip()
    if not base:
        return ""

    refined = _english_search_query(base) if _requests_english_query(request) else base
    refined = _remove_query_constraints(refined, request)
    additions: list[str] = []
    if any(marker in lowered for marker in ("海外", "国外", "overseas", "foreign")):
        additions.extend(["overseas", "English"])
    if "英文" in lowered or "english" in lowered:
        additions.append("English")
    if "论坛" in lowered or "forum" in lowered:
        additions.extend(["forums", "Reddit", "discussions"])
    if "项目" in request or "project" in lowered:
        additions.append("projects")
    refined = _append_unique_terms(refined, additions)
    return _strip_search_operation_words(refined)


def _requests_english_query(text: str) -> bool:
    lowered = text.lower()
    return "英文" in lowered or "换成英文" in lowered or "english" in lowered


def _english_search_query(query: str) -> str:
    replacements = (
        ("有论文支撑的", "paper-backed"),
        ("后训练", "post-training"),
        ("相关的项目", "related projects"),
        ("相关项目", "related projects"),
        ("项目", "projects"),
        ("相关度最好是高的", "high relevance"),
        ("相关度高", "high relevance"),
        ("论文支撑", "paper-backed"),
        ("海外论坛", "overseas forums"),
        ("国外论坛", "overseas forums"),
        ("英文论坛", "English forums"),
        ("论坛", "forums"),
    )
    clean = query
    for source, target in replacements:
        clean = clean.replace(source, f" {target} ")
    clean = clean.replace("，", " ").replace(",", " ")
    return " ".join(clean.split())


def _remove_query_constraints(query: str, request: str) -> str:
    lowered = request.lower()
    clean = query
    if any(marker in lowered for marker in ("去除", "不要", "不在要求", "不再要求", "无需", "不用", "without", "remove")):
        removable = (
            "paper-backed",
            "paper backed",
            "paper support",
            "research paper support",
            "有论文支撑的",
            "论文支撑",
        )
        for item in removable:
            clean = re.sub(rf"\b{re.escape(item)}\b", " ", clean, flags=re.IGNORECASE)
            clean = clean.replace(item, " ")
    return " ".join(clean.split())


def _append_unique_terms(query: str, terms: list[str]) -> str:
    clean = query
    existing = {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9._+-]*", clean)}
    for term in terms:
        if not term:
            continue
        key = term.lower()
        if key not in existing:
            clean = f"{clean} {term}".strip()
            existing.add(key)
    return " ".join(clean.split())


def _strip_search_operation_words(query: str) -> str:
    clean = re.sub(r"^\s*(search|find|look up)\s+", "", query, flags=re.IGNORECASE)
    return " ".join(clean.split())


def _strip_polite_search_suffixes(query: str) -> str:
    suffixes = (
        "吗",
        "么",
        "并回答我",
        "然后回答我",
        "并告诉我",
        "然后告诉我",
        "谢谢",
        "please",
    )
    clean = query.strip()
    lowered = clean.lower()
    for suffix in suffixes:
        if lowered.endswith(suffix):
            clean = clean[: -len(suffix)].strip(" ，,。.!！?？")
            lowered = clean.lower()
    return clean


def _search_query_needs_context(query: str) -> bool:
    clean = _safe_single_line_text(query)
    if not clean:
        return False
    lowered = clean.lower()
    if any(marker in lowered for marker in _UNDERSPECIFIED_SEARCH_MARKERS):
        return True
    return len(clean) <= 8 and not re.search(r"[A-Za-z0-9]", clean)


def _recent_context_search_anchor(recent_user_inputs: tuple[str, ...]) -> str:
    stopwords = {"this", "that", "with", "from", "about", "related", "project", "projects"}
    tokens: list[str] = []
    for text in recent_user_inputs[-5:]:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9._+-]{1,}", text):
            lowered = token.lower()
            if lowered not in stopwords and lowered not in [item.lower() for item in tokens]:
                tokens.append(token)
    return " ".join(tokens[-4:])


def _search_query_descriptor(query: str) -> str:
    clean = _safe_single_line_text(query)
    lowered = clean.lower()
    if "海外论坛" in clean or "国外论坛" in clean or "英文论坛" in clean:
        return "overseas forums reddit discussions"
    if "论坛" in clean or "forum" in lowered:
        return "forum discussions"
    if "项目" in clean or "project" in lowered:
        return "related open source projects"
    if "论文" in clean or "paper" in lowered:
        return "related papers"
    if "文档" in clean or "docs" in lowered or "documentation" in lowered:
        return "documentation"
    return clean


def _safe_single_line_text(value: object) -> str:
    return " ".join(_remove_unicode_surrogates(str(value or "")).split())


def _remove_unicode_surrogates(value: str) -> str:
    return "".join(" " if 0xD800 <= ord(char) <= 0xDFFF else char for char in value)


def _web_capability_response() -> str:
    return (
        "当前 Phase-2 Web Shell 可以通过显式 Web 请求访问外部来源，并把访问事件写入 SQLite Source History。"
        "可用方式包括：`/web fetch <url>`、`/web search <query>`，也支持明确的自然语言请求，例如"
        "`请访问 https://docs.vllm.ai/ 并总结` 或 `请联网搜索 vLLM Qwen2.5 AWQ compatibility`。"
        "这不是 Memory，也不会自动生成 Candidate/Policy/Memory。"
    )
