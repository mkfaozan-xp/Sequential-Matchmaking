import copy,json,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from blackbox.experiment import ROOT
sys.path.insert(0,str(ROOT/'starter'))
from kit import Simulator,generate,eligibility as official_eligibility,baseline_match
from blackbox.domain import HARD,SOFT,eligibility
from blackbox.policy import decide,MODES
from blackbox.contracts import validate_actions,validate_request
from blackbox.features import pair_features,direction_features
from blackbox.labels import msmi_label
from blackbox.allocation import allocate,greedy
from blackbox.storage import Ledger,atomic_json


def request(state,phase='match'):
    return {'schema_version':'1.0.0','phase':phase,'state':state,'memory':None}

def feasible_state():
    # Explicit fixture, fully disclosed fields, not a sampled hidden-world snapshot.
    s=Simulator(generate(81,4)).observe();base=copy.deepcopy(s['members'][0])
    base['age']=30;base['gender']='man';base['zone']='zone_a';base['arrived_day']=0;base['available']=True
    base['fields'].update(age_min=18,age_max=65,who_to_meet=['man'],relationship_structure='monogamous',
        smoking='no',partner_smoking='any',has_children=False,partner_children='any',wants_children='unsure',
        acceptable_zones=['zone_a'],schedule=['weekend_day'])
    base['fields'].update({k:None for k in SOFT})
    base['field_status']={k:'observed' if v is not None else 'not_asked' for k,v in base['fields'].items()}
    base['field_observed_day']={k:0 if v is not None else None for k,v in base['fields'].items()}
    s['members']=[]
    for i in range(4):
        m=copy.deepcopy(base);m['member_id']='syn_'+str(i)*32;s['members'].append(m)
    return s

