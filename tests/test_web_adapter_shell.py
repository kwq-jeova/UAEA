from __future__ import annotations

import http.server
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from memory.sqlite_store import connect, counts, get_web_access_event, initialize
from phase2.web_adapter import WebAdapter
from phase2.web_capability import WebFetchCapability, WebSearchCapability, web_fetch_metadata, web_search_metadata
from phase2.web_context import ProjectionLimits, project_web_access_events
from phase2.web_shell import Phase2WebShell, parse_web_command, parse_web_request
from runtime.ledger import LedgerStub
from runtime.sandbox import Sandbox
from runtime.semantic_observation import ExecutionObservation
from runtime.tools import ToolRegistry


class WebAdapterAndShellTests(unittest.TestCase):
    def test_web_fetch_capability_uses_registry_and_returns_bounded_observation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = root / "source.sqlite"
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            adapter = WebAdapter(snapshot_root=root / "snapshots", timeout_seconds=5)
            registry.register_capability(
                web_fetch_metadata(),
                WebFetchCapability(
                    db_path=db_path,
                    adapter=adapter,
                    projection_limits=ProjectionLimits(max_sources=1, per_source_chars=120, total_chars=120),
                ),
            )
            with local_web_server() as server:
                result = registry.execute_capability(
                    "web.fetch",
                    {"url": f"{server}/article.html"},
                    "fetch local article",
                )
            observation = ExecutionObservation.from_tool_result("web_fetch", result)
            with closing(connect(db_path)) as connection:
                event = get_web_access_event(connection, result.data["access_event_id"])

        assert event is not None
        self.assertTrue(result.ok)
        self.assertEqual(result.data["capability"], "web.fetch")
        self.assertEqual(result.data["tool"], "web_fetch")
        self.assertEqual(result.data["access_status"], "fetched")
        self.assertEqual(result.data["evidence_reference"]["source_kind"], "web_access_event")
        self.assertEqual(result.data["evidence_reference"]["source_id"], result.data["access_event_id"])
        self.assertIn("[WEB EVIDENCE BLOCK]", result.data["bounded_evidence_block"])
        self.assertIn("Main Web Article", result.data["bounded_evidence_block"])
        self.assertNotIn("<html>", result.data["bounded_evidence_block"])
        self.assertNotIn("content", result.data)
        self.assertLessEqual(result.data["projection_metrics"]["projected_chars"], 120)
        self.assertEqual(event["access_status"], "fetched")
        self.assertTrue(event["content_ref"])
        self.assertTrue(event["content_sha256"])
        self.assertEqual(observation.capability, "web.fetch")
        self.assertEqual(observation.tool_name, "web_fetch")
        self.assertEqual(observation.status, "success")

    def test_web_search_capability_uses_registry_and_returns_bounded_observation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = root / "source.sqlite"
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            with local_web_server() as server:
                registry.register_capability(
                    web_search_metadata(),
                    WebSearchCapability(
                        db_path=db_path,
                        adapter=WebAdapter(
                            snapshot_root=root / "snapshots2",
                            timeout_seconds=5,
                            search_url_template=f"{server}/search.html?q={{query}}",
                        ),
                        projection_limits=ProjectionLimits(max_sources=1, per_source_chars=120, total_chars=120),
                    ),
                )
                result = registry.execute_capability(
                    "web.search",
                    {"query": "vLLM Qwen2.5 AWQ"},
                    "search local article",
                )
            observation = ExecutionObservation.from_tool_result("web_search", result)
            with closing(connect(db_path)) as connection:
                event = get_web_access_event(connection, result.data["access_event_id"])

        assert event is not None
        self.assertTrue(result.ok)
        self.assertEqual(result.data["capability"], "web.search")
        self.assertEqual(result.data["tool"], "web_search")
        self.assertEqual(result.data["access_status"], "fetched")
        self.assertEqual(result.data["evidence_reference"]["source_kind"], "web_access_event")
        self.assertEqual(result.data["evidence_reference"]["source_id"], result.data["access_event_id"])
        self.assertIn("[WEB EVIDENCE BLOCK]", result.data["bounded_evidence_block"])
        self.assertIn("Qwen2.5 AWQ vLLM report", result.data["bounded_evidence_block"])
        self.assertEqual(result.data["search_query"], "vLLM Qwen2.5 AWQ")
        self.assertGreaterEqual(len(result.data["search_results"]), 1)
        self.assertLessEqual(result.data["projection_metrics"]["projected_chars"], 120)
        self.assertEqual(event["access_status"], "fetched")
        self.assertTrue(event["content_ref"])
        self.assertTrue(event["content_sha256"])
        self.assertEqual(observation.capability, "web.search")
        self.assertEqual(observation.tool_name, "web_search")
        self.assertEqual(observation.status, "success")

    def test_live_fetch_records_source_history_and_projects_bounded_context(self):
        with self.fixture_connection() as connection, tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                adapter = WebAdapter(snapshot_root=Path(tmpdir), timeout_seconds=5)
                result = adapter.fetch_url(connection, f"{server}/article.html")
                event = get_web_access_event(connection, result.access_event_id)
                assert event is not None
                snapshot_exists = Path(event["content_ref"]).is_file()
                projection = project_web_access_events(
                    connection,
                    [result.access_event_id],
                    limits=ProjectionLimits(max_sources=1, per_source_chars=180, total_chars=180),
                )

        self.assertEqual(result.status, "fetched")
        self.assertEqual(event["access_status"], "fetched")
        self.assertEqual(event["source_type"], "web_page")
        self.assertTrue(snapshot_exists)
        self.assertTrue(event["content_sha256"])
        self.assertIn("Main Web Article", projection.sources[0].projected_text)
        self.assertNotIn("<html>", projection.sources[0].projected_text)
        self.assertLessEqual(projection.total_projected_chars, 180)

    def test_failed_fetch_records_event_without_fake_content(self):
        with self.fixture_connection() as connection, tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                adapter = WebAdapter(snapshot_root=Path(tmpdir), timeout_seconds=5)
                result = adapter.fetch_url(connection, f"{server}/missing.html")
                event = get_web_access_event(connection, result.access_event_id)

        assert event is not None
        self.assertEqual(result.status, "failed")
        self.assertEqual(event["access_status"], "failed")
        self.assertEqual(event["http_status"], 404)
        self.assertEqual(event["content_ref"], "")
        self.assertEqual(event["content_chars"], 0)

    def test_search_records_search_results_as_external_source_event(self):
        with self.fixture_connection() as connection, tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir),
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                result = adapter.search(connection, "vLLM Qwen2.5 AWQ", max_results=2)
                event = get_web_access_event(connection, result.access_event_id)
                projection = project_web_access_events(connection, [result.access_event_id])

        assert event is not None
        self.assertEqual(result.status, "fetched")
        self.assertEqual(event["source_type"], "web_search_results")
        self.assertEqual(len(result.search_results), 2)
        self.assertIn("Search query: vLLM Qwen2.5 AWQ", projection.sources[0].projected_text)
        self.assertIn("Qwen2.5 AWQ vLLM report", projection.sources[0].projected_text)
        self.assertIn("https://example.test/qwen25", projection.sources[0].projected_text)

    def test_search_sanitizes_surrogate_input_before_url_encoding(self):
        with self.fixture_connection() as connection, tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir),
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                result = adapter.search(connection, "LoRA\udce5 related projects", max_results=1)
                event = get_web_access_event(connection, result.access_event_id)
                projection = project_web_access_events(connection, [result.access_event_id])

        assert event is not None
        self.assertEqual(result.status, "fetched")
        self.assertNotIn("\udce5", event["metadata"]["query"])
        self.assertIn("Search query: LoRA related projects", projection.sources[0].projected_text)

    def test_search_falls_back_when_first_provider_has_no_parsed_results(self):
        with self.fixture_connection() as connection, tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir),
                    timeout_seconds=5,
                    search_url_templates=(
                        f"{server}/empty-search.html?q={{query}}",
                        f"{server}/search.html?q={{query}}",
                    ),
                )
                result = adapter.search(connection, "vLLM Qwen2.5 AWQ", max_results=2)
                actual_counts = counts(connection)
                projection = project_web_access_events(connection, [result.access_event_id])

        self.assertEqual(result.status, "fetched")
        self.assertEqual(len(result.related_access_event_ids), 2)
        self.assertEqual(len(result.search_results), 2)
        self.assertEqual(actual_counts["web_access_events"], 2)
        self.assertIn("Qwen2.5 AWQ vLLM report", projection.sources[0].projected_text)

    def test_search_parser_supports_bing_result_shape(self):
        with self.fixture_connection() as connection, tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir),
                    timeout_seconds=5,
                    search_url_template=f"{server}/bing-search.html?q={{query}}",
                )
                result = adapter.search(connection, "vLLM Qwen2.5 AWQ", max_results=2)
                projection = project_web_access_events(connection, [result.access_event_id])

        self.assertEqual(result.status, "fetched")
        self.assertEqual(len(result.search_results), 2)
        self.assertEqual(result.search_results[0].url, "https://docs.vllm.ai/en/latest/features/quantization/auto_awq.html")
        self.assertIn("Bing style AWQ result", projection.sources[0].projected_text)

    def test_web_shell_fetch_hands_bounded_evidence_to_runtime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                root = Path(tmpdir)
                agent = FakeAgent()
                registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
                shell = Phase2WebShell(
                    agent,
                    db_path=root / "source.sqlite",
                    snapshot_root=root / "snapshots",
                    projection_limits=ProjectionLimits(max_sources=1, per_source_chars=220, total_chars=220),
                    capability_registry=registry,
                )
                result = shell.handle(f"/web fetch {server}/article.html")
                trace_events = [json.loads(line) for line in registry.ledger.path.read_text(encoding="utf-8").splitlines()]

        self.assertTrue(result.used_web)
        self.assertIn("web.fetch", registry.capability_names)
        self.assertEqual(len(result.access_event_ids), 1)
        self.assertEqual(agent.last_input, f"/web fetch {server}/article.html")
        self.assertIsNotNone(agent.last_execution_observation)
        assert agent.last_execution_observation is not None
        self.assertEqual(agent.last_execution_observation.capability, "web.fetch")
        self.assertIn("Main Web Article", result.evidence_block)
        self.assertEqual(result.response, "runtime response")
        tool_events = [event for event in trace_events if event["event_type"] == "tool_event"]
        observation_events = [event for event in trace_events if event["event_type"] == "execution_observation_event"]
        self.assertEqual(tool_events[-1]["metadata"]["tool_name"], "web_fetch")
        self.assertEqual(tool_events[-1]["metadata"]["output"]["capability"], "web.fetch")
        self.assertEqual(observation_events[-1]["metadata"]["capability"], "web.fetch")
        self.assertEqual(observation_events[-1]["metadata"]["tool_name"], "web_fetch")

    def test_web_shell_search_hands_search_results_to_runtime_without_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                agent = FakeAgent()
                root = Path(tmpdir)
                sandbox_root = root / "sandbox"
                sandbox_root.mkdir()
                registry = ToolRegistry(Sandbox(root, sandbox_root), LedgerStub(root / "traces"))
                adapter = WebAdapter(
                    snapshot_root=root / "snapshots",
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                shell = Phase2WebShell(
                    agent,
                    db_path=root / "source.sqlite",
                    snapshot_root=root / "snapshots",
                    adapter=adapter,
                    capability_registry=registry,
                )
                result = shell.handle("/web search vLLM Qwen2.5 AWQ")
                with closing(connect(root / "source.sqlite")) as connection:
                    actual_counts = counts(connection)
                trace_events = [json.loads(line) for line in registry.ledger.path.read_text(encoding="utf-8").splitlines()]

        self.assertTrue(result.used_web)
        self.assertIn("web.search", registry.capability_names)
        self.assertIn("web_search_results", result.evidence_block)
        self.assertEqual(agent.last_input, "/web search vLLM Qwen2.5 AWQ")
        self.assertIsNotNone(agent.last_execution_observation)
        assert agent.last_execution_observation is not None
        self.assertEqual(agent.last_execution_observation.capability, "web.search")
        self.assertIn("Qwen2.5 AWQ vLLM report", result.evidence_block)
        self.assertEqual(actual_counts["candidates"], 0)
        self.assertEqual(actual_counts["evidence_references"], 0)
        tool_events = [event for event in trace_events if event["event_type"] == "tool_event"]
        observation_events = [event for event in trace_events if event["event_type"] == "execution_observation_event"]
        self.assertEqual(tool_events[-1]["metadata"]["tool_name"], "web_search")
        self.assertEqual(tool_events[-1]["metadata"]["output"]["capability"], "web.search")
        self.assertEqual(observation_events[-1]["metadata"]["capability"], "web.search")
        self.assertEqual(observation_events[-1]["metadata"]["tool_name"], "web_search")

    def test_web_shell_natural_language_fetches_explicit_url_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                agent = FakeAgent()
                shell = Phase2WebShell(
                    agent,
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    projection_limits=ProjectionLimits(max_sources=1, per_source_chars=220, total_chars=220),
                )
                result = shell.handle(f"请访问 {server}/article.html 并告诉我这个页面的重点")

        self.assertTrue(result.used_web)
        self.assertEqual(len(result.access_event_ids), 1)
        self.assertEqual(agent.last_input, f"请访问 {server}/article.html 并告诉我这个页面的重点")
        self.assertIsNotNone(agent.last_execution_observation)
        assert agent.last_execution_observation is not None
        self.assertEqual(agent.last_execution_observation.capability, "web.fetch")
        self.assertIn("Main Web Article", result.evidence_block)

    def test_web_shell_natural_language_searches_explicit_search_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                agent = FakeAgent()
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir) / "snapshots",
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                shell = Phase2WebShell(
                    agent,
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    adapter=adapter,
                )
                result = shell.handle("请联网搜索 vLLM Qwen2.5 AWQ compatibility")

        self.assertTrue(result.used_web)
        self.assertEqual(agent.last_input, "请联网搜索 vLLM Qwen2.5 AWQ compatibility")
        self.assertIsNotNone(agent.last_execution_observation)
        assert agent.last_execution_observation is not None
        self.assertEqual(agent.last_execution_observation.capability, "web.search")
        self.assertIn("Qwen2.5 AWQ vLLM report", result.evidence_block)

    def test_web_shell_uses_semantic_intent_for_current_external_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                agent = FakeAgent()
                intent_model = FakeChatModel(
                    '{"kind":"search","value":"vLLM Qwen2.5 AWQ compatibility","confidence":"high","reason":"current compatibility"}'
                )
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir) / "snapshots",
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                shell = Phase2WebShell(
                    agent,
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    adapter=adapter,
                    intent_model=intent_model,
                )
                result = shell.handle("当前 vLLM 对 Qwen2.5 AWQ 的兼容性怎么样")

        self.assertTrue(result.used_web)
        self.assertEqual(result.intent_source, "semantic:search:high")
        self.assertEqual(len(intent_model.calls), 1)
        self.assertEqual(agent.last_input, "当前 vLLM 对 Qwen2.5 AWQ 的兼容性怎么样")
        self.assertIsNotNone(agent.last_execution_observation)
        assert agent.last_execution_observation is not None
        self.assertEqual(agent.last_execution_observation.capability, "web.search")

    def test_web_shell_uses_recent_context_to_expand_underspecified_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                agent = FakeAgent()
                intent_model = FakeChatModel(
                    '{"kind":"search","value":"LoRA training related open source projects","confidence":"high","reason":"related projects refers to LoRA"}'
                )
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir) / "snapshots",
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                shell = Phase2WebShell(
                    agent,
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    adapter=adapter,
                    intent_model=intent_model,
                )
                shell.handle("你知道后训练吗")
                shell.handle("这里我是指LoRA训练")
                shell.handle("有什么现有的项目相关吗")
                result = shell.handle("你可以联网查询一下相关项目，并总结")

        self.assertTrue(result.used_web)
        self.assertEqual(result.intent_source, "semantic:search:high")
        self.assertEqual(agent.last_input, "你可以联网查询一下相关项目，并总结")
        self.assertIsNotNone(agent.last_execution_observation)
        assert agent.last_execution_observation is not None
        self.assertEqual(agent.last_execution_observation.capability, "web.search")
        self.assertIn("LoRA训练", intent_model.calls[-1]["messages"][1]["content"])

    def test_web_shell_contextualizes_underspecified_search_when_semantic_intent_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                agent = FakeAgent()
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir) / "snapshots",
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                shell = Phase2WebShell(
                    agent,
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    adapter=adapter,
                    intent_model=FailingChatModel(),
                )
                shell.handle("这里我是指LoRA训练")
                result = shell.handle("你可以联网查询一下相关项目")

        self.assertTrue(result.used_web)
        self.assertEqual(result.intent_source, "deterministic:context")
        self.assertEqual(agent.last_input, "你可以联网查询一下相关项目")
        self.assertIsNotNone(agent.last_execution_observation)
        assert agent.last_execution_observation is not None
        self.assertEqual(agent.last_execution_observation.capability, "web.search")

    def test_web_shell_semantic_intent_failure_falls_back_to_runtime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = FakeAgent()
            shell = Phase2WebShell(
                agent,
                db_path=Path(tmpdir) / "source.sqlite",
                snapshot_root=Path(tmpdir) / "snapshots",
                intent_model=FailingChatModel(),
            )
            result = shell.handle("当前架构继续怎么推进")

        self.assertFalse(result.used_web)
        self.assertEqual(result.response, "runtime response")
        self.assertEqual(agent.last_input, "当前架构继续怎么推进")

    def test_web_shell_can_disable_semantic_intent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = FakeAgent()
            intent_model = FakeChatModel(
                '{"kind":"search","value":"vLLM Qwen2.5 AWQ compatibility","confidence":"high","reason":"current compatibility"}'
            )
            shell = Phase2WebShell(
                agent,
                db_path=Path(tmpdir) / "source.sqlite",
                snapshot_root=Path(tmpdir) / "snapshots",
                intent_model=intent_model,
                enable_semantic_intent=False,
            )
            result = shell.handle("当前 vLLM 对 Qwen2.5 AWQ 的兼容性怎么样")

        self.assertFalse(result.used_web)
        self.assertEqual(len(intent_model.calls), 0)
        self.assertEqual(agent.last_input, "当前 vLLM 对 Qwen2.5 AWQ 的兼容性怎么样")

    def test_web_capability_question_is_answered_by_phase2_shell(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = FakeAgent()
            shell = Phase2WebShell(
                agent,
                db_path=Path(tmpdir) / "source.sqlite",
                snapshot_root=Path(tmpdir) / "snapshots",
            )
            result = shell.handle("你可以访问互联网吗")

        self.assertFalse(result.used_web)
        self.assertIn("Phase-2 Web Shell", result.response)
        self.assertEqual(agent.last_input, "")

    def test_non_web_input_passes_through_without_source_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = FakeAgent()
            shell = Phase2WebShell(
                agent,
                db_path=Path(tmpdir) / "source.sqlite",
                snapshot_root=Path(tmpdir) / "snapshots",
            )
            result = shell.handle("ordinary question")

        self.assertFalse(result.used_web)
        self.assertEqual(agent.last_input, "ordinary question")

    def test_url_mention_without_access_intent_passes_through(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = FakeAgent()
            shell = Phase2WebShell(
                agent,
                db_path=Path(tmpdir) / "source.sqlite",
                snapshot_root=Path(tmpdir) / "snapshots",
            )
            result = shell.handle("我先记录一下这个链接 https://example.test/article")

        self.assertFalse(result.used_web)
        self.assertEqual(agent.last_input, "我先记录一下这个链接 https://example.test/article")

    def test_parse_web_command_keeps_routing_explicit(self):
        self.assertEqual(parse_web_command("/web fetch https://example.test"), {"kind": "fetch", "value": "https://example.test"})
        self.assertEqual(parse_web_command("/web search vllm awq"), {"kind": "search", "value": "vllm awq"})
        self.assertIsNone(parse_web_command("请帮我联网搜索 vllm awq"))

    def test_parse_web_request_supports_controlled_natural_language_web_intent(self):
        self.assertEqual(
            parse_web_request("请帮我联网搜索 vllm awq"),
            {"kind": "search", "value": "vllm awq"},
        )
        self.assertEqual(
            parse_web_request("那么请你联网查找一下Claude模型是否公布了runtime结构"),
            {"kind": "search", "value": "Claude模型是否公布了runtime结构"},
        )
        self.assertEqual(
            parse_web_request("请访问 https://example.test/article。"),
            {"kind": "fetch", "value": "https://example.test/article"},
        )
        self.assertEqual(
            parse_web_request("请访问 [https://docs.vllm.ai/](https://docs.vllm.ai/) 并总结这个页面"),
            {"kind": "fetch", "value": "https://docs.vllm.ai/"},
        )
        self.assertEqual(
            parse_web_request("你可以访问互联网吗"),
            {"kind": "capability", "value": ""},
        )
        self.assertEqual(
            parse_web_request("你可以搜索吗"),
            {"kind": "capability", "value": ""},
        )
        self.assertEqual(
            parse_web_request("最好是海外论坛的，你搜索的都是中国论坛的内容"),
            {"kind": "search", "value": "海外论坛"},
        )
        self.assertIsNone(parse_web_request("我先记录一下这个链接 https://example.test/article"))

    def test_reported_prior_search_phrase_does_not_become_search_query(self):
        self.assertNotEqual(
            parse_web_request("你搜索的都是中国论坛的内容"),
            {"kind": "search", "value": "的都是中国论坛的内容"},
        )

    def test_web_shell_contextualizes_overseas_forum_search_refinement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                agent = FakeAgent()
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir) / "snapshots",
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                shell = Phase2WebShell(
                    agent,
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    adapter=adapter,
                    intent_model=FailingChatModel(),
                )
                shell.handle("这里我是指LoRA训练")
                result = shell.handle("最好是海外论坛的，你搜索的都是中国论坛的内容")

        self.assertTrue(result.used_web)
        self.assertEqual(result.intent_source, "deterministic:refinement")
        self.assertEqual(agent.last_input, "最好是海外论坛的，你搜索的都是中国论坛的内容")
        self.assertIsNotNone(agent.last_execution_observation)
        assert agent.last_execution_observation is not None
        self.assertEqual(agent.last_execution_observation.capability, "web.search")

    def test_web_shell_refines_previous_search_by_removing_paper_requirement_and_using_english(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with local_web_server() as server:
                agent = FakeAgent()
                intent_model = FakeChatModel(
                    '{"kind":"search","value":"search","confidence":"medium","reason":"bad generic query"}'
                )
                adapter = WebAdapter(
                    snapshot_root=Path(tmpdir) / "snapshots",
                    timeout_seconds=5,
                    search_url_template=f"{server}/search.html?q={{query}}",
                )
                shell = Phase2WebShell(
                    agent,
                    db_path=Path(tmpdir) / "source.sqlite",
                    snapshot_root=Path(tmpdir) / "snapshots",
                    adapter=adapter,
                    intent_model=intent_model,
                )
                shell.handle("/web search LoRA后训练相关的项目，相关度最好是高的，有论文支撑的")
                result = shell.handle("那么去除一些关键词，不在要求一定是要论文支撑的，其次是你进行搜索的时候，可以把我的要求都换成英文")

        self.assertTrue(result.used_web)
        self.assertEqual(result.intent_source, "deterministic:refinement")
        self.assertEqual(
            agent.last_input,
            "那么去除一些关键词，不在要求一定是要论文支撑的，其次是你进行搜索的时候，可以把我的要求都换成英文",
        )
        self.assertIsNotNone(agent.last_execution_observation)
        assert agent.last_execution_observation is not None
        self.assertEqual(agent.last_execution_observation.capability, "web.search")
        self.assertEqual(len(intent_model.calls), 0)

    @contextmanager
    def fixture_connection(self) -> Iterator[sqlite3.Connection]:
        with tempfile.TemporaryDirectory() as tmpdir:
            with closing(connect(Path(tmpdir) / "memory.db")) as connection:
                initialize(connection)
                yield connection


class FakeAgent:
    def __init__(self) -> None:
        self.last_input = ""
        self.last_execution_observation: ExecutionObservation | None = None
        self.last_tool_result = None

    def handle(self, user_input: str) -> str:
        self.last_input = user_input
        self.last_execution_observation = None
        self.last_tool_result = None
        return "runtime response"

    def handle_execution_observation(
        self,
        user_input: str,
        execution_observation: ExecutionObservation,
        tool_result=None,
    ) -> str:
        self.last_input = user_input
        self.last_execution_observation = execution_observation
        self.last_tool_result = tool_result
        return "runtime response"


class FakeChatModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict] = []

    def chat(self, messages: list[dict], max_tokens: int = 256, temperature: float = 0.1) -> str:
        self.calls.append({"messages": messages, "max_tokens": max_tokens, "temperature": temperature})
        return self.response


class FailingChatModel:
    def chat(self, messages: list[dict], max_tokens: int = 256, temperature: float = 0.1) -> str:
        raise RuntimeError("intent model failed")


@contextmanager
def local_web_server() -> Iterator[str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _TestRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


class _TestRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/article.html"):
            self._send(
                200,
                b"""
                <!doctype html>
                <html>
                  <head><title>Local Article Fixture</title></head>
                  <body>
                    <nav>navigation should not dominate projection</nav>
                    <main>
                      <h1>Main Web Article</h1>
                      <p>This local page validates live fetch source history.</p>
                    </main>
                  </body>
                </html>
                """,
                "text/html; charset=utf-8",
            )
            return
        if self.path.startswith("/search.html"):
            self._send(
                200,
                b"""
                <!doctype html>
                <html>
                  <head><title>Search fixture</title></head>
                  <body>
                    <a class="result__a" href="https://example.test/qwen25">Qwen2.5 AWQ vLLM report</a>
                    <div class="result__snippet">Validated with bounded Phase-1 cases.</div>
                    <a class="result__a" href="https://example.test/ds14b">DS14B WNA16 failure report</a>
                    <div class="result__snippet">Historical compressed-tensors compatibility failure.</div>
                  </body>
                </html>
                """,
                "text/html; charset=utf-8",
            )
            return
        if self.path.startswith("/empty-search.html"):
            self._send(
                200,
                b"""
                <!doctype html>
                <html>
                  <head><title>Empty Search fixture</title></head>
                  <body><p>No parser-visible result rows.</p></body>
                </html>
                """,
                "text/html; charset=utf-8",
            )
            return
        if self.path.startswith("/bing-search.html"):
            self._send(
                200,
                b"""
                <!doctype html>
                <html>
                  <head><title>Bing fixture</title></head>
                  <body>
                    <ol>
                      <li class="b_algo">
                        <h2><a href="https://www.bing.com/ck/a?u=a1aHR0cHM6Ly9kb2NzLnZsbG0uYWkvZW4vbGF0ZXN0L2ZlYXR1cmVzL3F1YW50aXphdGlvbi9hdXRvX2F3cS5odG1s">Bing style AWQ result</a></h2>
                        <div class="b_caption"><p>vLLM documentation page about AWQ quantization.</p></div>
                      </li>
                      <li class="b_algo">
                        <h2><a href="https://www.bing.com/ck/a?u=a1aHR0cHM6Ly9naXRodWIuY29tL3ZsbG0tcHJvamVjdC92bGxt">Bing style GitHub result</a></h2>
                        <div class="b_caption"><p>vLLM GitHub repository.</p></div>
                      </li>
                    </ol>
                  </body>
                </html>
                """,
                "text/html; charset=utf-8",
            )
            return
        self._send(404, b"missing", "text/plain")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    unittest.main()
