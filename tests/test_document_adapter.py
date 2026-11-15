import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from harness.execution_host import SharedExecutionHost
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from h3_context_characterization import build_adapter
from research.document_adapter import ResearchDocumentAdapter
from research.document_fixture import render_snapshot


class ResearchDocumentAdapterTests(unittest.TestCase):
    def test_selected_body_complete_without_repeating_full_directory(self):
        with tempfile.TemporaryDirectory() as td:
            base = build_adapter(Path(td))
            body = "# source\n\n" + "".join("## "+str(i)+". Original section "+str(i)+"\n\nUSD millions; current 137, prior 94.\n\n" for i in range(1, 31))
            (Path(td)/"sandbox/source.md").write_text(body)
            binding = next(x for x in base.bindings if x.capability == "document.read_section")
            adapter = ResearchDocumentAdapter(base.registry, [binding], max_output_chars=12000)
            result = adapter.dispatch({"threadId":"t","turnId":"u","callId":"c","tool":"read_section",
                                       "arguments":{"path":"source.md","section_index":20}})
            payload = json.loads(result.to_app_server_response()["contentItems"][0]["text"])
            self.assertTrue(payload["data"]["document_projection"]["content_complete"])
            self.assertIn("137",payload["data"]["content"])
            self.assertLess(result.max_output_chars,12000)
            self.assertLess(payload["data"]["document_projection"]["catalog_supplied"],30)
            self.assertEqual(result.action_request.parameters["section_index"],20)
            self.assertTrue(result.ok)

    def test_directory_keeps_original_cap_and_actual_failure_stays_failure(self):
        with tempfile.TemporaryDirectory() as td:
            base = build_adapter(Path(td))
            binding = next(x for x in base.bindings if x.capability == "document.read_section")
            adapter = ResearchDocumentAdapter(base.registry,[binding],max_output_chars=12000)
            for index, expected in [(1,True),(999,False)]:
                result = adapter.dispatch({"threadId":"t","turnId":"u","callId":str(index),"tool":"read_section",
                                           "arguments":{"path":"README.md","section_index":index}})
                self.assertEqual(result.max_output_chars,12000)
                self.assertEqual(result.ok,expected)

    def test_rendered_directory_two_preserves_full_catalog_for_autonomous_discovery(self):
        html = ("<article><h1>Financial release</h1><p>Released November 3, 2026</p>" +
                "".join("<h2>Financial table " + str(i) + "</h2><table>"
                    "<tr><th>USD millions</th><th>Quarter ended 2026-09-26</th><th>Quarter ended 2025-09-27</th></tr>"
                    "<tr><td>Revenue</td><td>13,377</td><td>9,246</td></tr>"
                    "<tr><td>Gross profit</td><td>7,210</td><td>4,780</td></tr></table>" for i in range(1, 8)) +
                "</article>")
        markdown, _ = render_snapshot(html, url="https://example.org/release",
            captured_utc="2026-11-13T12:00:00Z", title="Frozen release")
        with tempfile.TemporaryDirectory() as td:
            base = build_adapter(Path(td))
            (Path(td)/"sandbox/source.md").write_text(markdown)
            binding = next(x for x in base.bindings if x.capability == "document.read_section")
            adapter = ResearchDocumentAdapter(base.registry,[binding],max_output_chars=12000)
            result = adapter.dispatch({"threadId":"t","turnId":"u","callId":"directory","tool":"read_section",
                "arguments":{"path":"source.md","section_index":2}})
            payload = json.loads(result.to_app_server_response()["contentItems"][0]["text"])
            self.assertTrue(result.ok)
            self.assertEqual(result.max_output_chars,12000)
            self.assertEqual(payload["data"]["section_index"],2)
            self.assertTrue(payload["data"]["document_projection"]["content_complete"])
            self.assertTrue(payload["data"]["document_projection"]["catalog_complete"])
            self.assertEqual(payload["data"]["section_catalog"],result.tool_result.data["section_catalog"])
            self.assertGreater(len(payload["data"]["section_catalog"]),2)
            # Discover a body using returned catalogue data; no hard-coded body ordinal.
            target = next(x for x in payload["data"]["section_catalog"] if "Table 1" in x["heading"])
            body = adapter.dispatch({"threadId":"t","turnId":"u","callId":"body","tool":"read_section",
                "arguments":{"path":"source.md","section_index":target["section_index"]}})
            supplied = json.loads(body.to_app_server_response()["contentItems"][0]["text"])["data"]
            self.assertEqual(supplied["content"],body.tool_result.data["content"])
            self.assertTrue(supplied["document_projection"]["content_complete"])
            for text in ["USD millions","2026-09-26","2025-09-27","Revenue","13,377","9,246","Gross profit","7,210"]:
                self.assertIn(text,supplied["content"])


