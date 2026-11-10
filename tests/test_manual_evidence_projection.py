"""Bounded model-surface contracts; no network, model or semantic truth oracle."""
from copy import deepcopy
import hashlib
import json
import unittest

from harness.codex_dynamic_tools import _bounded_json_text
from harness.io_contract import turn_context_payload
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from tests import test_fetch_evidence_budget as fetch_fixtures
from tests.test_harness_semantic_state_adapter import _completed


class ManualEvidenceProjectionTests(unittest.TestCase):
    def fetch(self, *, text=None, start=0, total=9000):
        p = fetch_fixtures.FetchEvidenceBudgetTests().payload(text if text is not None else 'Quoted "text" \n中文证据😀 '*200)
        p['data']['source_excerpt'].update(
            source_event_id='evt', content_sha256='raw-source-hash', start_char=start,
            end_char=start+len(p['data']['source_excerpt']['text']),
            extracted_text_chars=total, extracted_text_sha256='full-normalized-text-hash',
            has_more=True, next_start_char=start+len(p['data']['source_excerpt']['text']),
            snapshot_truncated=False)
        p['data']['evidence_reference'] = {'source_kind':'web_access_event','source_event_id':'evt'}
        return p

    def test_supplied_prefix_range_and_hash_match_escaped_unicode_wire(self):
        p = self.fetch(); before = deepcopy(p)
        wire = _bounded_json_text(p, 5000); d = json.loads(wire)['data']; e = d['source_excerpt']
        self.assertLessEqual(len(wire),5000)
        self.assertGreater(len(e['text']),0)
        self.assertLess(len(e['text']),len(p['data']['source_excerpt']['text']))
        self.assertEqual(e['text'],p['data']['source_excerpt']['text'][:len(e['text'])])
        self.assertEqual(e['text_sha256'],hashlib.sha256(e['text'].encode()).hexdigest())
        self.assertEqual(e['end_char'],len(e['text']))
        self.assertEqual(e['next_start_char'],e['end_char'])
        self.assertTrue(e['has_more'])
        self.assertIn('start_char=next_start_char',json.loads(wire)['message'])
        self.assertEqual(p,before)

    def test_nonzero_saved_segment_cursor_uses_supplied_not_acquired_length(self):
        p=self.fetch(start=3000)
        e=json.loads(_bounded_json_text(p,5000))['data']['source_excerpt']
        self.assertEqual(e['start_char'],3000)
        self.assertEqual(e['end_char'],3000+len(e['text']))
        self.assertEqual(e['next_start_char'],e['end_char'])

    def test_end_of_extracted_text_does_not_claim_complete_page_or_support(self):
        p=self.fetch(text='Last segment.',start=3000,total=3013)
        p['data']['source_excerpt'].update(has_more=False,next_start_char=None)
        v=json.loads(_bounded_json_text(p,5000))
        self.assertFalse(v['data']['source_excerpt']['has_more'])
        self.assertIsNone(v['data']['source_excerpt']['next_start_char'])
        self.assertIn('not a guarantee of full-page coverage',v['message'])

    def test_raw_snapshot_size_not_presented_as_extracted_text_length(self):
        p=self.fetch()
        d=json.loads(_bounded_json_text(p,5000))['data']
        self.assertEqual(d['evidence_extent']['snapshot_content_chars'],19000)
        self.assertEqual(d['source_excerpt']['extracted_text_chars'],9000)
        self.assertNotIn('source_text_chars',d['evidence_extent'])

    def test_temporal_and_authority_survive_verbose_audit_compaction(self):
        p=self.fetch()
        p['data']['temporal_facts']['publication_claims']=[
            {'field':'jsonld.datePublished','value':'2026-01-01','source_event_id':'evt'}]
        decision=p['data']['execution_decision']
        decision.update(action_id='call',input_id='input',workflow_id='workflow',
                        authorization={'state':'unknown'},allowed=False,reason='conflict')
        d=json.loads(_bounded_json_text(p,5000))['data']
        self.assertFalse(d['execution_decision']['allowed'])
        self.assertEqual(d['execution_decision']['authorization'],{'state':'unknown'})
        self.assertEqual(d['execution_decision']['effective_parameters'],decision['effective_parameters'])
        self.assertEqual(d['execution_decision']['parameter_sources'],decision['parameter_sources'])
        self.assertEqual(d['temporal_facts'],p['data']['temporal_facts'])
        self.assertEqual(d['execution_decision']['full_decision_sha256'],
            hashlib.sha256(json.dumps(decision,ensure_ascii=False,sort_keys=True).encode()).hexdigest())

    def test_invalid_source_hash_withholds_source_instead_of_repairing_it(self):
        p=self.fetch();p['data']['source_excerpt']['text_sha256']='bad'
        d=json.loads(_bounded_json_text(p,5000))['data']
        self.assertNotIn('source_excerpt',d)
        self.assertEqual(d['source_excerpt_status'],'invalid_acquired_excerpt_hash')

    def search(self, budget):
        p={'ok':True,'capability':'web.search','tool':'web_search','status':'success',
           'identity':{'call_id':'search-call'},'message':'verbose explanation '*100,
           'data':{'execution_succeeded':True,'actual_provider':'google',
                   'evidence_counts':{'raw':8,'retained':3,'visible':3,'discovery_citable':3,'page_content_acquired':0},
                   'evidence_boundary':{'schema':'uaea.evidence_boundary.v1','citation_scope':'search_result_only',
                                        'semantic_relevance':'unassessed','constraints_satisfied':'not_established'},
                   'citable_results':[{'title':f'Title {i}','url':f'https://example.org/{i}',
                                       'source_id':f'candidate:{i}','source_event_id':'search-event',
                                       'snippet':'Original candidate snippet. '*30} for i in range(3)]}}
        before=deepcopy(p);wire=_bounded_json_text(p,budget)
        self.assertEqual(p,before);self.assertLessEqual(len(wire),budget)
        v=json.loads(wire)
        self.assertNotIn('[field truncated]',v['message'])
        return p,v

    def test_search_uses_available_budget_for_more_than_120_snippet_chars(self):
        p,v=self.search(5000)
        candidates=v['data']['citable_results']
        self.assertEqual(len(candidates),3)
        self.assertGreater(len(candidates[0]['snippet']),120)
        for original,supplied in zip(p['data']['citable_results'],candidates):
            self.assertEqual(supplied['url'],original['url'])
            self.assertEqual(supplied['snippet'],original['snippet'][:len(supplied['snippet'])])
            self.assertEqual(supplied['snippet_truncated'],len(supplied['snippet'])<len(original['snippet']))
            self.assertNotIn('[field truncated]',supplied['snippet'])
        self.assertEqual(v['data']['evidence_counts']['page_content_acquired'],0)

    def test_search_pressure_preserves_identities_before_snippets(self):
        p,v=self.search(2300)
        candidates=v['data']['citable_results']
        self.assertEqual(len(candidates),3)
        for original,supplied in zip(p['data']['citable_results'],candidates):
            self.assertEqual(supplied['url'],original['url'])
            self.assertTrue(supplied['snippet_truncated'])
        self.assertEqual(v['data']['evidence_counts']['visible'],len(candidates))
        self.assertEqual(v['data']['evidence_boundary']['constraints_satisfied'],'not_established')


