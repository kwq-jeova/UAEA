import json,sys,tempfile,threading,time,unittest,http.client
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from harness.responses_bridge import ProviderHistoryBridge
from harness.request_audit import RequestAudit,transport_state
from research.longitudinal_dialogue import execution_config
class FramingTests(unittest.TestCase):
 def exchange(self,headers,body):
  class Upstream(BaseHTTPRequestHandler):
   protocol_version='HTTP/1.1'
   def log_message(self,*a):pass
   def do_POST(self):
    self.rfile.read(int(self.headers.get('Content-Length',0)))
    self.send_response(200)
    for k,v in headers.items():self.send_header(k,v)
    self.send_header('Connection','close');self.end_headers()
    self.wfile.write(body);self.wfile.flush();self.close_connection=True
  u=ThreadingHTTPServer(('127.0.0.1',0),Upstream);threading.Thread(target=u.serve_forever,daemon=True).start()
  try:
   with tempfile.TemporaryDirectory() as d:
    p=Path(d)
    with ProviderHistoryBridge(f'http://127.0.0.1:{u.server_port}',journal_path=p/'j',audit_path=p/'a') as b:
     c=http.client.HTTPConnection('127.0.0.1',int(b.base_url.rsplit(':',1)[1]),timeout=3)
     c.request('POST','/v1/responses',b'{"input":[]}');r=c.getresponse()
     self.assertEqual(r.status,200)
     try:r.read()
     except (http.client.IncompleteRead,ConnectionResetError):pass
     c.close()
     deadline=time.monotonic()+2
     while time.monotonic()<deadline:
      rr=[json.loads(x) for x in (p/'a').read_text().splitlines() if x]
      end=[x for x in rr if x['event']=='transport_result']
      if end:return end[0]
      time.sleep(.01)
     self.fail('missing final transport evidence')
  finally:u.shutdown();u.server_close()
 def test_fixed_100_advertised_3_received_is_partial(self):
  e=self.exchange({'Content-Length':'100'},b'abc')
  self.assertEqual(e['expected_body_bytes'],100);self.assertEqual(e['bytes_received'],3)
  self.assertEqual(e['bytes_forwarded'],3);self.assertTrue(e['upstream_eof'])
  self.assertFalse(e['http_framing_complete']);self.assertFalse(e['response_complete'])
  self.assertEqual(e['transport_error'],'IncompleteRead');self.assertEqual(transport_state(e),'partial')
 def test_fixed_exact_is_complete(self):
  e=self.exchange({'Content-Length':'3'},b'abc');self.assertEqual(transport_state(e),'complete_success')
  self.assertTrue(e['http_framing_complete'])
 def test_close_delimited_is_valid_http_not_sse_verdict(self):
  e=self.exchange({},b'abc');self.assertEqual(transport_state(e),'complete_success')
  self.assertIsNone(e['expected_body_bytes'])
 def test_chunked_truncation_is_partial(self):
  e=self.exchange({'Transfer-Encoding':'chunked'},b'3\r\nabc\r\n')
  self.assertEqual(transport_state(e),'partial');self.assertEqual(e['transport_error'],'IncompleteRead')
 def test_chunked_terminator_is_complete(self):
  e=self.exchange({'Transfer-Encoding':'chunked'},b'3\r\nabc\r\n0\r\n\r\n')
  self.assertEqual(transport_state(e),'complete_success')
 def test_direct_mismatched_expected_never_claims_complete(self):
  with tempfile.TemporaryDirectory() as d:
   a=RequestAudit(Path(d)/'a');a.response('r',status=200,bytes_received=3,bytes_forwarded=3,upstream_eof=True,expected_body_bytes=100)
   e=json.loads(a.path.read_text());self.assertFalse(e['response_complete']);self.assertFalse(e['http_framing_complete'])
  self.assertEqual(transport_state({**e,'response_complete':True}),'partial')
class FramingConsumerTests(unittest.TestCase):
 def valid(self):
  return {'http_status':200,'bytes_received':3,'bytes_forwarded':3,
          'response_complete':True,'upstream_eof':True,'http_framing_complete':True}
 def test_missing_framing_stays_unknown_despite_legacy_success(self):
  e=self.valid();e.pop('http_framing_complete')
  self.assertEqual(transport_state(e),'unknown')
 def test_explicit_false_overrides_other_success(self):
  e={**self.valid(),'http_framing_complete':False}
  self.assertEqual(transport_state(e),'partial')
 def test_only_boolean_true_can_validate_framing(self):
  for v in [None,1,'true',[],{}]:
   self.assertEqual(transport_state({**self.valid(),'http_framing_complete':v}),'unknown')
 def test_true_still_requires_eof_and_matching_bytes(self):
  self.assertEqual(transport_state(self.valid()),'complete_success')
  for change in [{'upstream_eof':False},{'bytes_forwarded':2},{'bytes_received':-1}]:
   self.assertNotEqual(transport_state({**self.valid(),**change}),'complete_success')
 def test_early_eof_cannot_be_forged_success(self):
  e={**self.valid(),'expected_body_bytes':100}
  self.assertEqual(transport_state(e),'partial')
 def test_error_or_http_failure_cannot_pass(self):
  self.assertEqual(transport_state({**self.valid(),'transport_error':'BrokenPipeError'}),'partial')
  self.assertEqual(transport_state({**self.valid(),'http_status':500}),'complete_http_error')
class ConfigTests(unittest.TestCase):
 def test_frozen_timeout_used_and_match_required(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'protocol.json').write_text('{"turn_timeout_seconds":420}')
   self.assertEqual(execution_config(p)['turn_timeout_seconds'],420)
   self.assertEqual(execution_config(p,420)['turn_timeout_seconds'],420)
   with self.assertRaisesRegex(ValueError,'differs'):execution_config(p,180)
 def test_absent_bad_or_infinite_config_fails(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   for v in [None,0,-1,False,'420',float('inf'),float('nan')]:
    (p/'protocol.json').write_text(json.dumps({'turn_timeout_seconds':v}))
    with self.assertRaises(ValueError):execution_config(p)
 def test_prepare_preflight_and_mismatch_without_model(self):
  import subprocess
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);f=p/'fixture.json'
   f.write_text(json.dumps({'cases':[{'id':'example','turns':['first question','second question']}]}))
   out=p/'study'
   r=subprocess.run([sys.executable,str(ROOT/'scripts/research/longitudinal_prepare.py'),'--output',str(out),'--scenarios',str(f),'--turn-timeout','420'],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr)
   argv=[sys.executable,str(ROOT/'scripts/research/longitudinal_dialogue.py'),'--output',str(out),'--check-only']
   r=subprocess.run(argv,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
   self.assertEqual(json.loads(r.stdout)['turn_timeout_seconds'],420)
   r=subprocess.run(argv+['--turn-timeout','180'],capture_output=True,text=True);self.assertNotEqual(r.returncode,0)
if __name__=='__main__':unittest.main()
