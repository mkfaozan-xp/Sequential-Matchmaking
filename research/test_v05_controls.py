import copy,math,tempfile,unittest
from pathlib import Path
from blackbox.basis import lift,lifted_names
from blackbox.features import NAMES,pair_features
from blackbox.metrics import ranking
from blackbox.runtime import runtime_info
from blackbox.seeds import reserve
from blackbox.model import score_pair
from blackbox.allocation import uniform_matching
from test_policy import feasible_state

class RevisionControls(unittest.TestCase):
    def test_nonlinear_lift_is_symmetric_bounded_and_keeps_base_features(self):
        s=feasible_state();a,b=s['members'][:2]
        a['fields']['relationship_goal']=b['fields']['relationship_goal']='long_term'
        x=pair_features(a,b,s);y=pair_features(b,a,s)
        self.assertEqual(lift(x,NAMES,'interactions_v1'),lift(y,NAMES,'interactions_v1'))
        self.assertEqual(lift(x,NAMES,'interactions_v1')[:len(x)],x)
        self.assertEqual(len(lift(x,NAMES,'interactions_v1')),len(lifted_names(NAMES,'interactions_v1')))
    def test_tie_aware_ranking_and_constant_comparator(self):
        rows=[{'prediction':.01,'label':int(i%5==0)} for i in range(20)]
        r=ranking(rows);self.assertEqual(r['auc'],.5);self.assertAlmostEqual(r['average_precision'],.2)
        self.assertAlmostEqual(r['top_decile_lift'],1)
        perfect=[{'prediction':.02 if r['label'] else .01,'label':r['label']} for r in rows]
        self.assertEqual(ranking(perfect)['auc'],1)
        self.assertEqual(ranking(perfect)['average_precision'],1)
    def test_nonlinear_json_export_and_basis_integrity(self):
        import hashlib
        from blackbox.features import DIRECTION_NAMES,FEATURE_VERSION
        from blackbox.model import LinearModel,sigmoid
        from blackbox import basis
        names=lifted_names(NAMES,'interactions_v1');weights=[0.0]*len(names);weights[len(NAMES)]=1
        artifact={'feature_version':FEATURE_VERSION,'model_id':'fixture',
            'basis_source_sha256':hashlib.sha256(Path(basis.__file__).read_bytes()).hexdigest(),
            'joint':{'basis':'interactions_v1','feature_names':names,'weights':weights,'intercept':0},
            'direction':{'feature_names':DIRECTION_NAMES,'weights':[0.0]*len(DIRECTION_NAMES),'intercept':0}}
        x=[0.0]*len(NAMES)
        for i,name in enumerate(NAMES):
            if name.endswith(':agree'):x[i]=1
        self.assertAlmostEqual(LinearModel(artifact).predict(x),sigmoid(1))
        artifact['basis_source_sha256']='0'*64
        with self.assertRaises(ValueError):LinearModel(artifact)
    def test_base_digest_is_resolved_and_matched(self):
        from unittest.mock import patch
        from blackbox.docker_base import resolve
        import json
        digest='python@sha256:'+'a'*64
        meta={'Id':'sha256:'+'b'*64,'RepoDigests':[digest]}
        with patch('blackbox.docker_base.subprocess.check_output',return_value=json.dumps([meta])):
            self.assertEqual(resolve('python:tag')['registry_digest'],digest)
        with patch('blackbox.docker_base.subprocess.check_output',side_effect=[json.dumps([meta]),json.dumps([dict(meta,Id='sha256:bad')])]):
            with self.assertRaises(ValueError):resolve('python:tag')
    def test_newer_runtime_is_recorded_instead_of_silently_certified(self):
        self.assertFalse(runtime_info((3,14,0))['reference_runtime'])
        with self.assertRaises(ValueError):runtime_info((3,11,9))
    def test_spent_final_seeds_cannot_be_rebound(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p={'identity':'one'};q={'identity':'two'}
            reserve([3301],p,root);reserve([3301],p,root)
            with self.assertRaises(ValueError):reserve([3301],q,root)
            with self.assertRaises(ValueError):reserve([3201],p,root)
    def test_uniform_draw_logging_is_conditional_and_disjoint(self):
        edges=[(('a','b'),1),(('a','c'),1),(('c','d'),1)]
        pairs,d=uniform_matching(edges,17);flat=[v for pair in pairs for v in pair]
        self.assertEqual(len(flat),len(set(flat)))
        self.assertEqual(d['selection_steps'][0]['eligible_edges'],3)
        self.assertAlmostEqual(d['selection_steps'][0]['conditional_probability'],1/3)
        self.assertAlmostEqual(d['joint_log_probability'],sum(math.log(s['conditional_probability']) for s in d['selection_steps']))
    def test_hybrid_model_cannot_invert_observed_heuristic_order(self):
        class M:
            def __init__(self,p):self.p=p
            def predict(self,x):return self.p
        s=feasible_state();a,b=s['members'][:2]
        low=score_pair(a,b,s,'hybrid',M(1))
        a['fields']['relationship_goal']=b['fields']['relationship_goal']='long_term'
        high=score_pair(a,b,s,'hybrid',M(0))
        self.assertGreater(high,low)

if __name__=='__main__':unittest.main()
