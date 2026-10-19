"""Regressions for target integrity, temporal leakage, sparsity and selection."""
import ast,copy,hashlib,json,math,unittest,zipfile
from pathlib import Path
from blackbox.features import NAMES,DIRECTION_NAMES,FEATURE_VERSION,pair_features,response_history
from blackbox.outcome_history import summarize,vector,NAMES as HISTORY_NAMES
from blackbox.labels import msmi_label,auxiliary_pair_label,scheduled_hold_label
from blackbox.model import LinearModel
from blackbox.basis import lifted_names
from blackbox.fitting import fit
from blackbox.provenance import execution_identity
from blackbox.experiment import ROOT,VARIANTS
from test_policy import feasible_state

class OutcomeTests(unittest.TestCase):
    def history_fixture(self):
        s=feasible_state();s['day']=20;a,b=s['members'][:2]
        intro={'introduction_id':'i','user_a':a['member_id'],'user_b':b['member_id'],'assigned_day':0,'response_deadline_day':7}
        s['introductions']=[intro];s['feedback']=[{'introduction_id':'i','member_id':None,'event':'date_happened','value':True,'occurred_day':10,'observed_day':10}]
        return s,intro

    def test_official_label_function_is_unchanged_from_v05(self):
        with zipfile.ZipFile(ROOT/'evidence/Blackbox_ML_Prototype_v0_5_0_original.zip') as z:
            old=ast.parse(z.read('Blackbox_ML_Prototype/blackbox/labels.py'))
        current=ast.parse((ROOT/'blackbox/labels.py').read_text())
        fn=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='msmi_label')
        self.assertEqual(ast.dump(fn(old)),ast.dump(fn(current)))

    def test_late_yes_is_auxiliary_positive_but_official_failure(self):
        s,i=self.history_fixture()
        for actor in (i['user_a'],i['user_b']):s['feedback'].append({'introduction_id':'i','member_id':actor,'event':'second_meeting_intention','value':'yes','occurred_day':14,'observed_day':14})
        self.assertEqual(msmi_label(i,s['feedback'],40),0)
        self.assertIsNone(auxiliary_pair_label(i,s['feedback'],39))
        self.assertEqual(auxiliary_pair_label(i,s['feedback'],40),1)

    def test_null_second_response_is_not_a_negative_preference(self):
        s,i=self.history_fixture();actor=i['user_a']
        s['feedback'].append({'introduction_id':'i','member_id':actor,'event':'second_meeting_intention','value':None,'occurred_day':None,'observed_day':15})
        history=summarize(s);self.assertEqual(history[actor]['answered'],0)
        v=vector(actor,history)
        self.assertEqual(v[HISTORY_NAMES.index('second_yes_rate')],.5)
        self.assertEqual(v[HISTORY_NAMES.index('second_no_history')],0)
        self.assertEqual(v[HISTORY_NAMES.index('second_record_count')],.1)

    def test_future_second_feedback_cannot_change_decision_features(self):
        s,i=self.history_fixture();a,b=s['members'][:2];before=pair_features(a,b,s)
        s['feedback'].append({'introduction_id':'i','member_id':i['user_a'],'event':'second_meeting_intention','value':'yes','occurred_day':21,'observed_day':21})
        self.assertEqual(before,pair_features(a,b,s));self.assertEqual(pair_features(a,b,s),pair_features(b,a,s))

    def test_observed_late_positive_updates_history_once(self):
        s,i=self.history_fixture();e={'introduction_id':'i','member_id':i['user_a'],'event':'second_meeting_intention','value':'yes','occurred_day':14,'observed_day':14}
        s['feedback'] += [e,copy.deepcopy(e)]
        h=summarize(s)[i['user_a']];self.assertEqual(h['yes'],1);self.assertEqual(h['answered'],1);self.assertEqual(h['timely_yes'],0)

    def test_scheduled_hold_proxy_keeps_censoring_and_range(self):
        s,i=self.history_fixture();self.assertIsNone(scheduled_hold_label(i,s['feedback'],39))
        self.assertEqual(scheduled_hold_label(i,s['feedback'],40),16)
        self.assertEqual(scheduled_hold_label(i,[],40),8)

    def test_sparse_fit_recovers_signal_and_zeros_independent_noise(self):
        rows=[{'x':[float(i%2),float((i//2)%2)],'label':i%2,'seed':1101+i%3} for i in range(400)]
        h=fit(rows,['signal','noise'],l2=1,l1=10)
        self.assertGreater(h['weights'][0],1)
        self.assertEqual(h['weights'][1],0)
        self.assertTrue(h['optimizer_converged']);self.assertLess(h['kkt_max_per_row'],1e-4)

    def test_relative_loss_stop_without_kkt_restarts_before_export(self):
        import numpy as np
        from types import SimpleNamespace
        from unittest.mock import patch
        from blackbox import fitting
        original=fitting.minimize;calls=[]
        def stalled_then_real(fun,initial,**kwargs):
            calls.append(1)
            if len(calls)==1:
                return SimpleNamespace(success=True,x=np.asarray(initial).copy(),jac=fun(initial)[1],
                    message='relative-loss stop with unresolved gradient',nit=0)
            return original(fun,initial,**kwargs)
        rows=[{'x':[float(i%2)],'label':i%2,'seed':1101+i%3} for i in range(120)]
        with patch.object(fitting,'minimize',side_effect=stalled_then_real):
            h=fitting.fit(rows,['signal'],l2=1,l1=2)
        self.assertGreater(len(calls),1)
        self.assertGreater(h['optimizer_attempts'][0]['kkt_max_per_row'],1e-4)
        self.assertLessEqual(h['kkt_max_per_row'],1e-4)
        self.assertGreater(h['weights'][0],1)

    def artifact(self):
        def h(names,basis='identity'):
            names=lifted_names(names,basis);return {'basis':basis,'feature_names':names,'weights':[0.0]*len(names),'intercept':0}
        return {'feature_version':FEATURE_VERSION,'model_id':'fixture','joint':h(NAMES),'direction':h(DIRECTION_NAMES),
            'joint_nohistory':h(NAMES,'without_outcome_history'),'timeliness_factor':.5}

    def test_exported_nohistory_head_ignores_second_history_at_inference(self):
        a=self.artifact();a['joint_nohistory']['weights']=[1.0]*len(a['joint_nohistory']['weights']);model=LinearModel(a)
        x=[0.0]*len(NAMES);y=[float(n.startswith('outcome:')) for n in NAMES]
        self.assertEqual(model.predict(x,'joint_nohistory'),model.predict(y,'joint_nohistory'))

    def test_nonfinite_auxiliary_head_and_invalid_factor_fail_loading(self):
        a=self.artifact();a['auxiliary']=copy.deepcopy(a['joint']);a['auxiliary']['weights'][0]=float('nan')
        with self.assertRaises(ValueError):LinearModel(a)
        a=self.artifact();a['timeliness_factor']=1.1
        with self.assertRaises(ValueError):LinearModel(a)

    def test_profile_hash_binds_new_history_implementation(self):
        from blackbox.registry import feature_digest
        a=self.artifact();a['feature_source_sha256']='0'*64
        with self.assertRaises(ValueError):LinearModel(a)
        a['feature_source_sha256']=feature_digest();LinearModel(a)

    def test_non_ml_goal_control_cannot_be_selected_as_ml_candidate(self):
        from scripts.select_candidate import choose,PILOT,ELIGIBLE
        rows=[];scores={'conservative':1,'hybrid':2,'aux_hybrid':3,'outcome':2,'rate':1,'ridge_tie':1,'nohistory_tie':1,'goal_tie':9}
        for seed in range(2601,2605):
            for v in VARIANTS:
                for mode in PILOT:
                    events=scores[mode];rows.append({'seed':seed,'variant':v,'method':mode,'valid':True,'arrived_members':200,
                        'mutual_second_meeting_intention':events,'dates':10,'mutual_acceptances':15,'assignments':20,
                        'msmi_per_100_arrived_members':events/2,'served_members':40,'unserved_members':160,'coverage':.2,
                        'ask_cost':100,'max_request_bytes':100,'max_response_bytes':100})
        data={'complete':True,'config':{'identity':execution_identity()},'seeds':list(range(2601,2605)),
            'variants':list(VARIANTS),'methods':list(PILOT),'episodes':rows,'attempt_audit':[]}
        selected=choose(data);self.assertEqual(selected['selected_mode'],'aux_hybrid');self.assertIn(selected['selected_mode'],ELIGIBLE)
        data['complete']=False
        with self.assertRaises(ValueError):choose(data)

if __name__=='__main__':unittest.main()
