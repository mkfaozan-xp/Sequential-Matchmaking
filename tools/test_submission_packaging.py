"""Regression checks for the submission verifier; no model training or tuning."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]


class SubmissionPackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='blackbox_submission_tests_')
        cls.copy=Path(cls.temp.name)/'submission'
        shutil.copytree(ROOT,cls.copy,ignore=shutil.ignore_patterns('__pycache__'))
        cls.original_manifest=(cls.copy/'SUBMISSION_MANIFEST.json').read_bytes()

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def invoke(self):
        env=dict(os.environ)
        for key in ('PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        return subprocess.run([sys.executable,'-B',str(self.copy/'tools/verify_submission.py')],
                              cwd=self.copy,capture_output=True,timeout=30,env=env)

    def altered(self,name,transform,expected_error):
        path=self.copy/name;original=path.read_bytes()
        try:
            path.write_bytes(transform(original))
            manifest=json.loads(self.original_manifest)
            manifest['files'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
            (self.copy/'SUBMISSION_MANIFEST.json').write_text(json.dumps(manifest))
            result=self.invoke()
            self.assertEqual(result.returncode,2)
            self.assertIn(expected_error,json.loads(result.stderr)['error'])
        finally:
            path.write_bytes(original)
            (self.copy/'SUBMISSION_MANIFEST.json').write_bytes(self.original_manifest)

    def test_clean_inventory(self):
        result=self.invoke();self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['submitted_mode'],'conservative')

    def test_mode_mismatch_even_after_outer_rehash(self):
        def change(raw):
            obj=json.loads(raw);obj['mode']='rank_aux';return json.dumps(obj).encode()
        self.altered('runtime/artifacts/deployment.json',change,'deployment mode/assets mismatch')

    def test_incomplete_baseline_matrix_even_after_outer_rehash(self):
        def change(raw):
            obj=json.loads(raw);obj['episodes'].pop();return json.dumps(obj).encode()
        self.altered('research/results/validation.json',change,'comparison incomplete')

    def test_incomplete_ablation_even_after_outer_rehash(self):
        def change(raw):
            obj=json.loads(raw);obj['episodes'].pop();return json.dumps(obj).encode()
        self.altered('results/asking_ablation.json',change,'ablation incomplete')

    def test_changed_research_source_even_after_outer_rehash(self):
        self.altered('research/blackbox/features.py',lambda raw:raw+b'\n# altered\n','research source identity changed')

    def test_unexpected_file(self):
        path=self.copy/'unexpected.txt'
        try:
            path.write_text('unexpected')
            result=self.invoke();self.assertEqual(result.returncode,2)
            self.assertIn('inventory changed',json.loads(result.stderr)['error'])
        finally:path.unlink()


if __name__=='__main__':unittest.main(verbosity=2)
