"""Host acquisition vs. verified Tool Result supply vs. recovery view."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from harness.codex_dynamic_tools import DynamicToolBinding, HarnessDynamicToolAdapter
from harness.evidence_provenance import source_inventory, source_reading_progress, record_source_delivery
from harness.execution_host import SharedExecutionHost
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from harness.responses_bridge import ProviderHistoryBridge
from harness.workflow_continuity import source_coverage
from phase2.web_adapter import WebAdapter
from phase2.web_capability import WebFetchCapability, web_fetch_metadata
from phase2.web_context import ProjectionLimits
from runtime.tools import ToolRegistry
from runtime.sandbox import Sandbox
from runtime.ledger import LedgerStub


class SourceReadingProgressTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.web=WebAdapter(snapshot_root=self.root/'snapshots')
        self.web._http_get=Mock(return_value={
            'body':('<html><main><p>'+'Evidence text, not semantic proof. '*65+'</p></main></html>').encode(),
            'content_type':'text/html','status':200})
        cap=WebFetchCapability(db_path=self.root/'source.sqlite',adapter=self.web,
            projection_limits=ProjectionLimits(max_sources=1,per_source_chars=3000,total_chars=3000))
        reg=ToolRegistry(Sandbox(self.root,self.root),LedgerStub(self.root/'traces'))
        reg.register_capability(web_fetch_metadata(),cap)
        spec=DynamicToolBinding.from_registry(reg,'web.fetch',description='Read saved source',
            input_schema={'type':'object','properties':{'url':{'type':'string'}},'required':['url']})
        self.semantic=HarnessSemanticStateAdapter(require_registered_input=True)
        self.semantic.prepare_turn('t','Read the source and distinguish missing evidence.',turn_id='turn')
        self.adapter=HarnessDynamicToolAdapter(reg,[spec],max_output_chars=5000,
            execution_boundary=SharedExecutionHost(reg,self.semantic,self.root/'contract.jsonl'))
        self.adapter.bind_semantic_state_adapter(self.semantic)
        self.url='https://example.test/article'

    def dispatch(self,cid='first',**kwargs):
        dispatch=self.adapter.dispatch({'threadId':'t','turnId':'turn','callId':cid,
            'tool':'web_fetch','arguments':{'url':self.url,**kwargs}})
        wire=dispatch.to_app_server_response()['contentItems'][0]['text']
        return dispatch,json.loads(wire),wire

    def echo(self,dispatch,payload=None,*,thread='t',turn='turn'):
        payload=payload or json.loads(dispatch.to_app_server_response()['contentItems'][0]['text'])
        self.semantic.consume_raw_event({'method':'rawResponseItem/completed','params':{
            'threadId':thread,'turnId':turn,'item':{'type':'function_call_output',
            'call_id':dispatch.call_id,'output':json.dumps(payload,ensure_ascii=False)}}},
            raw_event_reference={'path':'fixture.jsonl','line':1})

    def steps(self):return self.semantic._state_for('t').runtime_objects.step_runs
    def progress(self,payload):
        e=payload['data']['source_excerpt']
        return source_reading_progress(self.steps(),e['source_event_id'],e['content_sha256'])

    def test_acquisition_alone_is_not_historical_supply(self):
        d,p,_=self.dispatch()
        self.assertEqual(self.progress(p)['state'],'not_established')
        self.assertIsNone(self.progress(p)['saved_text_fully_supplied'])
        self.assertFalse(source_inventory(self.steps())[0]['excerpt_supplied'])

    def test_verified_shorter_echo_does_not_upgrade_unseen_acquired_remainder(self):
        self.adapter.max_output_chars=3500
        d,p,_=self.dispatch()
        acquired=d.tool_result.data['source_excerpt']['text'];actual=p['data']['source_excerpt']['text']
        self.assertLess(len(actual),len(acquired))
        self.echo(d,p)
        source=source_inventory(self.steps())[0]
        self.assertTrue(source['excerpt_supplied']);self.assertEqual(source['excerpt'],actual)
        self.assertFalse(self.progress(p)['saved_text_fully_supplied'])
        self.assertNotEqual(source['excerpt'],acquired)

    def complete(self):
        d,p,_=self.dispatch();self.echo(d,p);first=p['data']['source_excerpt']
        offset=first['next_start_char'];count=0
        while offset is not None:
            count+=1
            d,p,_=self.dispatch('part'+str(count),source_event_id=first['source_event_id'],start_char=offset,max_chars=3000)
            self.echo(d,p);offset=p['data']['source_excerpt']['next_start_char']
            self.assertLess(count,10)
        return d,p

    def test_complete_saved_text_survives_short_recovery_view(self):
        d,p=self.complete();progress=self.progress(p);total=p['data']['source_excerpt']['extracted_text_chars']
        self.assertTrue(progress['saved_text_fully_supplied'])
        self.assertEqual(progress['supplied_ranges'],[[0,total]])
        self.assertIsNone(progress['next_unsupplied_start_char'])
        recovery=self.semantic.recovery_sources('t')[0]
        self.assertLessEqual(len(recovery['text']),300)
        self.assertTrue(recovery['historical_supply']['saved_text_fully_supplied'])
        self.assertEqual(recovery['end_char'],recovery['start_char']+len(recovery['text']))
        state=self.semantic.snapshot('t')
        self.assertFalse(state['workflow_continuity']['completion_established'])
        self.assertIsNone(state['phase1_runtime_snapshot']['active_goal'])
        self.assertTrue(all(s['content_supported']=='not_assessed' for s in source_inventory(self.steps())))

    def test_duplicate_echo_is_idempotent_and_cannot_overwrite_history(self):
        d,p,_=self.dispatch()
        receipt=deepcopy(self.steps()[0].action['host_execution_receipt'])
        outcome=deepcopy(self.steps()[0].action['outcome'])
        self.echo(d,p)
        self.assertEqual(self.steps()[0].action['host_execution_receipt'],receipt)
        self.assertEqual(self.steps()[0].action['outcome'],outcome)
        before=deepcopy(self.steps()[0].action['source_delivery'])
        self.echo(d,p)
        self.assertEqual(self.steps()[0].action['source_delivery'],before)
        self.assertEqual(self.progress(p)['supplied_chars'],len(p['data']['source_excerpt']['text']))

    def test_wrong_call_turn_source_hash_or_text_does_not_create_delivery(self):
        mutations=[
          lambda p:p['data']['source_excerpt'].update(text='invented'),
          lambda p:p['data']['source_excerpt'].update(content_sha256='wrong'),
          lambda p:p['data']['source_excerpt'].update(source_event_id='unknown'),
          lambda p:p['data']['source_excerpt'].update(extracted_text_sha256='wrong'),
          lambda p:p['data']['source_excerpt'].update(start_char=True),
          lambda p:p['data']['source_excerpt'].update(end_char=999999),
          lambda p:p['identity'].update(call_id='other'),
          lambda p:p.update(identity='malformed'),
          lambda p:p.update(data='malformed'),
        ]
        for index,mutate in enumerate(mutations):
            d,p,_=self.dispatch('bad'+str(index));mutate(p)
            self.echo(d,p)
            step=next(s for s in self.steps() if s.action['harness']['call_id']==d.call_id)
            self.assertNotIn('source_delivery',step.action)
        d,p,_=self.dispatch('wrongturn');self.echo(d,p,turn='foreign')
        step=next(s for s in self.steps() if s.action['harness']['call_id']==d.call_id)
        self.assertNotIn('source_delivery',step.action)

    def test_assistant_claim_does_not_add_supply(self):
        d,p,_=self.dispatch()
        self.semantic.consume_raw_event({'method':'item/completed','params':{'threadId':'t','turnId':'turn',
            'item':{'type':'agentMessage','id':'claim','text':'I read every page.'}}})
        self.assertEqual(self.progress(p)['state'],'not_established')

    def test_missing_host_receipt_cannot_be_upgraded_by_echo(self):
        d,p,_=self.dispatch()
        step=self.steps()[0];step.action.pop('host_execution_receipt')
        self.assertFalse(record_source_delivery(step,p,provenance={'source':'fake'}))
        self.assertNotIn('source_delivery',step.action)

    def test_changed_acquisition_after_recording_invalidates_delivery(self):
        d,p,_=self.dispatch();self.echo(d,p)
        self.steps()[0].action['host_execution_receipt']['result']['data']['source_excerpt']['text']='changed'
        self.assertEqual(self.progress(p)['state'],'not_established')

    def test_equal_extracted_text_reference_does_not_merge_snapshot_versions(self):
        _,complete=self.complete()
        prior=complete['data']['source_excerpt']['source_event_id']
        # New HTML acquisition, equal normalized extract. The first saved version
        # stays fully supplied; the new version is initially unknown.
        self.web._http_get.return_value['body']=self.web._http_get.return_value['body'].replace(b'<html>',b'<html><!--version2-->')
        d,p,_=self.dispatch('newversion',max_chars=400)
        current=p['data']['source_excerpt']['source_event_id']
        self.assertNotEqual(current,prior)
        self.assertEqual(self.progress(p)['state'],'not_established')
        recovery=self.semantic.recovery_sources('t')[0]
        self.assertEqual(recovery['source_event_id'],current)
        self.assertEqual(recovery['same_extracted_text_as']['source_event_id'],prior)
        self.assertTrue(recovery['same_extracted_text_as']['historical_supply']['saved_text_fully_supplied'])
        self.echo(d,p)
        self.assertFalse(self.progress(p)['saved_text_fully_supplied'])
        self.assertEqual(self.web._http_get.call_count,2)  # no automatic suppression or cache substitution

    def test_changed_extracted_text_does_not_get_equal_content_reference(self):
        self.complete()
        self.web._http_get.return_value['body']=b'<html><p>Different text, no inherited completeness.</p></html>'
        self.dispatch('different')
        self.assertNotIn('same_extracted_text_as',self.semantic.recovery_sources('t')[0])

    def test_overlaps_are_counted_once_and_holes_are_not_full_supply(self):
        d,p,_=self.dispatch('a',max_chars=400);self.echo(d,p)
        sid=p['data']['source_excerpt']['source_event_id']
        d2,p2,_=self.dispatch('b',source_event_id=sid,start_char=200,max_chars=400);self.echo(d2,p2)
        progress=self.progress(p2)
        self.assertEqual(progress['supplied_ranges'],[[0,600]])
        self.assertEqual(progress['supplied_chars'],600)
        self.assertEqual(progress['next_unsupplied_start_char'],600)
        d3,p3,_=self.dispatch('c',source_event_id=sid,start_char=900,max_chars=400);self.echo(d3,p3)
        progress=self.progress(p3)
        self.assertFalse(progress['saved_text_fully_supplied'])
        self.assertEqual(progress['supplied_ranges'],[[0,600],[900,1300]])

    def test_budget_shortens_only_current_recovery_not_historical_progress(self):
        _,p=self.complete()
        source=self.semantic.recovery_sources('t')[0]
        before=deepcopy(source['historical_supply'])
        with ProviderHistoryBridge('http://127.0.0.1:8003',journal_path=self.root/'journal') as bridge:
            blocks={'uaea.recovery_sources':{'kind':'untrusted','value':json.dumps([source],ensure_ascii=False)}}
            original=bridge.max_recovery_bytes
            size=len(json.dumps(bridge._render_blocks(blocks),ensure_ascii=False).encode())
            bridge.max_recovery_bytes=size-10
            output,omitted,_=bridge._bounded_blocks(blocks)
            recovered=json.loads(output['uaea.recovery_sources']['value'])[0]
            self.assertTrue(omitted)
            self.assertLess(len(recovered['text']),len(source['text']))
            self.assertEqual(recovered['end_char'],recovered['start_char']+len(recovered['text']))
            self.assertEqual(recovered['historical_supply'],before)
            self.assertTrue(recovered['historical_supply']['saved_text_fully_supplied'])
            self.assertEqual(blocks['uaea.recovery_sources']['value'],json.dumps([source],ensure_ascii=False))

    def test_old_workflow_delivery_is_not_adopted_as_new_workflow_supply(self):
        _,payload=self.complete()
        old=payload['data']['source_excerpt']['source_event_id']
        self.semantic.consume_raw_event({'method':'turn/completed','params':{
            'threadId':'t','turn':{'id':'turn','status':'completed'}}})
        self.semantic.prepare_turn('t','new task: independently inspect the saved source.',turn_id='other')
        dispatch=self.adapter.dispatch({'threadId':'t','turnId':'other','callId':'new-owner',
            'tool':'web_fetch','arguments':{'url':self.url,'source_event_id':old,'max_chars':400}})
        self.assertTrue(dispatch.ok)
        recovery=self.semantic.recovery_sources('t')[0]
        self.assertEqual(recovery['source_event_id'],old)
        self.assertEqual(recovery['historical_supply']['state'],'not_established')
        self.assertNotIn('same_extracted_text_as',recovery)

    def test_recent_fetch_survives_ahead_of_old_discovery_urls(self):
        d,p,_=self.dispatch()
        # source_coverage accepts actual Step records. Add only discovery URLs;
        # this tests deterministic recency, not a semantic relevance classifier.
        from types import SimpleNamespace
        old=SimpleNamespace(tool='web_search',capability='web.search',status='completed',
            action={'harness':{'call_id':'s','turn_id':'turn'},'outcome':{
                'execution_succeeded':True,'evidence_status':'candidates_available','observation_id':'search',
                'citable_candidates':[{'url':'https://old.test/first'},{'url':self.url}]}})
        coverage=source_coverage([old,*self.steps()])
        self.assertEqual(coverage['sources'][0]['url'],self.url)
        self.assertEqual(coverage['sources'][0]['fetch_state'],'fetched')


if __name__=='__main__':unittest.main()
