from __future__ import annotations

import json
import unittest

from harness.event_normalizer import HarnessEventNormalizer
from harness.io_contract import turn_context_payload
from harness.semantic_state_adapter import HarnessSemanticStateAdapter


def _event(method: str, params: dict) -> dict:
    return {"message": {"jsonrpc": "2.0", "method": method, "params": params}}


def _user(thread_id: str, turn_id: str, item_id: str, text: str) -> dict:
    return _event(
        "item/completed",
        {
            "threadId": thread_id,
            "turnId": turn_id,
            "item": {
                "type": "userMessage",
                "id": item_id,
                "content": [{"type": "text", "text": text}],
            },
        },
    )


def _completed(thread_id: str, turn_id: str, status: str = "completed") -> dict:
    return _event(
        "turn/completed",
        {
            "threadId": thread_id,
            "turn": {"id": turn_id, "status": status},
        },
    )


class HarnessSemanticStateAdapterTests(unittest.TestCase):
    def test_turn_scope_expires_at_completion_and_cannot_affect_next_turn(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn("thread", "本轮只关注论文", turn_id="t1")
        self.assertIn("prefer:academic_papers", projection.payload["source_preferences"])
        self.assertEqual(projection.payload["constraints"], [])
        adapter.consume_raw_event(_completed("thread", "t1"))
        snapshot = adapter.snapshot("thread")
        constraint = next(item for item in snapshot["semantic_items"]
                          if item["metadata"]["kind"] == "capability_constraint")
        self.assertEqual(constraint["metadata"]["scope"], "turn")
        self.assertEqual(constraint["status"], "expired")
        self.assertEqual(constraint["metadata"]["lifecycle_reason"], "turn_terminal_boundary")
        next_projection = adapter.prepare_turn("thread", "继续研究", turn_id="t2")
        self.assertNotIn("prefer:academic_papers", next_projection.payload["source_preferences"])

    def test_relation_signal_alone_does_not_authorize_owner_change(self):
        adapter = HarnessSemanticStateAdapter()
        first = adapter.prepare_turn("thread", "指定google站点", turn_id="t1")
        adapter.consume_raw_event(_completed("thread", "t1"))
        second = adapter.prepare_turn(
            "thread", "agi ai agent最近3个月的相关研究，最好是开发论坛的，github等", turn_id="t2",
        )
        self.assertEqual(second.payload["turn_relation"]["relation"], "new_task")
        self.assertEqual(first.payload["task_id"], second.payload["task_id"])
        self.assertIn("web.fallback=forbidden", second.payload["constraints"])
        self.assertFalse(adapter.validate_tool_action(
            "thread", "web.search", {"provider": "google", "allow_fallback": True}, turn_id="t2",
        )["valid"])

    def test_task_scope_survives_continuation_reference_and_challenge(self):
        adapter = HarnessSemanticStateAdapter()
        first = adapter.prepare_turn("thread", "这次只关注论文", turn_id="t1")
        adapter.consume_raw_event(_completed("thread", "t1"))
        for turn_id, text in (("t2", "继续研究"), ("t3", "展开第一个方向"),
                              ("t4", "不对，请重新检查")):
            projection = adapter.prepare_turn("thread", text, turn_id=turn_id)
            self.assertEqual(projection.payload["task_id"], first.payload["task_id"])
            self.assertIn("prefer:academic_papers", projection.payload["source_preferences"])
            adapter.consume_raw_event(_completed("thread", turn_id))

    def test_explicit_owner_change_expires_task_items_but_retains_session_items(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "以后所有搜索都不要使用 Bing", turn_id="t1")
        adapter.consume_raw_event(_completed("thread", "t1"))
        previous = adapter.prepare_turn("thread", "这次只关注论文", turn_id="t2")
        adapter.consume_raw_event(_completed("thread", "t2"))
        projection = adapter.prepare_turn("thread", "新任务：研究编译器", turn_id="t3")
        self.assertNotEqual(projection.payload["task_id"], previous.payload["task_id"])
        self.assertNotIn("prefer:academic_papers", projection.payload["source_preferences"])
        self.assertIn("web.exclude_provider=bing", projection.payload["constraints"])
        decision = adapter.validate_tool_action(
            "thread", "web.search", {"provider": "bing", "allow_fallback": False}, turn_id="t3",
        )
        self.assertFalse(decision["valid"])
        self.assertEqual(decision["effective_state_id"], projection.payload["effective_state_id"])
        records = adapter.snapshot("thread")["semantic_items"]
        paper = next(item for item in records if item["metadata"]["value"] == "prefer:academic_papers")
        self.assertEqual(paper["status"], "expired")
        excluded = next(item for item in records if item["metadata"]["value"] == "web.exclude_provider=bing")
        self.assertEqual(excluded["status"], "active")
        self.assertEqual(excluded["metadata"]["scope"], "explicit_until_revoked")

    def test_cross_task_scope_and_explicit_revocation(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "本会话只关注论坛", turn_id="t1")
        adapter.consume_raw_event(_completed("thread", "t1"))
        projection = adapter.prepare_turn("thread", "新任务：论文复现", turn_id="t2")
        self.assertIn("prefer:forums", projection.payload["source_preferences"])
        revoked = adapter.prepare_turn("thread", "本会话取消搜索限制", turn_id="t3")
        self.assertNotIn("prefer:forums", revoked.payload["source_preferences"])
        item = next(item for item in adapter.snapshot("thread")["semantic_items"]
                    if item["metadata"]["value"] == "prefer:forums")
        self.assertEqual(item["metadata"]["lifecycle_reason"], "explicit_revocation")

    def test_explicit_replacement_preserves_superseded_record_and_source_identity(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "这次只使用 Google，不允许 fallback", turn_id="t1")
        adapter.consume_raw_event(_user("thread", "t1", "user-1", "这次只使用 Google，不允许 fallback"),
                                  raw_event_reference={"artifact": "fixture.jsonl", "line": 1})
        adapter.consume_raw_event(_completed("thread", "t1"))
        projection = adapter.prepare_turn("thread", "改用 DuckDuckGo，允许 fallback", turn_id="t2")
        decision = adapter.validate_tool_action(
            "thread", "web.search", {"provider": "duckduckgo", "allow_fallback": True}, turn_id="t2",
        )
        self.assertTrue(decision["valid"])
        self.assertEqual(decision["active_constraints"], projection.payload["constraints"])
        self.assertNotIn("web.provider=google", decision["active_constraints"])
        old = next(item for item in adapter.snapshot("thread")["semantic_items"]
                   if item["metadata"]["value"] == "web.provider=google")
        self.assertEqual(old["status"], "superseded")
        source = old["metadata"]["provenance"]
        self.assertEqual(source["turn_id"], "t1")
        self.assertEqual(source["item_id"], "user-1")
        self.assertEqual(source["raw_event_reference"]["artifact"], "fixture.jsonl")
        self.assertTrue(old["metadata"]["superseded_by"])

    def test_native_turn_binding_does_not_duplicate_input_or_change_resolution(self):
        adapter = HarnessSemanticStateAdapter()
        text = "这次只使用 Google，不允许 fallback"
        projection = adapter.prepare_turn("thread", text)
        adapter.consume_raw_event(_event("turn/started", {
            "threadId": "thread", "turn": {"id": "native-turn", "status": "inProgress"},
        }))
        adapter.consume_raw_event(_user("thread", "native-turn", "user-native", text))
        decision = adapter.validate_tool_action(
            "thread", "web.search", {"provider": "google", "allow_fallback": True},
            turn_id="native-turn", call_id="conflict",
        )
        self.assertEqual(projection.payload["effective_state_id"], decision["effective_state_id"])
        self.assertEqual(projection.payload["constraints"], decision["active_constraints"])
        self.assertFalse(decision["valid"])
        self.assertTrue(all(item["owner"] and item["metadata"]["scope"] == "task"
                            and item["metadata"]["provenance"]["turn_id"] == "native-turn"
                            for item in decision["semantic_items"]))
        adapter.consume_raw_event(_completed("thread", "native-turn"))
        snapshot = adapter.snapshot("thread")
        self.assertEqual(snapshot["turn_count"], 1)
        self.assertEqual(snapshot["phase1_runtime_snapshot"]["step_count"], 0)
        self.assertIsNone(snapshot["phase1_runtime_snapshot"]["active_goal"])
        self.assertEqual(snapshot["phase1_runtime_snapshot"]["planned_step_count"], 0)

    def test_scope_precedence_restores_session_policy_when_turn_item_expires(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "以后不允许 fallback", turn_id="t1")
        adapter.consume_raw_event(_completed("thread", "t1"))
        projection = adapter.prepare_turn("thread", "本轮允许 fallback", turn_id="t2")
        self.assertIn("web.fallback=allowed", projection.payload["constraints"])
        self.assertNotIn("web.fallback=forbidden", projection.payload["constraints"])
        adapter.consume_raw_event(_completed("thread", "t2"))
        next_projection = adapter.prepare_turn("thread", "继续研究", turn_id="t3")
        self.assertIn("web.fallback=forbidden", next_projection.payload["constraints"])
        self.assertFalse(adapter.validate_tool_action(
            "thread", "web.search", {"allow_fallback": True}, turn_id="t3",
        )["valid"])

    def test_projection_budget_fails_explicitly_instead_of_hiding_constraints(self):
        adapter = HarnessSemanticStateAdapter(max_projection_chars=600)
        with self.assertRaisesRegex(ValueError, "constraints were not dropped"):
            adapter.prepare_turn("thread", "仅使用 Google，不允许 fallback，不要 Bing")
        self.assertIn("web.provider=google", adapter.snapshot("thread")["constraints"])

    def test_negated_provider_does_not_become_a_required_provider(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn("thread", "以后不要使用 Bing 搜索引擎", turn_id="t1")
        self.assertIn("web.exclude_provider=bing", projection.payload["constraints"])
        self.assertNotIn("web.provider=bing", projection.payload["constraints"])

    def test_cancelled_turn_expires_only_turn_scoped_items(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "以后只关注论坛", turn_id="t1")
        adapter.consume_raw_event(_completed("thread", "t1"))
        adapter.prepare_turn("thread", "本轮只关注论文", turn_id="t2")
        adapter.consume_raw_event(_completed("thread", "t2", "interrupted"))
        snapshot = adapter.snapshot("thread")
        self.assertIn("prefer:forums", snapshot["source_preferences"])
        self.assertNotIn("prefer:academic_papers", snapshot["source_preferences"])

    def test_google_only_constraint_is_materialized_and_validates_actions(self):
        adapter = HarnessSemanticStateAdapter()
        thread_id = "thread-google-only"
        adapter.prepare_turn(
            thread_id,
            "仅使用 Google 搜索 LoRA 训练资料，不要 Bing，不允许 fallback",
            turn_id="turn-1",
        )

        rejected = adapter.validate_tool_action(
            thread_id,
            "web.search",
            {"query": "LoRA training", "provider": "google", "allow_fallback": True},
            turn_id="turn-1",
            call_id="call-conflict",
        )
        self.assertFalse(rejected["valid"])
        self.assertIn("web.provider=google", rejected["active_constraints"])
        self.assertIn("web.fallback=forbidden", rejected["active_constraints"])
        self.assertIn("fallback is forbidden", rejected["conflicts"][0])

        accepted = adapter.validate_tool_action(
            thread_id,
            "web.search",
            {"query": "LoRA training", "provider": "google", "allow_fallback": False},
            turn_id="turn-1",
            call_id="call-corrected",
        )
        self.assertTrue(accepted["valid"])

        snapshot = adapter.snapshot(thread_id)
        self.assertEqual(snapshot["phase1_context"]["turn_relation"]["relation"], "new_task")
        self.assertEqual(
            snapshot["semantic_constraint_provenance"][0]["source"],
            "phase1.semantic_observation.boundary",
        )
        self.assertEqual(len(snapshot["action_decisions"]), 2)

    def test_google_site_phrasing_and_followup_keep_current_task_constraint(self):
        adapter = HarnessSemanticStateAdapter()
        thread_id = "thread-google-site"
        adapter.prepare_turn(
            thread_id,
            "请只从google站点搜索，且搜索的内容按照英文翻译",
            turn_id="turn-1",
        )

        rejected = adapter.validate_tool_action(
            thread_id,
            "web.search",
            {
                "query": "Which websites are supported",
                "provider": "google",
                "allow_fallback": "true",
                "language": "en",
            },
            turn_id="turn-1",
        )
        self.assertFalse(rejected["valid"])
        self.assertIn("web.provider=google", rejected["active_constraints"])
        self.assertIn("web.fallback=forbidden", rejected["active_constraints"])

        accepted = adapter.validate_tool_action(
            thread_id,
            "web.search",
            {
                "query": "Which websites are supported",
                "provider": "google",
                "allow_fallback": "false",
                "language": "en",
            },
            turn_id="turn-1",
        )
        self.assertTrue(accepted["valid"])

        projection = adapter.prepare_turn(
            thread_id,
            "内容是AGI最近相关的研究，可以是任何领域的，但是不要中文网站的",
            turn_id="turn-2",
        )
        self.assertEqual(projection.payload["turn_relation"]["relation"], "continuation")
        self.assertIn("web.provider=google", projection.payload["constraints"])
        retained = adapter.validate_tool_action(
            thread_id,
            "web.search",
            {
                "query": "latest AGI research",
                "provider": "google",
                "allow_fallback": "true",
                "language": "en",
            },
            turn_id="turn-2",
        )
        self.assertFalse(retained["valid"])

    def test_new_task_releases_previous_web_constraint(self):
        adapter = HarnessSemanticStateAdapter()
        thread_id = "thread-task-scope"
        adapter.prepare_turn(
            thread_id,
            "仅使用 Google 搜索，不要 Bing，不允许 fallback",
            turn_id="turn-1",
        )
        adapter.validate_tool_action(
            thread_id,
            "web.search",
            {"query": "AI", "provider": "google", "allow_fallback": False},
            turn_id="turn-1",
        )

        projection = adapter.prepare_turn(
            thread_id,
            "搜索一个新的普通主题",
            turn_id="turn-2",
        )
        self.assertEqual(projection.payload["turn_relation"]["relation"], "new_task")
        self.assertEqual(projection.payload["constraints"], [])
        accepted = adapter.validate_tool_action(
            thread_id,
            "web.search",
            {"query": "ordinary topic", "provider": "google", "allow_fallback": False},
            turn_id="turn-2",
        )
        self.assertTrue(accepted["valid"])
        self.assertNotIn("web.provider=google", accepted["active_constraints"])

    def test_four_turn_probe_accumulates_semantic_state_and_bounded_projection(self):
        adapter = HarnessSemanticStateAdapter(max_projection_chars=1800)
        thread_id = "thread-research"
        turns = (
            ("turn-1", "AI agent research"),
            ("turn-2", "只关注论文和论坛，不要商业宣传"),
            ("turn-3", "哪些方向更值得研究？"),
            ("turn-4", "展开第一个方向"),
        )

        for turn_id, text in turns:
            projection = adapter.prepare_turn(thread_id, text, turn_id=turn_id)
            self.assertLessEqual(len(projection.to_context_value()), 1800)
            adapter.consume_raw_event(
                _user(thread_id, turn_id, f"user-{turn_id}", text),
                raw_event_reference={"fixture": "semantic-probe"},
            )
            adapter.consume_raw_event(_completed(thread_id, turn_id))

        snapshot = adapter.snapshot(thread_id)
        self.assertEqual(snapshot["turn_count"], 4)
        self.assertEqual(snapshot["completed_turn_count"], 4)
        self.assertEqual(snapshot["topic"], "AI agent research")
        self.assertIn("prefer:academic_papers", snapshot["source_preferences"])
        self.assertIn("prefer:forums", snapshot["source_preferences"])
        self.assertIn("exclude:commercial_promotional", snapshot["source_preferences"])
        self.assertEqual(snapshot["constraints"], [])
        self.assertEqual(snapshot["turn_relation"]["relation"], "reference")
        self.assertEqual(snapshot["references"], ["direction:first"])
        self.assertEqual(len(snapshot["semantic_observations"]), 0)
        self.assertGreater(snapshot["phase1_projection_count"], 0)
        self.assertEqual(snapshot["last_projection"]["schema"], "uaea.semantic_projection.v0")
        self.assertEqual(snapshot["last_projection"]["topic"], "AI agent research")
        self.assertLessEqual(
            len(json.dumps(snapshot["last_projection"], ensure_ascii=False)),
            1800,
        )

        next_projection = adapter.prepare_turn(thread_id, "请比较第一个方向的证据")
        self.assertEqual(next_projection.payload["topic"], "AI agent research")
        self.assertIn("prefer:academic_papers", next_projection.payload["source_preferences"])
        self.assertEqual(next_projection.payload["turn_relation"]["relation"], "reference")

    def test_relation_classification_covers_new_task_continuation_reference_challenge(self):
        adapter = HarnessSemanticStateAdapter()
        thread_id = "thread-relations"
        cases = (
            ("turn-1", "AI agent research", "new_task"),
            ("turn-2", "继续研究这个主题", "continuation"),
            ("turn-3", "展开第一个方向", "reference"),
            ("turn-4", "不对，请重新检查这个结论", "challenge"),
        )
        for turn_id, text, expected in cases:
            projection = adapter.prepare_turn(thread_id, text, turn_id=turn_id)
            self.assertEqual(projection.payload["turn_relation"]["relation"], expected)
            adapter.consume_raw_event(_user(thread_id, turn_id, turn_id, text))
            adapter.consume_raw_event(_completed(thread_id, turn_id))

    def test_execution_observation_semantic_observation_and_provenance_are_retained(self):
        adapter = HarnessSemanticStateAdapter()
        thread_id = "thread-observation"
        adapter.prepare_turn(thread_id, "AI agent research", turn_id="turn-1")
        adapter.consume_raw_event(_user(thread_id, "turn-1", "user-1", "AI agent research"))
        adapter.consume_raw_event(
            _event(
                "item/completed",
                {
                    "threadId": thread_id,
                    "turnId": "turn-1",
                    "item": {
                        "type": "dynamicToolCall",
                        "id": "call-1",
                        "tool": "web_search",
                        "status": "completed",
                        "success": True,
                        "contentItems": [
                            {"type": "inputText", "text": '{"ok": true}'}
                        ],
                    },
                },
            ),
            raw_event_reference={"artifact": "app-server-events.jsonl"},
        )
        adapter.consume_raw_event(_completed(thread_id, "turn-1"))

        snapshot = adapter.snapshot(thread_id)
        self.assertEqual(len(snapshot["semantic_observations"]), 1)
        record = snapshot["semantic_observations"][0]
        self.assertEqual(record["execution_observation"]["tool_name"], "web_search")
        self.assertEqual(record["provenance"]["thread_id"], thread_id)
        self.assertEqual(record["provenance"]["turn_id"], "turn-1")
        self.assertEqual(record["provenance"]["item_id"], "call-1")
        self.assertEqual(record["provenance"]["raw_event_reference"]["artifact"], "app-server-events.jsonl")
        self.assertEqual(record["semantic_observation"]["type"], "semantic_observation")

    def test_per_thread_state_isolated_and_projection_is_additional_context(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread-a", "AI agent research")
        adapter.consume_raw_event(_user("thread-a", "turn-a", "user-a", "AI agent research"))
        adapter.consume_raw_event(_completed("thread-a", "turn-a"))
        adapter.prepare_turn("thread-b", "document migration")
        adapter.consume_raw_event(_user("thread-b", "turn-b", "user-b", "document migration"))
        adapter.consume_raw_event(_completed("thread-b", "turn-b"))

        payload = turn_context_payload(
            [],
            semantic_projection=adapter.prepare_turn("thread-a", "继续研究").payload,
        )
        state_a = adapter.snapshot("thread-a")
        state_b = adapter.snapshot("thread-b")
        self.assertEqual(state_a["topic"], "AI agent research")
        self.assertEqual(state_b["topic"], "document migration")
        self.assertIn("uaea.semantic_state_projection", payload)
        projection_value = payload["uaea.semantic_state_projection"]["value"]
        self.assertEqual(json.loads(projection_value)["schema"], "uaea.semantic_projection.v0")
        self.assertNotIn("topic", json.loads(projection_value))
        self.assertEqual(payload["uaea.semantic_interpretations"]["kind"], "untrusted")
        self.assertEqual(json.loads(payload["uaea.semantic_interpretations"]["value"])["topic"], "AI agent research")


if __name__ == "__main__":
    unittest.main()
