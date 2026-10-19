import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from argparse import Namespace
from unittest.mock import patch
from blackbox.registry import ROOT
from blackbox.provenance import execution_identity


def module(name):
    spec=importlib.util.spec_from_file_location('test_support_'+name,ROOT/'scripts'/f'{name}.py')
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


class ReleaseControlTests(unittest.TestCase):
    def test_unbound_pass_flags_cannot_pass_gate(self):
        gate=module('release_gate')
        result=gate.assess({'success':True},{'all_valid':True},{'validated':True})
        self.assertEqual(result['status'],'blocked')
        self.assertFalse(result['candidate_promotion']['eligible'])

    def test_identity_includes_exact_model_and_sampler_manifest(self):
        identity=execution_identity()
        self.assertEqual(len(identity['inference_release']['deployment']['release_id']),64)
        self.assertEqual(len(identity['inference_release']['manifest_sha256']),64)

    def test_old_source_or_asset_attestation_is_rejected(self):
        gate=module('release_gate')
        container={'identity':{'old':'model'},'status':'completed','validated':True}
        result=gate.assess(None,None,container)
        self.assertFalse(result['checks']['exact_container_release'])

    def test_conservative_container_does_not_attest_learned_policy(self):
        gate=module('release_gate')
        container={'identity':execution_identity(mode='conservative'),'status':'completed',
            'image_id':'sha256:'+'1'*64,'image_size_bytes':100,
            'constraints':{'network':'none','cpus':2,'memory_bytes':1024**3,'pids':64,'read_only':True,'tmpfs_bytes':64*1024**2},
            'episodes':[{'seed':101,'variant':v,'valid':True} for v in gate.VARIANTS]}
        self.assertTrue(gate.container_valid(container,'conservative'))
        self.assertFalse(gate.container_valid(container,'learned'))

    def test_partial_validation_matrix_cannot_pass(self):
        gate=module('release_gate')
        data={'complete':True,'config':{'identity':execution_identity()},'seeds':[2101],
              'variants':['development'],'methods':['conservative'],'episodes':[]}
        self.assertFalse(gate.valid_matrix(data,require_baselines=True))

    def test_report_never_claims_pass_without_test_execution(self):
        report=module('build_report')
        # Inspection of behavior is covered through the gate; absent suites never count as tests.
        gate=module('release_gate')
        tests={'identity':execution_identity(),'success':True,'tests_run':999,'suites':[]}
        self.assertFalse(gate.assess(tests,None,None)['checks']['actual_test_suites'])

    def test_budget_timeout_prevents_later_phase(self):
        budget=module('run_budget');calls=[]
        def runner(command,seconds,log,environment):
            calls.append(command)
            raise TimeoutError('test deadline')
        with tempfile.TemporaryDirectory() as d,patch.object(budget,'ROOT',Path(d)):
            (Path(d)/'results').mkdir()
            record={'phases':[]}
            result=budget.execute_phases([('first',['first'],10,True),('later',['later'],10,True)],
                                          200,record,{},runner=runner,clock=lambda:100)
            self.assertFalse(result);self.assertEqual(calls,[['first']])
            self.assertEqual(record['phases'][0]['status'],'timed_out')

    def test_budget_protects_downstream_reservations(self):
        budget=module('run_budget');allowances=[]
        def runner(command,seconds,log,environment):
            allowances.append(seconds);return 0
        with tempfile.TemporaryDirectory() as d,patch.object(budget,'ROOT',Path(d)):
            (Path(d)/'results').mkdir()
            result=budget.execute_phases([('training',['train'],9000,True),('container',['docker'],2400,True)],
                4000,{'phases':[]},{},runner=runner,clock=lambda:100,reservations={'container':1200})
            self.assertTrue(result);self.assertEqual(allowances,[2640,2400])

    def test_failed_workflow_still_finalizes_and_marks_skipped_docker_current(self):
        budget=module('run_budget');calls=[]
        def execute(phases,deadline,record,environment,**kwargs):
            calls.append([p[0] for p in phases]);return len(calls)>1
        with tempfile.TemporaryDirectory() as d,patch.object(budget,'ROOT',Path(d)),\
                patch.object(budget,'execute_phases',side_effect=execute),\
                patch.object(budget,'cleanup_docker'),\
                patch('blackbox.provenance.execution_identity',side_effect=lambda mode=None:{'current':True,'mode':mode}):
            code=budget.run_workflow(Namespace(minutes=120,bootstrap=False,skip_training=False,skip_docker=True))
            import json
            self.assertEqual(code,2)
            self.assertEqual(calls[1],['release_gate','report'])
            evidence=json.loads((Path(d)/'results/container_candidate.json').read_text())
            self.assertEqual(evidence['identity'],{'current':True,'mode':'hybrid'})
            self.assertFalse(evidence['validated'])

if __name__=='__main__':unittest.main()
