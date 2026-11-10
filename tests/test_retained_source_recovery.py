"""Bounded source lookup and actual saved-snapshot execution, not entailment."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import Mock

import memory.sqlite_store  # Bind the host package before frozen Runtime path setup.
from harness.codex_dynamic_tools import DynamicToolBinding, HarnessDynamicToolAdapter
from harness.evidence_provenance import retained_source_index
from harness.execution_host import SharedExecutionHost
from harness.responses_bridge import ProviderHistoryBridge, ContextBudgetError
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from phase2.web_adapter import WebAdapter
from phase2.web_capability import WebFetchCapability, web_fetch_metadata
from runtime.tools import ToolRegistry
from runtime.sandbox import Sandbox
from runtime.ledger import LedgerStub


class RetainedSourceRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.web = WebAdapter(snapshot_root=self.root / 'snapshots')
        self.web._http_get = Mock(return_value={
            'body': b'<html><main><p>Original verified source: 731, not a guess.</p></main></html>',
            'content_type': 'text/html', 'status': 200})
        self.cap = WebFetchCapability(db_path=self.root / 'source.sqlite', adapter=self.web)
        reg = ToolRegistry(Sandbox(self.root, self.root), LedgerStub(self.root / 'trace'))
        reg.register_capability(web_fetch_metadata(), self.cap)
        binding = DynamicToolBinding.from_registry(reg, 'web.fetch', description='Read source',
            input_schema={'type': 'object', 'properties': {'url': {'type': 'string'}}, 'required': ['url']})
        self.semantic = HarnessSemanticStateAdapter(require_registered_input=True)
        self.semantic.prepare_turn('t', 'Read the sources, then report source-grounded details.', turn_id='seed')
        self.adapter = HarnessDynamicToolAdapter(reg, [binding],
            execution_boundary=SharedExecutionHost(reg, self.semantic, self.root / 'contract.jsonl'))
        self.adapter.bind_semantic_state_adapter(self.semantic)

    def dispatch(self, call_id, url, **args):
        return self.adapter.dispatch({'threadId': 't', 'turnId': 'seed', 'callId': call_id,
                                      'tool': 'web_fetch', 'arguments': {'url': url, **args}})

    def index(self):
        return self.semantic.recovery_source_index('t')

    def steps(self):
        return self.semantic._state_for('t').runtime_objects.step_runs

    def test_old_source_ids_remain_discoverable_beyond_three_recent_excerpts(self):
        for i in range(20):
            self.assertTrue(self.dispatch(str(i), f'https://example.test/{i}').ok)
        self.assertEqual(len(self.semantic.recovery_sources('t')), 3)
        index = self.index()
        self.assertEqual(len(index['entries']), 20)
        self.assertEqual(index['omitted_sources'], 0)
        self.assertLessEqual(len(json.dumps(index, ensure_ascii=False).encode()), 6000)
        self.assertIn('https://example.test/0', [x['url'] for x in index['entries']])
        self.assertTrue(all('text' not in x for x in index['entries']))

    def test_lookup_executes_retained_snapshot_without_http_or_completion_promotion(self):
        self.dispatch('first', 'https://example.test/old')
        ref = self.index()['entries'][0]
        original = deepcopy(self.steps()[0].action['host_execution_receipt'])
        result = self.dispatch('recover', ref['url'], source_event_id=ref['source_event_id'], max_chars=3000)
        self.assertTrue(result.ok)
        data = result.tool_result.data
        self.assertEqual(data['acquisition_mode'], 'retained_snapshot')
        self.assertFalse(data['http_attempted'])
        self.assertEqual(data['content_sha256'], ref['content_sha256'])
        text = data['source_excerpt']['text']
        self.assertIn('731', text)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), data['source_excerpt']['text_sha256'])
        self.assertEqual(self.web._http_get.call_count, 1)
        self.assertEqual(self.steps()[0].action['host_execution_receipt'], original)
        self.assertFalse(self.semantic.snapshot('t')['workflow_continuity']['completion_established'])
        self.assertIsNone(self.semantic.snapshot('t')['phase1_runtime_snapshot']['active_goal'])
        self.assertEqual(len(self.index()['entries']), 1)  # A new read is not a new source version.

    def test_same_url_different_snapshots_keep_separate_versions(self):
        self.dispatch('v1', 'https://example.test/version')
        self.web._http_get.return_value['body'] = b'<main><p>Changed original, value 952.</p></main>'
        self.dispatch('v2', 'https://example.test/version')
        refs = self.index()['entries']
        self.assertEqual(len(refs), 2)
        self.assertNotEqual(refs[0]['source_event_id'], refs[1]['source_event_id'])
        self.assertNotEqual(refs[0]['content_sha256'], refs[1]['content_sha256'])
        result = self.dispatch('old', refs[1]['url'], source_event_id=refs[1]['source_event_id'])
        self.assertIn('731', result.tool_result.data['source_excerpt']['text'])
        self.assertNotIn('952', result.tool_result.data['source_excerpt']['text'])
        self.assertEqual(self.web._http_get.call_count, 2)

    def test_missing_or_changed_file_never_silently_refetches(self):
        self.dispatch('first', 'https://example.test/missing')
        ref = self.index()['entries'][0]
        snapshot = next(self.web.snapshot_root.iterdir())
        snapshot.write_bytes(b'tampered')
        bad = self.dispatch('changed', ref['url'], source_event_id=ref['source_event_id'])
        self.assertFalse(bad.ok)
        self.assertEqual(bad.tool_result.data['execution_status'], 'source_unavailable')
        self.assertFalse(bad.tool_result.data['http_attempted'])
        self.assertFalse(bad.tool_result.data['retryable'])
        self.assertEqual(bad.tool_result.data['failure_scope'], 'saved_source_version')
        self.assertEqual(bad.observation.status, 'failure')
        visible = json.loads(bad.to_app_server_response()['contentItems'][0]['text'])
        self.assertEqual(visible['data']['execution_status'], 'source_unavailable')
        self.assertFalse(visible['data']['http_attempted'])
        snapshot.unlink()
        missing = self.dispatch('missing', ref['url'], source_event_id=ref['source_event_id'])
        self.assertFalse(missing.ok)
        self.assertEqual(missing.tool_result.data['recovery']['legal_next_steps'][0]['missing_details'], 'UNKNOWN')
        self.assertEqual(self.web._http_get.call_count, 1)
        self.assertFalse(self.semantic.snapshot('t')['workflow_continuity']['completion_established'])

    def test_wrong_url_or_unknown_id_cannot_resolve_a_different_source(self):
        self.dispatch('first', 'https://example.test/right')
        ref = self.index()['entries'][0]
        self.assertFalse(self.dispatch('wrong', 'https://example.test/wrong',
                                      source_event_id=ref['source_event_id']).ok)
        self.assertFalse(self.dispatch('unknown', ref['url'], source_event_id='invented').ok)
        self.assertEqual(self.web._http_get.call_count, 1)

    def test_model_claim_and_native_echo_cannot_create_lookup_entries(self):
        self.semantic.consume_raw_event({'method': 'item/completed', 'params': {
            'threadId': 't', 'turnId': 'seed', 'item': {'type': 'agentMessage',
            'id': 'claim', 'text': 'I read https://example.test/invented and confirmed its content.'}}})
        self.assertEqual(self.index()['total_sources'], 0)
        self.dispatch('first', 'https://example.test/right')
        self.steps()[0].action.pop('host_execution_receipt')
        self.assertEqual(self.index()['total_sources'], 0)

    def test_corrupt_receipt_excluded_and_foreign_workflow_not_inherited(self):
        self.dispatch('first', 'https://example.test/right')
        step = self.steps()[0]
        step.action['host_execution_receipt']['result']['data']['source_excerpt']['text'] = 'invented'
        self.assertEqual(self.index()['entries'], [])
        self.assertEqual(self.index()['invalid_receipts'], 1)
        self.semantic.prepare_turn('t', 'new task: unrelated independent question', turn_id='foreign')
        self.assertEqual(self.index()['total_sources'], 0)

    def test_conflicting_identity_is_not_resolved_to_latest_silently(self):
        self.dispatch('first', 'https://example.test/old')
        a = self.steps()[0]
        b = deepcopy(a)
        data = b.action['host_execution_receipt']['result']['data']
        data['url'] = 'https://example.test/another'
        index = retained_source_index([a, b], a.workflow_id)
        self.assertEqual(index['entries'], [])
        self.assertEqual(index['conflicting_identities'], 1)

    def test_missing_harness_metadata_does_not_invalidate_source_identity(self):
        self.dispatch('first', 'https://example.test/old')
        step = self.steps()[0]
        for metadata in (None, 'malformed', []):
            with self.subTest(metadata=metadata):
                step.action['harness'] = metadata
                index = retained_source_index([step], step.workflow_id)
                self.assertEqual(index['total_sources'], 1)
                self.assertEqual(index['entries'][0]['turn_id'], '')

    def test_catalogue_bound_and_disclosed_omissions(self):
        self.dispatch('first', 'https://example.test/a')
        a = self.steps()[0]
        steps = []
        for i in range(40):
            step = deepcopy(a)
            data = step.action['host_execution_receipt']['result']['data']
            data['access_event_id'] = data['source_excerpt']['source_event_id'] = f'source-{i}'
            data['url'] = 'https://example.test/' + str(i)
            steps.append(step)
        index = retained_source_index(steps, a.workflow_id)
        self.assertLessEqual(len(index['entries']), 32)
        self.assertLessEqual(len(json.dumps(index, ensure_ascii=False).encode()), 6000)
        self.assertEqual(index['omitted_sources'] + len(index['entries']), 40)

    def test_host_budget_removes_optional_index_without_altering_required_state(self):
        self.dispatch('first', 'https://example.test/right')
        with ProviderHistoryBridge('http://127.0.0.1:8003', journal_path=self.root / 'journal') as bridge:
            mandatory = {'uaea.current_user_request': {'kind': 'untrusted', 'value': 'Do not use tools.'}}
            size = len(json.dumps(bridge._render_blocks(mandatory), ensure_ascii=False).encode())
            bridge.max_recovery_bytes = size + 1
            blocks = {**mandatory, 'uaea.recovery_source_index': {'kind': 'untrusted',
                       'value': json.dumps(self.index())}}
            actual, omissions, count = bridge._bounded_blocks(blocks)
            self.assertEqual(actual, mandatory)
            self.assertIn('uaea.recovery_source_index', omissions)
            self.assertLessEqual(count, bridge.max_recovery_bytes)
            self.assertTrue(blocks['uaea.recovery_source_index'])
            bridge.max_recovery_bytes = size - 1
            with self.assertRaises(ContextBudgetError):
                bridge._bounded_blocks(blocks)

    def test_old_directory_expires_when_new_workflow_has_no_index(self):
        old = '<external_uaea.recovery_source_index>{"workflow_id":"old"}</external_uaea.recovery_source_index>'
        quote = 'User asks about this quoted text: ' + old
        request = {'input': [
            {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': old}]},
            {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': quote}]},
        ]}
        normalized, removed = ProviderHistoryBridge._without_host_blocks(request, {})
        self.assertEqual(removed, 1)
        self.assertEqual(normalized['input'][0]['content'][0]['text'], quote)
        self.assertEqual(len(request['input']), 2)

    def test_directory_yields_before_recent_text_within_same_budget(self):
        self.dispatch('first', 'https://example.test/right')
        recent = self.semantic.recovery_sources('t')
        base = {'uaea.current_user_request': {'kind': 'untrusted', 'value': 'Read the saved evidence.'},
                'uaea.recovery_sources': {'kind': 'untrusted', 'value': json.dumps(recent)}}
        blocks = {**base, 'uaea.recovery_source_index': {'kind': 'untrusted', 'value': json.dumps(self.index())}}
        original = deepcopy(blocks)
        with ProviderHistoryBridge('http://127.0.0.1:8003', journal_path=self.root / 'journal') as bridge:
            bridge.max_recovery_bytes = len(json.dumps(bridge._render_blocks(base), ensure_ascii=False).encode()) + 1
            output, omissions, count = bridge._bounded_blocks(blocks)
            self.assertEqual(output['uaea.recovery_sources'], base['uaea.recovery_sources'])
            self.assertFalse(any('recovery_sources.text:' in x for x in omissions))
            self.assertIn('uaea.recovery_source_index', omissions)
            self.assertLessEqual(count, bridge.max_recovery_bytes)
            self.assertEqual(blocks, original)


if __name__ == '__main__':
    unittest.main()
