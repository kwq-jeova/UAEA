import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from h3_harness_interactive_repl import InteractiveAppServer
from tests.test_contract_convergence import setup_host

class TurnCorrelationTests(unittest.TestCase):
    def run_case(self,events, *, expect_terminal=True):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);adapter,semantic,_=setup_host(root/"workspace")
            app=InteractiveAppServer(codex=Path("/not-started"),codex_home=root/"home",
                workspace=root/"workspace",base_url="http://127.0.0.1:8003",adapter=adapter,
                events_path=root/"raw.jsonl",stderr_path=root/"stderr",turn_timeout=1)
            app.thread_id="t";app.semantic_state=semantic;app._send=lambda message:None
            semantic.prepare_turn("t","A new user request",turn_id="")
            for e in events:app._queue.put(("stdout",json.dumps(e)))
            with app.events_path.open("w") as f:
                app._events_file=f
                got=app._request_turn({"id":99,"method":"turn/start","params":{"threadId":"t"}},timeout=.1)
            if expect_terminal:self.assertEqual(got["params"]["turn"]["id"],"new")
            else:self.assertIsNone(got)
            snap=semantic.snapshot("t")
            self.assertEqual(snap["completed_turn_count"],1 if expect_terminal else 0)
            receipt_ids=[x["turn_id"] for x in snap["workflow_continuity"]["turn_receipts"]]
            self.assertNotIn("old",receipt_ids)
            path=root/"turn-correlation.jsonl"
            records=[json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
            return got,records

    def test_old_compaction_completion_before_ack_cannot_finish_or_expire_new_request(self):
        _,rows=self.run_case([
            {"method":"turn/completed","params":{"threadId":"t","turn":{"id":"old","status":"completed"}}},
            {"id":99,"result":{"turn":{"id":"new"}}},
            {"method":"turn/started","params":{"threadId":"t","turn":{"id":"new","status":"inProgress"}}},
            {"method":"turn/completed","params":{"threadId":"t","turn":{"id":"new","status":"completed"}}}])
        self.assertEqual(rows[0]["observed_turn_id"],"old")
        self.assertFalse(rows[0]["semantic_state_updated"])

    def test_foreign_terminal_after_ack_does_not_match_active_turn(self):
        _,rows=self.run_case([
            {"id":99,"result":{"turn":{"id":"new"}}},
            {"method":"turn/completed","params":{"threadId":"t","turn":{"id":"old","status":"completed"}}},
            {"method":"turn/completed","params":{"threadId":"t","turn":{"id":"new","status":"completed"}}}])
        self.assertEqual(rows[0]["expected_turn_id"],"new")

    def test_completion_without_ack_is_not_a_success(self):
        self.run_case([{"method":"turn/completed","params":{"threadId":"t","turn":{"id":"old","status":"completed"}}}],
                      expect_terminal=False)
