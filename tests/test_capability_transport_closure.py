"""Configuration and physical transport counterexamples; no model."""
import copy,json,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from harness.io_contract import effective_capability_state,turn_context_payload
from harness.request_audit import transport_state,RequestAudit
from research.goal_hypothesis_audit import transport_binding
from research.longitudinal_audit import document_delivery
class CapabilityClosure(unittest.TestCase):
 def shell(self,features,mode='read-only'):
  return effective_capability_state([{'name':'read_section'}],harness_config={'features':features},sandbox_mode=mode)['execution_planes']['harness_native_shell']
 def test_disabled_does_not_masquerade_as_read_only_shell(self):
  s=self.shell({'shell_tool':False,'unified_exec':False})
  self.assertIs(s['available'],False);self.assertEqual(s['filesystem'],'unavailable');self.assertEqual(s['sandbox_filesystem'],'read_only')
 def test_enabled_read_only(self):
  s=self.shell({'shell_tool':True,'unified_exec':False})
  self.assertIs(s['available'],True);self.assertEqual(s['filesystem'],'read_only')
 def test_enabled_workspace_write_is_distinct_metadata_not_permission(self):
  self.assertEqual(self.shell({'shell_tool':False,'unified_exec':True},'workspace-write')['filesystem'],'workspace_write')
 def test_missing_flags_stay_unknown(self):
  self.assertIsNone(self.shell({})['available'])
  self.assertIsNone(self.shell({'shell_tool':False})['available'])
 def test_context_reflects_real_generated_config(self):
  import tomllib
  from h3_context_characterization import write_config
  with tempfile.TemporaryDirectory() as d:
   home=Path(d);write_config(home,'http://127.0.0.1:8003',32768,n1x=True)
   cfg=tomllib.loads((home/'config.toml').read_text())
   c=turn_context_payload([{'name':'read_section'}],harness_config=cfg,sandbox_mode='read-only')
   state=json.loads(c['uaea.effective_capability_state']['value'])
   self.assertIs(state['execution_planes']['harness_native_shell']['available'],False)
   self.assertTrue(state['capabilities']['document.read_section']['available'])
   self.assertFalse(state['capabilities']['web.search']['available'])
   self.assertNotIn('web.fetch are available',c['uaea.runtime_facts.capabilities']['value'])
class TransportClosure(unittest.TestCase):
 def good(self):return {'request_id':'r','http_status':200,'bytes_received':100,'bytes_forwarded':100,'upstream_eof':True,'http_framing_complete':True,'response_complete':True,'transport_error':None,'utc':3}
 def test_complete_eof_and_bytes(self):
  self.assertEqual(transport_state(self.good()),'complete_success')
  self.assertEqual(transport_binding({'request_id':'r','utc':1},[self.good()])['status'],'PASS')
 def test_200_with_broken_pipe_never_passes(self):
  e={**self.good(),'transport_error':'BrokenPipeError'}
  self.assertEqual(transport_state(e),'partial')
  self.assertEqual(transport_binding({'request_id':'r','utc':1},[e])['status'],'FAIL')
 def test_partial_even_without_error_name(self):
  e={**self.good(),'response_complete':False,'upstream_eof':False}
  self.assertEqual(transport_state(e),'partial')
 def test_legacy_200_bytes_are_unknown(self):
  e={'request_id':'r','http_status':200,'bytes_received':100,'transport_error':None,'utc':3}
  self.assertEqual(transport_state(e),'unknown')
  self.assertEqual(transport_binding({'request_id':'r','utc':1},[e])['status'],'UNKNOWN')
 def test_forged_complete_without_eof_or_full_forwarding_not_proven(self):
  for change in [{'upstream_eof':False},{'bytes_forwarded':1}]:
   self.assertEqual(transport_state({**self.good(),**change}),'unknown')
 def test_error_before_response_not_partial(self):
  self.assertEqual(transport_state({'http_status':None,'transport_error':'ConnectionRefusedError'}),'failed_before_response')
 def test_request_audit_measures_not_fixed_success(self):
  with tempfile.TemporaryDirectory() as d:
   a=RequestAudit(Path(d)/'a.jsonl')
   a.response('r',status=200,bytes_received=100,bytes_forwarded=10,upstream_eof=False,error='BrokenPipeError')
   e=json.loads(a.path.read_text());self.assertFalse(e['response_complete'])
   self.assertEqual(transport_state(e),'partial')
