from pathlib import Path
import http.client,json,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from harness.responses_bridge import ProviderHistoryBridge
class StreamObserverTests(unittest.TestCase):
 def setUp(self):
  class Upstream(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    self.rfile.read(int(self.headers['Content-Length']))
    self.send_response(200);self.send_header('Content-Length','3');self.end_headers();self.wfile.write(b'abc')
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Upstream)
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
 def tearDown(self):self.server.shutdown();self.server.server_close()
 def exchange(self,observer):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   with ProviderHistoryBridge(f'http://127.0.0.1:{self.server.server_port}',journal_path=p/'j',audit_path=p/'a',stream_observer=observer) as b:
    c=http.client.HTTPConnection('127.0.0.1',int(b.base_url.rsplit(':',1)[1]))
    c.request('POST','/v1/responses',b'{"input":[]}');r=c.getresponse()
    self.assertEqual(r.status,200);self.assertEqual(r.read(),b'abc');c.close()
   events=[json.loads(l) for l in (p/'a').read_text().splitlines()]
   result=next(x for x in events if x['event']=='transport_result')
   self.assertTrue(result['response_complete']);self.assertTrue(result['http_framing_complete'])
   return b
 def test_observed_bytes_preserved(self):
  seen=[]
  self.exchange(lambda stage,rid,chunk,metadata:seen.append((stage,chunk)))
  for stage in ['upstream','downstream']:
   self.assertEqual(b''.join(data for k,data in seen if k==stage),b'abc')
  self.assertEqual(seen[-1][0],'finished')
 def test_observer_failure_does_not_change_transport(self):
  def fail(*args):raise OSError('diagnostic failure')
  b=self.exchange(fail);self.assertGreaterEqual(b.stream_observer_errors,2)
if __name__=='__main__':unittest.main()
