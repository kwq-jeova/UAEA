import unittest, copy, math
from s1_shadow import Filter, Observation, transition, as_of, confusion, Exceptions

def obs(kind='D',polarity='-',targets=('Intel',),unit='original:user:1',scope='research'):
    return Observation(unit,kind,targets,polarity,'unmarked','SIM user quote',scope)

class MathTests(unittest.TestCase):
    def test_T1_negative_relative_to_predictive_prior(self):
        f=Filter(['Intel','AMD'],'research');f.b=[.1,.8,.05,.05]
        prior=f.b[1];self.assertLess(f.update(obs())[1],prior)

    def test_T1_not_universal_monotonic_across_transition(self):
        f=Filter(['Intel','AMD'],'research');f.b=[.8,.000001,.099999,.1]
        t=transition(f.states,.05);pred=sum(f.b[i]*t[i][1]for i in range(4))
        post=f.update(obs(),True)[1]
        self.assertGreater(post,.000001);self.assertLess(post,pred)

    def test_T2_X_freezes_even_boundary(self):
        f=Filter(['Intel'],'research');old=f.b[:]
        self.assertEqual(f.update(obs('X','0',()),True),old)

    def test_T5_unresolved_exception_cannot_be_created(self):
        with self.assertRaises(ValueError):Exceptions().add('x','','roa','u1')

    def test_T6_bounded_observation(self):
        for k in range(1,4):
            f=Filter(['H'+str(i+1)for i in range(k)],'research')
            b=f.update(obs('D','+',('H1',)))
            self.assertTrue(all(0<x<1 for x in b));self.assertAlmostEqual(sum(b),1)

    def test_T7_future_candidate(self):
        with self.assertRaisesRegex(ValueError,'FUTURE'):
            as_of([{'id':'future','source_id':'u1','available_at':3}],2)

    def test_T7_future_source(self):
        with self.assertRaises(ValueError):
            as_of([{'id':'candidate','source_id':'u1','available_at':1},
                   {'id':'u1','source_id':'raw','available_at':3}],2)

    def test_transition_rows_and_stay(self):
        for k in range(4):
            for h in (0,.01,.05,.9):
                states=['H0',*['H'+str(i+1)for i in range(k)],'HU']
                for i,row in enumerate(transition(states,h)):
                    self.assertAlmostEqual(sum(row),1);self.assertAlmostEqual(row[i],1-h)
                    self.assertTrue(all(x>=0 for x in row))

    def test_eta_invalid(self):
        for x in (0,.04,.5,.9,float('nan')):
            with self.assertRaises(ValueError):Filter(['Intel'],'r',eta=x)

    def test_duplicate_has_no_transition(self):
        f=Filter(['Intel'],'research');f.update(obs());old=f.b[:]
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):f.update(obs(),True)
        self.assertEqual(old,f.b)

    def test_wrong_scope_atomic(self):
        f=Filter(['Intel'],'research');old=f.b[:]
        with self.assertRaises(ValueError):f.update(obs(scope='other'))
        self.assertEqual(old,f.b);self.assertFalse(f.seen)

    def test_negative_R_atomic(self):
        f=Filter(['Intel'],'research');old=f.b[:]
        with self.assertRaises(ValueError):f.update(obs('R'))
        self.assertEqual(old,f.b);self.assertFalse(f.seen)

    def test_C_flat_does_not_repair_wrong_interpretation(self):
        f=Filter(['Intel','Method'],'research');f.b=[.01,.95,.02,.02]
        f.update(obs('C','+',('Method',)))
        self.assertGreater(f.b[1],f.b[2]) # Documents a structural limitation, NOT desired cognition.

    def test_N_drift_is_transition_not_evidence(self):
        f=Filter(['Intel'],'research');old=f.b[:]
        self.assertNotEqual(f.update(obs('N','0',())),old)

    def test_zero_candidates(self):
        f=Filter([],'research');self.assertEqual(f.states,['H0','HU'])
        self.assertAlmostEqual(sum(f.update(obs('N','0',()))),1)

    def test_asof_generator_and_bad_time(self):
        row={'id':'a','source_id':'u','available_at':1}
        self.assertEqual(as_of(iter([row]),1),[row])
        for x in (float('nan'),float('inf'),True,'tomorrow'):
            with self.assertRaises(ValueError):as_of([row],x)
            with self.assertRaises(ValueError):as_of([{**row,'available_at':x}],2)

    def test_confusion_direction_and_support(self):
        c=confusion([('D','X'),('D','D')]);self.assertEqual(c['counts'][0][1],1)
        self.assertEqual(c['row_support'],[2,0,0,0,0]);self.assertAlmostEqual(sum(c['probabilities'][0]),1)

class ExceptionTests(unittest.TestCase):
    def fresh(self):
        e=Exceptions();e.add('x','AMD','compute_roa','u1');return e

    def test_T3_missing_handoff(self):
        e=self.fresh();v,h=e.snapshot()
        with self.assertRaises(ValueError):Exceptions.restore([],h,['x'])

    def test_T4_used_again(self):
        e=self.fresh();e.start('x','AMD','compute_roa','call1')
        e.finish_use('x','call1',True,'answer1')
        with self.assertRaises(ValueError):e.start('x','AMD','compute_roa','call2')

    def test_same_call_replay(self):
        e=self.fresh();e.start('x','AMD','compute_roa','call1')
        e.finish_use('x','call1',True,'answer1');self.assertFalse(e.start('x','AMD','compute_roa','call1'))

    def test_unused_expires_at_scope_end(self):
        e=self.fresh();e.end_scope('AMD');self.assertEqual(e.records['x'].status,'expired')
        with self.assertRaises(ValueError):e.start('x','AMD','compute_roa','call2')

    def test_plan_is_not_success(self):
        e=self.fresh();e.start('x','AMD','compute_roa','call1')
        with self.assertRaises(ValueError):e.finish_use('x','call1',False,'failed')
        e.end_scope('AMD');self.assertEqual(e.records['x'].status,'expired')

    def test_restart_retains_consumption(self):
        e=self.fresh();e.start('x','AMD','compute_roa','call1');e.finish_use('x','call1',True,'answer1')
        v,h=e.snapshot();e=Exceptions.restore(v,h,['x']);self.assertEqual(e.records['x'].status,'consumed')
        with self.assertRaises(ValueError):e.start('x','NVIDIA','compute_roa','new')

    def test_corruption_or_wrong_action(self):
        e=self.fresh();v,h=e.snapshot();v[0]['scope']='NVIDIA'
        with self.assertRaises(ValueError):Exceptions.restore(v,h,['x'])
        with self.assertRaises(ValueError):e.start('x','AMD','trade','call1')

    def test_ambiguous_state_is_not_long_term_goal(self):
        f=Filter(['Intel'],'research');e=self.fresh();v,h=e.snapshot()
        e=Exceptions.restore(v,h,['x']);self.assertEqual(f.b,[.8,.15,.05])

if __name__=='__main__':unittest.main(verbosity=2)
