from pathlib import Path
import sys,unittest,runpy,tempfile,copy,json,uuid
from unittest.mock import patch
C=Path(__file__).parent/'candidate'
class Collector(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir='/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records');self.addCleanup(self.temp.cleanup)
  self.folder=Path(self.temp.name)
  with patch.object(sys,'argv',['guard_ctl.py',str(self.folder)]):self.g=runpy.run_path(str(C/'guard_ctl.py'))['collect_challenge'].__globals__
  self.guard=str(uuid.uuid4());self.sampler=str(uuid.uuid4());self.state={}
 def request(self,n=1,guard=None):
  guard=guard or self.guard
  return {'protocol':'single_clock_v1','guard_run_id':guard,'sampler_run_id':self.sampler,
   'request_seq':n,'nonce':guard+':'+str(n)+':'+uuid.uuid4().hex,'windows_issue_utc':1.0}
 def metric(self):return {'utc':1.,'gpu_total':64*2**30,'gpu_used':2**30,'gpu_free':63*2**30}
 def collect(self,q,fn=None):return self.g['collect_challenge'](q,self.state,self.sampler,sample_fn=fn or self.metric)
 def test_consumed_before_actual_query_and_once(self):
  q=self.request();seen=[]
  def read():
   self.assertEqual(self.state['identity'],(self.guard,1,q['nonce']));seen.append('query');return self.metric()
  f=self.collect(q,read);self.assertEqual(f['nonce'],q['nonce']);self.assertEqual(seen,['query'])
  self.assertIsNone(self.collect(q,read));self.assertEqual(seen,['query'])
 def test_each_new_challenge_performs_new_query(self):
  a=self.collect(self.request());z=self.collect(self.request(2))
  self.assertNotEqual(a['nonce'],z['nonce']);self.assertEqual((a['seq'],z['seq']),(1,2))
 def test_no_old_good_cache_on_query_failure(self):
  self.collect(self.request())
  q=self.request(2)
  with self.assertRaises(RuntimeError):self.collect(q,lambda:(_ for _ in ()).throw(RuntimeError('injected')))
  self.assertEqual(self.state['last_request'],2);self.assertIsNone(self.collect(q))
 def test_source_clock_does_not_gate_collection(self):
  for utc in [1.,1794300000.,1794390000.]:
   n=self.state.get('last_request',0)+1
   f=self.collect(self.request(n),lambda:{**self.metric(),'utc':utc})
   self.assertTrue(f['valid']);self.assertEqual(f['utc'],utc)
 def test_slow_collection_is_terminal(self):
  for d in [2.1,3.1]:
   self.state={};ticks=[0.]
   def read():ticks[0]+=d;return self.metric()
   with patch.object(self.g['time'],'monotonic',side_effect=lambda:ticks[0]):
    with self.assertRaises(TimeoutError):self.collect(self.request(),read)
 def test_cross_sampler_run(self):
  q=self.request();q['sampler_run_id']='other'
  with self.assertRaisesRegex(ValueError,'SAMPLER_RUN'):self.collect(q)
 def test_cross_guard_run(self):
  self.collect(self.request())
  with self.assertRaisesRegex(ValueError,'CROSS_RUN'):self.collect(self.request(2,str(uuid.uuid4())))
 def test_nonce_reuse_under_new_sequence(self):
  q=self.request();self.collect(q);q['request_seq']=2
  with self.assertRaisesRegex(ValueError,'NONCE'):self.collect(q)
 def test_sequence_reversal_and_conflict(self):
  self.collect(self.request(2))
  with self.assertRaisesRegex(ValueError,'REVERSE'):self.collect(self.request(1))
  with self.assertRaisesRegex(ValueError,'REPLAY_CONFLICT'):self.collect(self.request(2))
 def test_bad_protocol_sequence_and_counters(self):
  q=self.request();q['protocol']='old'
  with self.assertRaisesRegex(ValueError,'PROTOCOL'):self.collect(q)
  q=self.request();q['request_seq']=True
  with self.assertRaisesRegex(ValueError,'SEQUENCE'):self.collect(q)
  with self.assertRaisesRegex(ValueError,'INVALID_METRIC'):self.collect(self.request(),lambda:{'gpu_total':float('nan')})
if __name__=='__main__':unittest.main()
