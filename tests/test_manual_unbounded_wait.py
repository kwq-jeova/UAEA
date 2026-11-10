"""Manual lifetime regression: virtual long waits and CPU-only local transport."""
from contextlib import redirect_stdout
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import io
import json
import math
import os
from pathlib import Path
import queue
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from h3_harness_interactive_repl import InteractiveAppServer, _optional_wait_timeout, parse_args
from harness.responses_bridge import ProviderHistoryBridge
from phase2.terminal_input import read_user_input
from tests.test_native_user_input import request as question


class ManualUnboundedWaitTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.app=InteractiveAppServer(codex=self.root/'unused',codex_home=self.root/'home',
            workspace=self.root,base_url='http://127.0.0.1:8003',adapter=Mock(),
            events_path=self.root/'events.jsonl',stderr_path=self.root/'stderr',turn_timeout=0)
        self.app.thread_id='thread';self.app._send=Mock()
        self.app.semantic_state.prepare_turn('thread','Read the retained sources.',turn_id='turn')
        self.app._events_file=(self.root/'events.jsonl').open('w')
        self.addCleanup(self.app._events_file.close)

    def put(self,msg):self.app._queue.put(('stdout',json.dumps(msg)))
    def terminal(self,turn='turn',status='completed'):
        return {'method':'turn/completed','params':{'threadId':'thread','turn':{'id':turn,'status':status,'items':[]}}}
    def start(self):
        self.put({'id':99,'result':{'turn':{'id':'turn'}}})
        return {'id':99,'method':'turn/start','params':{'threadId':'thread'}}

    def test_zero_is_disabled_not_nonblocking_socket_timeout(self):
        self.assertIsNone(self.app.turn_timeout);self.assertIsNone(self.app.user_input_timeout)
        for value in (0,0.0,None):self.assertIsNone(_optional_wait_timeout(value))
        self.assertEqual(_optional_wait_timeout(420),420)
        for value in (-1,float('nan'),float('inf'),True,'0'):
            with self.subTest(value=value),self.assertRaises(ValueError):_optional_wait_timeout(value)

    def test_virtual_hours_do_not_end_manual_turn_and_final_response_is_handled(self):
        start=self.start()
        self.put({'method':'item/started','params':{'threadId':'thread','turnId':'turn',
                  'item':{'type':'contextCompaction','id':'compact'}}})
        self.put({'method':'item/completed','params':{'threadId':'thread','turnId':'turn',
                  'item':{'type':'contextCompaction','id':'compact'}}})
        self.put({'method':'item/completed','params':{'threadId':'thread','turnId':'turn',
                  'item':{'type':'agentMessage','text':'Evidence-aware answer.'}}})
        self.put(self.terminal())
        # No elapsed-deadline calls in an unbounded wait; virtual jumps beyond
        # 420/1800 seconds must not cause return-to-stdin before these events.
        clock=[0]
        get=self.app._queue.get
        def advance(*args,**kwargs):
            clock[0]+=9000
            return get(*args,**kwargs)
        with patch('h3_harness_interactive_repl.time.monotonic',side_effect=lambda:clock[0]), \
             patch.object(self.app._queue,'get',side_effect=advance), \
             redirect_stdout(io.StringIO()) as printed:
            result=self.app._request_turn(start,timeout=self.app.turn_timeout)
        self.assertGreater(clock[0],1800)
        self.assertEqual(result,self.terminal())
        self.assertIn('Evidence-aware answer.',printed.getvalue())
        self.assertIsNone(self.app._pending_turn)
        self.assertFalse((self.root/'turn-lifecycle.jsonl').exists())
        self.assertEqual(self.app._send.call_count,1)

    def test_tool_request_is_dispatched_after_long_virtual_wait_not_only_final_text(self):
        start=self.start()
        tool={'id':501,'method':'item/tool/call','params':{'threadId':'thread','turnId':'turn','callId':'c','tool':'read_section','arguments':{}}}
        self.put(tool);self.put(self.terminal())
        with patch.object(self.app,'_handle_tool_call') as handle, \
             patch('h3_harness_interactive_repl.time.monotonic',side_effect=[0,9000,18000]),redirect_stdout(io.StringIO()):
            self.app._request_turn(start,timeout=None)
        handle.assert_called_once_with(tool)

    def test_explicit_finite_experiment_wait_still_retains_pending_identity(self):
        start=self.start()
        with patch('h3_harness_interactive_repl.time.monotonic',side_effect=[0,1000]),redirect_stdout(io.StringIO()):
            result=self.app._request_turn(start,timeout=420)
        self.assertIsNone(result);self.assertIsNotNone(self.app._pending_turn)
        self.assertIn('"event":"wait_timeout"',(self.root/'turn-lifecycle.jsonl').read_text())

    def test_ctrl_c_returns_controls_without_inventing_cancel_or_completion(self):
        before=deepcopy(self.app.semantic_state.snapshot('thread'))
        with patch.object(self.app,'_wait_for',side_effect=KeyboardInterrupt),redirect_stdout(io.StringIO()):
            result=self.app._request_turn({'id':99,'method':'turn/start'},timeout=None)
        self.assertIsNone(result);self.assertIsNotNone(self.app._pending_turn)
        self.assertEqual(before,self.app.semantic_state.snapshot('thread'))
        self.assertEqual(self.app._send.call_count,1)  # just start, no implicit grant/cancel
        self.assertIn('"event":"wait_interrupted"',(self.root/'turn-lifecycle.jsonl').read_text())

    def pending(self):
        self.app._pending_turn={'request_id':99,'turn_id':'turn','input_id':self.app.semantic_state.snapshot('thread')['current_input_id']}

    def test_idle_pump_completes_only_matching_turn_without_new_input(self):
        self.pending()
        self.put(self.terminal('foreign'));self.put(self.terminal())
        with redirect_stdout(io.StringIO()):self.app.poll_pending_turn()
        self.assertIsNone(self.app._pending_turn)
        self.app._send.assert_not_called()

    def test_idle_pump_no_unconfirmed_journal_spam(self):
        self.pending()
        self.app.poll_pending_turn();self.app.poll_pending_turn()
        self.assertIsNotNone(self.app._pending_turn)
        self.assertFalse((self.root/'turn-lifecycle.jsonl').exists())

    def test_native_user_reply_has_no_duration_deadline_and_still_requires_real_answer(self):
        seen=[]
        def answer(prompt,**kwargs):
            seen.append(kwargs['timeout'])
            kwargs['on_idle']()
            return 'Actual answer'
        with patch('h3_harness_interactive_repl.read_user_input',side_effect=answer), \
             patch('h3_harness_interactive_repl.time.monotonic',side_effect=[0,9000]),redirect_stdout(io.StringIO()):
            self.app._handle_message(question())
        self.assertEqual(seen,[None])
        self.assertEqual(self.app._send.call_args.args[0]['result']['answers']['scope']['answers'],['Actual answer'])
        events=[json.loads(l) for l in (self.root/'user-input-events.jsonl').read_text().splitlines()]
        self.assertTrue(all(not e['authorization_established'] for e in events))

    def test_dead_harness_breaks_unbounded_wait_not_model_service_lifetime(self):
        self.app.process=Mock();self.app.process.poll.return_value=1
        self.assertIsNone(self.app._wait_for(lambda x:False,None))
        with self.assertRaises(EOFError):self.app.poll_pending_turn()
        self.app._send.assert_not_called()

    def test_pending_turn_is_pumped_by_real_polled_stdin_until_input_arrives(self):
        self.pending();readfd,writefd=os.pipe();invoked=[]
        self.addCleanup(lambda:os.close(writefd))
        def idle():
            invoked.append(True)
            self.put(self.terminal())
            self.app.poll_pending_turn()
            os.write(writefd,b'/turn status\n')
        with os.fdopen(readfd,'r') as stream,patch('sys.stdin',stream),redirect_stdout(io.StringIO()):
            line=read_user_input('',on_idle=idle)
        self.assertEqual(line,'/turn status');self.assertTrue(invoked)
        self.assertIsNone(self.app._pending_turn)

    def test_resumed_wait_can_be_deliberately_interrupted_without_clearing_pending(self):
        self.pending()
        with patch.object(self.app,'_wait_for',side_effect=KeyboardInterrupt),redirect_stdout(io.StringIO()):
            self.app._control_turn('/turn wait')
        self.assertIsNotNone(self.app._pending_turn)
        self.app._send.assert_not_called()

    def test_cli_manual_defaults_and_explicit_finite_values(self):
        with patch('harness.version_manifest.current_platform',return_value='linux-aarch64'), \
             patch('harness.version_manifest.identify_harness',return_value={'build_target':'aarch64-unknown-linux-gnu'}):
            args=parse_args([])
            self.assertEqual((args.turn_timeout,args.user_input_timeout),(0,0))
            args=parse_args(['--turn-timeout','420','--user-input-timeout','300'])
            self.assertEqual((args.turn_timeout,args.user_input_timeout),(420,300))
            for flags in (['--turn-timeout','-1'],['--user-input-timeout','-1']):
                with redirect_stdout(io.StringIO()),patch('sys.stderr',io.StringIO()),self.assertRaises(SystemExit):
                    parse_args(flags)