class ResearchDocumentIndexGuardTests(unittest.TestCase):
    def build(self, root, *, shared=False):
        base = build_adapter(root)
        binding = next(x for x in base.bindings if x.capability == "document.read_section")
        semantic = HarnessSemanticStateAdapter()
        host = SharedExecutionHost(base.registry, semantic, root/"shared-execution.jsonl") if shared else None
        adapter = ResearchDocumentAdapter(base.registry, [binding], max_output_chars=12000,
                                          execution_boundary=host)
        adapter.bind_semantic_state_adapter(semantic)
        if shared:
            semantic.prepare_turn("thread", "Read source material", turn_id="turn")
        return adapter, semantic

    def params(self, value, cid="call"):
        return {"threadId":"thread","turnId":"turn","callId":cid,"tool":"read_section",
                "arguments":{"path":"README.md","section_index":value}}

    def test_invalid_values_return_failure_without_source_read_or_parameter_rewrite(self):
        with tempfile.TemporaryDirectory() as td:
            adapter, _ = self.build(Path(td))
            for index in (0, -1, True, False, "1", 1.5, None, [], {}):
                with self.subTest(index=index), patch.object(adapter.registry.sandbox, "read_path",
                        side_effect=AssertionError("Invalid index must not read a source")):
                    result = adapter.dispatch(self.params(index))
                    self.assertFalse(result.ok)
                    self.assertEqual(result.action_request.parameters["section_index"], index)
                    self.assertEqual(result.tool_result.data["error_code"], "invalid_section_index")
                    self.assertFalse(result.tool_result.data["execution_succeeded"])
                    self.assertFalse(result.tool_result.data["source_body_read"])
                    self.assertNotIn("content", result.tool_result.data)
                    self.assertNotIn("source_hash", result.tool_result.data)
                    self.assertTrue(result.tool_result.data["retryable"])

    def test_shared_host_records_real_rejected_attempt_and_observation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            adapter, semantic = self.build(root, shared=True)
            with patch.object(adapter.registry.sandbox, "read_path",
                              side_effect=AssertionError("No read for index zero")):
                result = adapter.dispatch(self.params(0, "zero"))
            state = semantic._state_for("thread")
            steps = state.runtime_objects.step_runs
            self.assertEqual(len(steps), 1)
            self.assertEqual(steps[0].action["harness"]["call_id"], "zero")
            self.assertIsNotNone(steps[0].execution_observation_id)
            events = [json.loads(line) for line in (root/"shared-execution.jsonl").read_text().splitlines()]
            observations = [x for x in events if x["event_type"] == "OBSERVATION"]
            self.assertEqual(len(observations), 1)
            obs = observations[0]["payload"]["execution_observation"]
            self.assertEqual(obs["observation_id"], steps[0].execution_observation_id)
            self.assertEqual(observations[0]["identity"]["item_id"], "zero")
            self.assertEqual(obs["data"]["error_code"], "invalid_section_index")
            self.assertFalse(obs["data"]["execution_succeeded"])
            receipt = json.loads(result.to_app_server_response()["contentItems"][0]["text"])
            self.assertFalse(receipt["ok"])
            self.assertEqual(receipt["identity"]["call_id"], "zero")
            self.assertEqual(receipt["identity"]["observation_id"], obs["observation_id"])
            self.assertEqual(receipt["data"]["requested_section_index"], 0)

    def test_positive_section_works_and_positive_out_of_range_is_original_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            adapter, _ = self.build(root)
            a = adapter.dispatch(self.params(1, "first"))
            b = adapter.dispatch(self.params(999, "outside"))
            self.assertTrue(a.ok)
            self.assertFalse(b.ok)
            self.assertEqual(b.tool_result.data["error_code"], "section_not_found")
            self.assertEqual(b.tool_result.data["requested_section_index"], 999)
            self.assertIn("section_catalog", b.tool_result.data)
            self.assertNotEqual(b.tool_result.data["error_code"], "invalid_section_index")

    def test_opt_in_leaves_unwrapped_phase1_registry_and_other_capabilities_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = build_adapter(root)
            # Legacy Phase-1 behavior is retained outside the opt-in adapter.
            legacy = base.registry.execute_capability("document.read_section",
                        {"path":"README.md","section_index":0}, "Legacy")
            self.assertTrue(legacy.ok)
            binding = next(x for x in base.bindings if x.capability == "document.read_section")
            guarded = ResearchDocumentAdapter(base.registry, [binding])
            execute = base.registry.execute_capability
            ResearchDocumentAdapter(base.registry, [binding])
            self.assertIs(base.registry.execute_capability, execute)
            listing = base.registry.execute_capability("fs.list", {"path":"."}, "List")
            self.assertTrue(listing.ok)
            self.assertIn("README.md", listing.data["entries"])


if __name__ == "__main__":
    unittest.main()
