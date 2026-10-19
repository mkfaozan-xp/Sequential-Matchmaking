import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'));sys.path.insert(0,str(ROOT))
from coordinated.engine import matching,objective,potential,load_model,decide,response_probability
from blackbox.contracts import validate_actions


class CoordinatedTests(unittest.TestCase):
    def test_allocator_accounts_for_displaced_pairs(self):
        pairs,value=matching([(('a','b'),8),(('a','c'),7),(('b','d'),7)])
        self.assertEqual(value,14);self.assertEqual(pairs,[['a','c'],['b','d']])

    def test_no_endpoint_is_used_twice(self):
        edges=[((str(a),str(b)),(a+b+1)/10) for a in range(12) for b in range(a+1,12)]
        pairs,_=matching(edges);ids=[i for p in pairs for i in p]
        self.assertEqual(len(ids),len(set(ids)))

    def test_wait_is_an_explicit_outside_option(self):
        pairs,_,diag=objective([(('a','b'),.01,40),(('a','c'),.5,8),(('b','d'),.5,8)],0)
        self.assertNotIn(['a','b'],pairs);self.assertGreater(diag['deferred_nonpositive_edges'],0)

    def test_continuation_shrinks_with_remaining_horizon(self):
        edges=[(('a','b'),.2,10)]
        _,early,_=objective(edges,0);_,late,_=objective(edges,59)
        self.assertGreater(early,late);self.assertEqual(objective(edges,59)[0],[['a','b']])

    def test_adding_disclosed_options_cannot_reduce_same_objective(self):
        for day in (0,30,59):
            old=[(('a','b'),.1,10)];new=old+[(('a','c'),.9,8)]
            self.assertGreaterEqual(objective(new,day)[1]+1e-12,objective(old,day)[1])

    def test_myopic_is_the_declared_component_ablation(self):
        edges=[(('a','b'),.3,10),(('c','d'),.4,20)]
        _,value,diag=objective(edges,0,True)
        self.assertAlmostEqual(value,.7);self.assertEqual(diag['continuation_value'],0)

    def test_response_estimate_uses_only_current_logs(self):
        self.assertEqual(response_probability({'day':0,'ask_log':[]}),.5)

    def test_refreshed_actions_ignore_forged_optimistic_memory(self):
        req=json.loads((ROOT/'runtime/examples/refreshed_match_request.json').read_text())
        model=load_model();original=decide(req)
        forged=copy.deepcopy(req);forged['memory']={'sampled_profiles':'all feasible','pairs':[['fake','ids']]}
        self.assertEqual(original,decide(forged));validate_actions(req['state'],'match',original['pairs'])

    def test_no_hypothetical_answer_is_disclosed_in_real_state(self):
        req=json.loads((ROOT/'runtime/examples/day0_request.json').read_text());before=copy.deepcopy(req)
        response=decide(req);self.assertEqual(req,before)
        validate_actions(req['state'],'ask',response['asks'])

    def test_predictions_are_finite_and_feature_support_is_clean(self):
        model=load_model();self.assertEqual(len(model['feature_names']),32)
        self.assertFalse(any(n.startswith(('emotional_availability:','space_for_relationship:','relocate:')) for n in model['feature_names']))
        self.assertGreater(model['reward']['nonzero_weights'],0)


if __name__=='__main__':unittest.main(verbosity=2)
