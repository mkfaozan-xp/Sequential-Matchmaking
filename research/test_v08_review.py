import copy,unittest
from unittest.mock import patch
from blackbox.ranking import contrasts,rank_names,project,heuristic_score
from blackbox.features import NAMES
from blackbox.compatibility import episode_cache,prepared,_CACHE
from blackbox.domain import eligibility
from blackbox.outcome_history import vector
from blackbox.model import LinearModel
from test_policy import feasible_state
import test_v06_outcomes as outcome_fixtures

class ReviewResponseTests(unittest.TestCase):
    def row(self,key,label,goal=False,excluded=False,day=0):
        x=[0.0]*len(NAMES)
        for k in ('relationship_goal','relationship_pace','lifestyle','conversations','emotional_availability','space_for_relationship','relocate'):
            x[NAMES.index(k+':missing')]=1
        for k,on in [('relationship_goal',goal),('emotional_availability',excluded)]:
            if on:x[NAMES.index(k+':agree')]=1;x[NAMES.index(k+':missing')]=0
        return dict(row_id=key,label=label,auxiliary_label=label,seed=1101,variant='development',assigned_day=day,x=x)
    def test_matching_uses_actual_seven_fields_and_retains_mirrors(self):
        yes=self.row('p',1,goal=True);wrong=self.row('wrong',0);right=self.row('n',0,excluded=True)
        self.assertEqual(heuristic_score(yes['x']),heuristic_score(right['x']))
        c=contrasts([yes,wrong,right]);self.assertEqual(len(c),2)
        self.assertTrue(all(p['negative_row_id']=='n' for p in c))
        self.assertTrue(all(p['positive_heuristic_score']==p['negative_heuristic_score'] for p in c))
        self.assertEqual(c[0]['x'],[-x for x in c[1]['x']])
    def test_legacy_control_can_compare_cross_score_without_changing_default(self):
        rows=[self.row('p',1,goal=True),self.row('n',0)]
        self.assertEqual(contrasts(rows),[]);self.assertEqual(len(contrasts(rows,same_score=False)),2)
    def test_reference_dimensions_and_nohistory_isolation(self):
        self.assertEqual([len(rank_names(p)) for p in ['full','reference','reference_nohistory']],[36,32,16])
        x=self.row('a',0)['x'];y=x[:]
        for i,n in enumerate(NAMES):
            if n.startswith('outcome:'):y[i]=.7
        self.assertEqual(project(x,'reference_nohistory'),project(y,'reference_nohistory'))
        self.assertNotEqual(project(x,'reference'),project(y,'reference'))
        with self.assertRaises(ValueError):project(x,'unknown')
    def test_reference_reparameterization_preserves_missing_preference(self):
        w={'agree':.22123972453773358,'disagree':-.6117973913285518,'missing':.39054885517053}
        reference={s:w[s]-w['missing'] for s in ('agree','disagree')}
        for s in w:self.assertAlmostEqual(w[s],w['missing']+reference.get(s,0))
        self.assertLess(reference['agree'],0) # Coding alone cannot impose monotonicity.
    def test_history_translation_cancels_and_half_rate_is_not_no_date(self):
        yes=vector('p',{'p':{'yes':1,'answered':1,'dates':1,'date_records':1}})
        no=vector('p',{'p':{'yes':0,'answered':1,'dates':1,'date_records':1}})
        self.assertAlmostEqual((yes[0]-.15)-(no[0]-.15),yes[0]-no[0])
        unanswered=vector('p',{'p':{'yes':0,'answered':0,'dates':1,'date_records':1}})
        self.assertEqual(unanswered[0],.5);self.assertGreater(unanswered[6],0)
    def test_each_projected_asset_validates_its_actual_schema(self):
        artifact=outcome_fixtures.OutcomeTests().artifact()
        for head,projection in [('rank_reference','reference'),('rank_nohistory','reference_nohistory')]:
            names=rank_names(projection)
            artifact[head]={'basis':'identity','ranking_projection':projection,'feature_names':names,'weights':[0.0]*len(names),'intercept':0}
        LinearModel(artifact)
        artifact['rank_reference']['ranking_projection']='full'
        with self.assertRaises(ValueError):LinearModel(artifact)

class CompatibilityCacheTests(unittest.TestCase):
    def test_cold_path_is_original_function(self):
        self.assertIs(prepared(feasible_state()['members']),eligibility)
    def test_cached_result_cannot_be_mutated_by_caller(self):
        members=feasible_state()['members'];a,b=members[:2]
        with episode_cache():
            check=prepared(members);expected=eligibility(a,b);result=check(a,b);result['reasons'].append('invented');result['status']='invented'
            with patch('blackbox.compatibility.eligibility',side_effect=AssertionError('expected cache hit')):self.assertEqual(check(a,b),expected)
        self.assertIsNone(_CACHE.get())
    def test_updated_constraints_and_public_member_values_invalidate(self):
        base=feasible_state()['members'][:2]
        changes=[lambda b:b.update(age=17),lambda b:b.update(pool_id='other'),lambda b:b.update(zone='other'),
            lambda b:b['fields'].update(schedule=[]),lambda b:b['fields'].update(wants_children='yes'),
            lambda b:b['fields'].update(age_min=None)]
        with episode_cache():
            prepared(base)(*base)
            for change in changes:
                members=copy.deepcopy(base);change(members[1]);self.assertEqual(prepared(members)(*members),eligibility(*members))
    def test_reversed_pair_preserves_ordered_missing_ids_and_bound(self):
        members=feasible_state()['members'][:2];members[0]['fields']['age_min']=None;members[1]['fields']['age_max']=None
        with episode_cache(limit=1):
            check=prepared(members)
            for a,b in [members,members[::-1],members]:
                self.assertEqual(check(a,b),eligibility(a,b));self.assertLessEqual(len(_CACHE.get()[0]),1)
        with self.assertRaises(ValueError):
            with episode_cache(limit=20001):pass
        with episode_cache():
            with self.assertRaises(ValueError):
                with episode_cache():pass

if __name__=='__main__':unittest.main()