class HistoricalContextSurfaceTests(unittest.TestCase):
    def test_missing_marker_is_unknown_on_model_surface_without_changing_owner_or_authority(self):
        adapter=HarnessSemanticStateAdapter()
        first=adapter.prepare_turn('thread','你是什么模型',turn_id='t1')
        adapter.consume_raw_event(_completed('thread','t1'))
        current=adapter.prepare_turn('thread','指定google搜索最近的开源项目',turn_id='t2')
        before=deepcopy(current.payload)
        model=turn_context_payload([],semantic_projection=current.payload)
        context=json.loads(model['uaea.semantic_interpretations']['value'])
        authority=json.loads(model['uaea.semantic_state_projection']['value'])
        self.assertEqual(current.payload['turn_relation']['relation'],'new_task')  # legacy record retained
        self.assertEqual(context['relation_hint'],'unknown')
        self.assertEqual(context['background']['historical_topic'],'你是什么模型')
        self.assertNotIn('topic',context['background'])
        self.assertEqual(context['workflow_continuation']['current_request'],'指定google搜索最近的开源项目')
        self.assertEqual(first.payload['task_id'],authority['task_id'])
        self.assertEqual(authority['constraints'],current.payload['constraints'])
        self.assertFalse(authority['workflow_execution']['completion_established'])
        self.assertEqual(model['uaea.semantic_interpretations']['kind'],'untrusted')
        self.assertEqual(current.payload,before)

    def test_explicit_switch_and_ordinary_continuation_not_reclassified(self):
        adapter=HarnessSemanticStateAdapter()
        adapter.prepare_turn('thread','研究编译器',turn_id='t1')
        for i,text,expected in [('t2','继续研究','continuation'),('t3','new task: read the README','new_task')]:
            p=adapter.prepare_turn('thread',text,turn_id=i)
            context=json.loads(turn_context_payload([],semantic_projection=p.payload)['uaea.semantic_interpretations']['value'])
            self.assertEqual(context['relation_hint'],expected)


if __name__=='__main__': unittest.main()