class PolicyTests(unittest.TestCase):
    def test_eligibility_parity(self):
        import itertools
        for seed in (101,102):
            s=Simulator(generate(seed,40)).observe()
            for a,b in itertools.combinations(s['members'],2):self.assertEqual(eligibility(a,b),official_eligibility(a,b))
    def test_empty_all_modes(self):
        s=Simulator(generate(42,0)).observe()
        for mode in MODES:
            if 'learned' in mode or mode in ('single_value','waiting','answer_stress'):
                if not (ROOT/'artifacts/candidate.json').exists():continue
            if 'value' in mode or mode=='answer_stress':
                if not (ROOT/'artifacts/deployment.json').exists():continue
            for phase in ('ask','match'):
                out=decide(request(s,phase),mode);self.assertEqual(out['asks' if phase=='ask' else 'pairs'],[])
    def test_feature_symmetry_and_no_id_features(self):
        s=feasible_state();a,b=s['members'][:2]
        self.assertEqual(pair_features(a,b,s),pair_features(b,a,s))
        x=pair_features(a,b,s);a['member_id']='different';self.assertEqual(x,pair_features(a,b,s))
    def test_missing_cannot_be_overridden(self):
        s=feasible_state();s['members'][0]['fields']['schedule']=None
        with self.assertRaises(ValueError):validate_actions(s,'match',[[m['member_id'] for m in s['members'][:2]]])
    def test_failure_precedes_missing(self):
        s=feasible_state();a,b=s['members'][:2];a['fields']['age_min']=None;a['fields']['who_to_meet']=['woman']
        self.assertEqual(eligibility(a,b)['status'],'infeasible')
    def test_declined_not_asked(self):
        s=feasible_state()
        for m in s['members']:
            m['fields']['schedule']=None;m['field_status']['schedule']='declined';m['field_observed_day']['schedule']=None
        self.assertEqual(decide(request(s,'ask'))['asks'],[])
    def test_no_repeat_overlap_or_stale_availability(self):
        s=feasible_state();a,b,c=[m['member_id'] for m in s['members'][:3]]
        for pairs in ([[a,b],[a,c]],[[a,a]]):
            with self.assertRaises(ValueError):validate_actions(s,'match',pairs)
        s['introductions']=[{'user_a':a,'user_b':b,'assigned_day':0}]
        with self.assertRaises(ValueError):validate_actions(s,'match',[[a,b]])
        s['members'][2]['available']=False
        with self.assertRaises(ValueError):validate_actions(s,'match',[[a,c]])
    def test_global_path_counterexample(self):
        # MIP solves the true general graph rather than an invented bipartition.
        from blackbox.solve import solve
        edges=[(('a','b'),1),(('b','c'),1.5),(('c','d'),1)]
        self.assertEqual(len(greedy(edges)),1)
        self.assertEqual(len(solve(edges)['pairs']),2)
    def test_solver_timeout_returns_prebuilt_legal_fallback(self):
        s=feasible_state()
        with patch('blackbox.allocation.subprocess.run',side_effect=subprocess.TimeoutExpired('solver',1)):
            pairs,diag=allocate(s,solver='milp')
        self.assertTrue(diag['fallback']);validate_actions(s,'match',pairs)
    def test_baseline_match_parity(self):
        s=feasible_state();self.assertEqual(decide(request(s))['pairs'],baseline_match(s))
    def test_future_or_hidden_observation_rejected(self):
        for key,value in [('truth',{}),('bias',1),('exit_day',50)]:
            s=feasible_state();s['members'][0][key]=value
            with self.assertRaises(ValueError):validate_request(request(s))
        s=feasible_state();s['members'][0]['field_observed_day']['schedule']=1
        with self.assertRaises(ValueError):validate_request(request(s))
    def test_maturity_and_event_window(self):
        intro={'introduction_id':'i','user_a':'a','user_b':'b','assigned_day':0}
        self.assertIsNone(msmi_label(intro,[],32));self.assertEqual(msmi_label(intro,[],33),0)
        events=[{'introduction_id':'i','event':'date_happened','value':True,'occurred_day':30,'observed_day':30}]
        for ident in ('a','b'):events.append({'introduction_id':'i','member_id':ident,'event':'second_meeting_intention','value':'yes','occurred_day':33,'observed_day':33})
        self.assertEqual(msmi_label(intro,events,33),1)
        events[-1]['occurred_day']=34;events[-1]['observed_day']=34
        self.assertEqual(msmi_label(intro,events,34),0)
    def test_stdout_single_json_restart_and_nan_rejection(self):
        s=feasible_state();r=request(s)
        outputs=[]
        for _ in range(2):
            p=subprocess.run([sys.executable,str(ROOT/'policy.py')],input=json.dumps(r),text=True,capture_output=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr);outputs.append(json.loads(p.stdout))
            self.assertEqual(set(outputs[-1]),{'pairs','memory'})
        self.assertEqual(*outputs)
        p=subprocess.run([sys.executable,str(ROOT/'policy.py')],input='{"memory":NaN}',text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertEqual(p.stdout,'')
    def test_ledger_resume_and_interrupted_run(self):
        with tempfile.TemporaryDirectory() as d:
            l=Ledger(Path(d)/'runs.db');key,prior=l.claim({'seed':1});self.assertIsNone(prior)
            l.close();l=Ledger(Path(d)/'runs.db');key,prior=l.claim({'seed':1});self.assertIsNone(prior)
            l.finish(key,{'valid':True,'score':3});_,prior=l.claim({'seed':1});self.assertEqual(prior['score'],3);l.close()
    def test_waiting_cap_for_reavailable_members(self):
        s=feasible_state();s['day']=10
        with patch('blackbox.allocation.graph_edges',return_value=[((s['members'][0]['member_id'],s['members'][1]['member_id']),.01)]):
            pairs,_=allocate(s,wait_threshold=.02,available_since={m['member_id']:10 for m in s['members']})
            self.assertEqual(pairs,[])
            pairs,_=allocate(s,wait_threshold=.02,available_since={m['member_id']:7 for m in s['members']})
            self.assertEqual(len(pairs),1)
    def test_model_integrity(self):
        if not (ROOT/'artifacts/candidate.json').exists():self.skipTest('train first')
        from blackbox.model import load_model
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'model.json';p.write_text('{}');p.with_suffix('.sha256').write_text('bad')
            with self.assertRaises(ValueError):load_model(p)
    def test_paired_questions_are_chosen_before_answers(self):
        if not (ROOT/'artifacts/deployment.json').exists():self.skipTest('train first')
        s=feasible_state()
        for m in s['members'][:2]:
            m['fields']['schedule']=None;m['field_status']['schedule']='not_asked';m['field_observed_day']['schedule']=None
        before=copy.deepcopy(s);out=decide(request(s,'ask'),'value_greedy')
        self.assertEqual(s,before);validate_actions(s,'ask',out['asks'])

if __name__=='__main__':unittest.main()