class UnboundedBridgeTransportTests(unittest.TestCase):
    def test_actual_loopback_http_succeeds_with_no_socket_wait_deadline(self):
        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length','0')))
                body=b'data: {"type":"response.completed"}\n\n'
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers()
                self.wfile.write(body)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Provider)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                with ProviderHistoryBridge(f'http://127.0.0.1:{server.server_port}',journal_path=Path(tmp)/'journal',timeout=None) as bridge:
                    self.assertIsNone(bridge.timeout)
                    real_connection=http.client.HTTPConnection
                    conn=real_connection('127.0.0.1',int(bridge.base_url.rsplit(':',1)[1]),timeout=5)
                    observed={}
                    def upstream_connection(*args,**kwargs):
                        observed['connect_timeout']=kwargs.get('timeout')
                        upstream=real_connection(*args,**kwargs)
                        getresponse=upstream.getresponse
                        def response():
                            observed['read_timeout']=upstream.sock.gettimeout()
                            return getresponse()
                        upstream.getresponse=response
                        return upstream
                    try:
                        with patch('harness.responses_bridge.http.client.HTTPConnection',side_effect=upstream_connection):
                            conn.request('POST','/v1/responses',json.dumps({'input':[{'role':'user','content':'fixture'}]}),
                                         {'Content-Type':'application/json'})
                            response=conn.getresponse()
                            self.assertEqual(response.status,200)
                            self.assertIn(b'response.completed',response.read())
                        self.assertEqual(observed,{'connect_timeout':10,'read_timeout':None})
                    finally:conn.close()
        finally:server.shutdown();server.server_close();thread.join(5)


if __name__=='__main__':unittest.main()
