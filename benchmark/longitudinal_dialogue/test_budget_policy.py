import unittest
from budget_policy import BudgetPolicy, BudgetConfig


class Clock:
    def __init__(self): self.t=0
    def __call__(self): return self.t
    def advance(self,n): self.t+=n


class BudgetTests(unittest.TestCase):
    def make(self, soft=10, hard=30, idle=15, requests=2):
        self.c=Clock()
        return BudgetPolicy(BudgetConfig(soft,hard,idle,requests),clock=self.c)

    def test_soft_real_progress_continues_same_turn(self):
        b=self.make()
        b.begin_request("r1")
        self.c.advance(9)
        self.assertTrue(b.note_progress("output_delta","r1:1","new text"))
        self.c.advance(2)
        d=b.evaluate()
        self.assertEqual(d.action,"continue")
        self.assertEqual(d.reason,"soft_budget_progress_continuation")
        self.assertEqual(d.request_count,1)

    def test_heartbeat_does_not_extend(self):
        b=self.make()
        for i in range(15):
            self.c.advance(1)
            self.assertFalse(b.note_progress("heartbeat",str(i),"alive"))
        self.assertEqual(b.evaluate().reason,"no_progress_limit")

    def test_duplicate_progress_does_not_extend(self):
        b=self.make()
        b.note_progress("tool_result","call1",{"text":"source"})
        self.c.advance(10)
        self.assertFalse(b.note_progress("tool_result","call1",{"text":"source"}))
        self.c.advance(5)
        self.assertEqual(b.evaluate().reason,"no_progress_limit")

    def test_conflicting_progress_identity_rejected(self):
        b=self.make()
        b.note_progress("tool_result","call1",{"text":"source"})
        with self.assertRaises(ValueError):
            b.note_progress("tool_result","call1",{"text":"changed"})

    def test_hard_stops_despite_fresh_progress(self):
        b=self.make()
        self.c.advance(29)
        b.note_progress("output_delta","r1:1","fresh")
        self.c.advance(1)
        self.assertEqual(b.evaluate().reason,"hard_time_limit")

    def test_guard_wins_completed_and_progress(self):
        b=self.make()
        b.note_progress("tool_result","call1",{"x":1})
        self.assertEqual(b.evaluate(completed=True,guard_failure="stale").status,"safety_stop")

    def test_native_completion_wins_budget_poll(self):
        b=self.make()
        self.c.advance(31)
        self.assertEqual(b.evaluate(completed=True).status,"completed")

    def test_request_cap_does_not_abort_inflight(self):
        b=self.make()
        self.assertTrue(b.begin_request("r1").request_allowed)
        self.assertTrue(b.begin_request("r2").request_allowed)
        self.assertEqual(b.evaluate().action,"continue")
        self.assertEqual(b.begin_request("r3").reason,"request_limit")
        self.assertEqual(len(b.request_ids),2)

    def test_completed_wins_request_cap(self):
        b=self.make()
        b.begin_request("r1");b.begin_request("r2")
        self.assertEqual(b.evaluate(completed=True,request_requested=True).status,"completed")

    def test_duplicate_request_never_admitted(self):
        b=self.make()
        self.assertTrue(b.begin_request("r1").request_allowed)
        d=b.begin_request("r1")
        self.assertEqual(d.action,"observe_only")
        self.assertFalse(d.request_allowed)
        self.assertEqual(d.request_count,1)

    def test_wait_timeout_is_not_a_failure_input(self):
        b=self.make()
        self.c.advance(11)
        self.assertEqual(b.evaluate().status,"running")
        self.assertIsNone(b.snapshot()["terminal"])

    def test_fault_external_and_budget_separate(self):
        b=self.make()
        self.assertEqual(b.evaluate(execution_failure="bridge").status,"execution_fault")
        b=self.make()
        self.assertEqual(b.evaluate(external_interrupt="operator").status,"external_interruption")
        b=self.make()
        self.c.advance(16)
        self.assertEqual(b.evaluate().status,"budget_stop")

    def test_terminal_sticky_no_new_request(self):
        b=self.make();b.evaluate(completed=True)
        self.assertEqual(b.begin_request("r1").status,"completed")
        self.assertEqual(len(b.request_ids),0)

    def test_guard_after_terminal_preserves_first_cause(self):
        b=self.make();b.evaluate(completed=True)
        self.assertEqual(b.evaluate(guard_failure="unsafe").status,"safety_stop")
        self.assertEqual(b.first_terminal.status,"completed")

    def test_empty_payload_not_progress(self):
        b=self.make()
        self.assertFalse(b.note_progress("output_delta","x",""))
        self.assertEqual(b.progress_count,0)

    def test_thread_safe_request_budget(self):
        from concurrent.futures import ThreadPoolExecutor
        b=self.make(requests=6)
        with ThreadPoolExecutor(max_workers=4) as pool:
            ds=list(pool.map(b.begin_request, [str(i) for i in range(20)]))
        self.assertEqual(sum(d.request_allowed for d in ds),6)
        self.assertEqual(len(b.request_ids),6)

    def test_soft_wait_without_progress_is_not_claimed_progress(self):
        b=self.make()
        self.c.advance(11)
        self.assertEqual(b.evaluate().reason,"soft_budget_waiting_within_idle_limit")
        self.assertEqual(b.evaluate().progress_count,0)

    def test_invalid_config(self):
        for c in [(20,10,10,1),(1,10,10,0),(1,float("inf"),10,1),(True,10,10,1)]:
            with self.assertRaises(ValueError): BudgetConfig(*c)

    def test_backwards_clock_rejected(self):
        b=self.make();self.c.t=-1
        with self.assertRaises(ValueError): b.evaluate()


if __name__=="__main__": unittest.main()
