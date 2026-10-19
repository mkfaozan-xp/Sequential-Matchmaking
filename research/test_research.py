import copy
import unittest
from blackbox.clarification import pruned,soft_fill,sampled_asks
from blackbox.contracts import validate_actions
from blackbox.domain import SOFT
from blackbox.policy import MODES
from test_policy import feasible_state


class ResearchTests(unittest.TestCase):
    def test_calibration_is_pooled_by_bin_before_ece(self):
        from scripts.research_analysis import pooled_calibration
        from blackbox.metrics import calibration
        result=pooled_calibration([calibration([{'prediction':.11,'label':0}]),calibration([{'prediction':.12,'label':1}])])
        self.assertEqual(result['n'],2)
        self.assertAlmostEqual(result['ece'],.385)
        self.assertAlmostEqual(result['brier'],(.11**2+.88**2)/2)

    def test_soft_fill_keeps_hard_priority_and_never_reads_new_answers(self):
        state=feasible_state()
        for member in state['members'][:2]:
            member['fields']['schedule']=None;member['field_status']['schedule']='not_asked';member['field_observed_day']['schedule']=None
        before=copy.deepcopy(state);hard=pruned(state);asks,diag=soft_fill(state)
        self.assertEqual(asks[:len(hard)],hard)
        self.assertEqual(state,before)
        self.assertGreater(diag['soft_asks'],0)
        validate_actions(state,'ask',asks)

    def test_soft_fill_respects_refusals_and_deduplicates_pair_endpoints(self):
        state=feasible_state()
        state['members'][0]['field_status'][SOFT[0]]='declined'
        asks,_=soft_fill(state)
        self.assertNotIn({'member_id':state['members'][0]['member_id'],'field':SOFT[0]},asks)
        self.assertEqual(len(asks),len({(a['member_id'],a['field']) for a in asks}))
        validate_actions(state,'ask',asks)

    def test_fully_spent_hard_budget_leaves_zero_soft_asks(self):
        state=feasible_state()
        for member in state['members']:
            member['fields']['schedule']=None;member['field_status']['schedule']='not_asked';member['field_observed_day']['schedule']=None
        asks,diag=soft_fill(state)
        self.assertEqual(len(asks),4);self.assertEqual(diag['soft_asks'],0)
        self.assertTrue(all(a['field']=='constraints' for a in asks))

    def test_pair_and_single_search_have_equal_completed_hypothetical_work(self):
        state=feasible_state()
        for member in state['members'][:2]:
            member['fields']['schedule']=None;member['field_status']['schedule']='not_asked';member['field_observed_day']['schedule']=None
        for pair_seeds in (False,True):
            asks,diag=sampled_asks(state,score='constant',pair_seeds=pair_seeds,seconds=10,max_batches=2,samples=2,pad_batches=True)
            self.assertFalse(diag['fallback']);self.assertEqual(diag['hypothetical_solves'],4)
            self.assertEqual(len(asks),len(pruned(state)))
            validate_actions(state,'ask',asks)

    def test_factorial_changes_only_asking_and_matching(self):
        modes=[MODES[m] for m in ('learned','learned_global','study_pair_greedy','study_pair_global')]
        self.assertEqual({m[1] for m in modes},{'learned'})
        self.assertEqual({(m[0],m[2]) for m in modes},{('pruned','greedy'),('pruned','milp'),('study_pair','greedy'),('study_pair','milp')})

if __name__=='__main__':unittest.main()