class RealPartialTransport(unittest.TestCase):
 def test_loopback_client_reset_is_not_http_success(self):
  import http.client,socket,struct,threading,time
  from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
  from harness.responses_bridge import ProviderHistoryBridge
  release=threading.Event()
  class Receiver(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    self.rfile.read(int(self.headers['Content-Length']))
    self.send_response(200);self.end_headers();self.wfile.write(b'x');self.wfile.flush()
    release.wait(3)
    try:
     for _ in range(128):self.wfile.write(b'x'*65536);self.wfile.flush()
    except (BrokenPipeError,ConnectionResetError):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Receiver)
  t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
  try:
   with tempfile.TemporaryDirectory() as d:
    root=Path(d);audit=root/'audit.jsonl'
    with ProviderHistoryBridge(f'http://127.0.0.1:{server.server_port}',journal_path=root/'j.jsonl',audit_path=audit) as bridge:
     c=http.client.HTTPConnection('127.0.0.1',int(bridge.base_url.rsplit(':',1)[1]))
     c.request('POST','/v1/responses',json.dumps({'input':[]}).encode())
     r=c.getresponse();self.assertEqual(r.status,200);r.read(1)
     r.fp.raw._sock.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('ii',1,0))
     r.close();c.close();release.set()
     deadline=time.monotonic()+4;done=[]
     while time.monotonic()<deadline:
      done=[x for x in [json.loads(l) for l in audit.read_text().splitlines()] if x['event']=='transport_result']
      if done:break
      time.sleep(.02)
     self.assertTrue(done);self.assertFalse(done[0]['response_complete'])
     self.assertIn(done[0]['transport_error'],['BrokenPipeError','ConnectionResetError'])
     self.assertEqual(transport_state(done[0]),'partial')
  finally:release.set();server.shutdown();server.server_close();t.join()
class FixtureContextClosure(unittest.TestCase):
 def test_available_version_is_not_read_and_block_is_replaced(self):
  from unittest.mock import patch
  from research.longitudinal_dialogue import ScenarioApp
  from h3_harness_interactive_repl import InteractiveAppServer
  class Bridge:
   def __init__(self):self._runtime_context={'blocks':{},'input_id':'u1'}
   def set_runtime_context(self,blocks,**kw):self._runtime_context={**kw,'blocks':blocks}
  with tempfile.TemporaryDirectory() as d:
   app=object.__new__(ScenarioApp);app._history_bridge=Bridge();app.workspace=Path(d)
   app.thread_id='t';app.model='test-model';app._dynamic_tools=[{'name':'read_section'}];app._last_turn_context={}
   app.events_path=Path(d)/'events.jsonl'
   f=Path(d)/'sim.md';f.write_text('HIDDEN_NUMERIC_BODY')
   app.research_fixture_files=[{'path':str(f),'sha256':'version1','available_since_turn':1}]
   with patch.object(InteractiveAppServer,'_publish_runtime_context_snapshot',lambda self:None):
    app._publish_runtime_context_snapshot();app._publish_runtime_context_snapshot()
   blocks=app._history_bridge._runtime_context['blocks']
   value=json.loads(blocks['uaea.research_fixture']['value'])
   self.assertFalse(value['create_or_modify_required'])
   self.assertEqual(len(value['available_files']),1)
   self.assertNotIn('HIDDEN_NUMERIC_BODY',str(blocks))
   self.assertIn('File existence does not prove reading',value['instruction'])
   self.assertEqual(list(blocks).count('uaea.research_fixture'),1)
if __name__=='__main__':unittest.main()
