import unittest
from s1_parts import Allowance,contradictions,revision_keyword
class PartsTests(unittest.TestCase):
 def test_recalculation_not_new_budget(self):
  a=Allowance({'AMD'},'explicit-N','本次',1)
  self.assertTrue(a.use('AMD','ROA','v1'));self.assertTrue(a.use('AMD','ROA','v1'))
  self.assertEqual(len(a.seen),1);self.assertFalse(a.use('AMD','ROA','v2'))
 def test_different_object(self):
  a=Allowance({'AMD'});self.assertFalse(a.use('NVIDIA','ROA','v1'))
 def test_close_slot_keep_history(self):
  a=Allowance({'AMD'},time_scope='本次');a.use('AMD','ROA','v1');a.end_task()
  self.assertIsNone(a.task_focus);self.assertTrue(a.history);self.assertFalse(a.use('AMD','ROA','v1'))
 def test_future_scope_persists(self):
  a=Allowance({'AMD'},time_scope='今后');a.end_task();self.assertTrue(a.use('AMD','ROA','v1'))
 def test_explicit_withdraw(self):
  a=Allowance({'AMD'},'until-corrected');a.withdraw();self.assertFalse(a.use('AMD','ROA','v1'))
 def test_unresolved_scope(self):
  with self.assertRaises(ValueError):Allowance(set())
 def test_same_identity_new_purpose_limitation(self):
  a=Allowance({'AMD'});a.use('AMD','ROA','v1')
  self.assertTrue(a.use('AMD','ROA','v1','different deliverable')) # Explicit counterexample, not semantic correctness.
 def test_known_shape_positive(self):
  self.assertTrue(contradictions('NVIDIA本轮不执行ROA。NVIDIA的ROA约18.7%。'))
 def test_other_object_negative(self):
  self.assertFalse(contradictions('NVIDIA本轮不执行ROA。AMD的ROA约2.6%。'))
 def test_hard_negative_limitations(self):
  self.assertTrue(contradictions('NVIDIA未计算ROA，不能据此说ROA为0%。'))
 def test_keyword_frozen(self):
  self.assertEqual(revision_keyword('我一直投资，从现在起不再投资'),'misunderstanding_correction') # Known simple baseline error.
if __name__=='__main__':unittest.main(verbosity=2)
