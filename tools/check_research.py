"""Run research regressions with one historical archive read replaced by a flat fixture."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]/'research'
sys.path.insert(0,str(ROOT))


def main():
    os.chdir(ROOT)
    fixtures=json.loads((ROOT/'evidence/FLAT_TEST_FIXTURES.json').read_text())
    label=(ROOT/'evidence/label_v05.py').read_bytes()
    if hashlib.sha256(label).hexdigest()!=fixtures['label_v05_sha256']:raise ValueError('flat label fixture integrity')
    final=(ROOT/'evidence/v0_3_frozen_original/final_test.json').read_bytes()
    if hashlib.sha256(final).hexdigest()!=fixtures['frozen_final_sha256']:raise ValueError('flat final fixture integrity')
    import test_v06_outcomes
    def unchanged_label(self):
        fn=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='msmi_label')
        self.assertEqual(ast.dump(fn(ast.parse(label))),ast.dump(fn(ast.parse((ROOT/'blackbox/labels.py').read_text()))))
    test_v06_outcomes.OutcomeTests.test_official_label_function_is_unchanged_from_v05=unchanged_label
    suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test*.py')
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    print(json.dumps({'passed':result.wasSuccessful(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'flat_fixture_adaptations':1,'skipped':len(result.skipped)}))
    return 0 if result.wasSuccessful() else 2


if __name__=='__main__':raise SystemExit(main())
