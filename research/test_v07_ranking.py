import copy,unittest,math
from unittest.mock import patch
from blackbox.ranking import project,contrasts,RANK_NAMES
from blackbox.features import NAMES
from blackbox.fitting import fit
from blackbox.model import LinearModel
import test_v06_outcomes as fixtures

class RankingTests(unittest.TestCase):
    def row(self,key,label,seed=1101,variant='development',day=0):
        x=[0.0]*len(NAMES);x[NAMES.index('relationship_goal:agree')]=float(label);x[NAMES.index('emotional_availability:agree')]=float(1-label)
        return dict(row_id=key,label=label,auxiliary_label=label,seed=seed,variant=variant,assigned_day=day,x=x)
    def test_projection_ignores_distractor_and_category_changes(self):
        a=[0.0]*len(NAMES);b=[float(any(k in n for k in ('emotional_availability','space_for_relationship','relocate')) or ':count:' in n) for n in NAMES]
        self.assertEqual(project(a),project(b));self.assertEqual(len(RANK_NAMES),36)
    def test_contrasts_preserve_world_time_and_mirror(self):
        rows=[self.row('yes',1),self.row('near',0,day=7),self.row('far',0,day=8),self.row('other',0,seed=1102),self.row('family',0,variant='shift')]
        c=contrasts(rows);self.assertEqual(len(c),2)
        self.assertTrue(all(r['negative_row_id']=='near' for r in c));self.assertEqual(c[0]['x'],[-v for v in c[1]['x']]);self.assertEqual({r['label'] for r in c},{0,1})
    def test_old_vectors_and_unmatured_labels_rejected(self):
        r=self.row('a',1);r['x']=r['x'][:49]
        with self.assertRaises(ValueError):contrasts([r])
        r=self.row('a',1);r['label']=None
        with self.assertRaises(ValueError):contrasts([r])
    def test_rank_fit_recovers_relative_signal_without_probability_claim(self):
        rows=[]
        for seed in range(1101,1105):rows.extend([self.row(str(seed)+'p',1,seed),self.row(str(seed)+'n',0,seed)])
        h=fit(contrasts(rows),RANK_NAMES,l2=1,l1=0)
        self.assertGreater(h['weights'][RANK_NAMES.index('relationship_goal:agree')],0)
        self.assertLess(h['kkt_max_per_row'],1e-4)
    def test_rank_asset_rejects_nonfinite_or_wrong_projection(self):
        a=fixtures.OutcomeTests().artifact();a['rank_official']={'basis':'identity','feature_names':RANK_NAMES,'weights':[0.0]*len(RANK_NAMES),'intercept':0}
        a['rank_official']['weights'][0]=float('nan')
        with self.assertRaises(ValueError):LinearModel(a)
        a['rank_official']['weights'][0]=0;a['rank_official']['feature_names']=RANK_NAMES[::-1]
        with self.assertRaises(ValueError):LinearModel(a)
    def test_constant_ranker_skips_feature_work_without_changing_score(self):
        from test_policy import feasible_state
        from blackbox.model import score_pair
        s=feasible_state();a,b=s['members'][:2];artifact=fixtures.OutcomeTests().artifact()
        artifact['rank_official']={'basis':'identity','feature_names':RANK_NAMES,'weights':[0.0]*len(RANK_NAMES),'intercept':0}
        model=LinearModel(artifact)
        with patch('blackbox.model.pair_features',side_effect=AssertionError('constant does not need features')):
            value=score_pair(a,b,s,'rank_tie',model)
        self.assertEqual(value,score_pair(a,b,s,'soft')+.125)

    def test_ranking_selection_rejects_partial_or_wrong_pilot(self):
        from scripts.select_candidate import choose_ranking
        with self.assertRaises(ValueError):choose_ranking({'complete':False})


class SnapshotTests(unittest.TestCase):
    def test_snapshot_matches_uncached_actions_and_skips_repeated_disk_reads(self):
        from blackbox.registry import verified_episode_snapshot,identity,selected,episode_model
        from blackbox.policy import decide
        from test_policy import feasible_state
        import blackbox.registry as registry
        request={'schema_version':'1.0.0','phase':'match','state':feasible_state(),'memory':None}
        expected=identity();cold=decide(copy.deepcopy(request),'conservative')
        with verified_episode_snapshot(expected):
            with patch.object(registry,'sha',side_effect=AssertionError('no repeated asset reads')):
                self.assertEqual(identity(),expected)
                self.assertEqual(decide(copy.deepcopy(request),'conservative'),cold)
                self.assertIsNotNone(episode_model())
        self.assertIsNone(episode_model())
        with patch.object(registry,'sha',side_effect=ValueError('disk check restored')):
            with self.assertRaises(ValueError):selected()
    def test_snapshot_rejects_wrong_subject_and_nested_scope(self):
        from blackbox.registry import verified_episode_snapshot,identity
        with self.assertRaises(ValueError):
            with verified_episode_snapshot({'wrong':'subject'}):pass
        with verified_episode_snapshot(identity()):
            with self.assertRaises(ValueError):
                with verified_episode_snapshot():pass

if __name__=='__main__':unittest.main()
