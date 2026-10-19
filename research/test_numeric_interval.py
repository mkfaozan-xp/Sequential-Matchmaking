"""A mathematically zero lower endpoint must never pass strict positive gain."""
import json
import tempfile
import unittest
import copy
from unittest.mock import patch
from pathlib import Path
from blackbox.metrics import paired_interval
from blackbox.reanalysis import binding,accepts_matrix,ROOT
from blackbox.provenance import source_hash


class NumericIntervalTests(unittest.TestCase):
    def test_frozen_exact_zero_is_not_tiny_positive(self):
        original=json.loads((ROOT/'evidence/v0_3_frozen_original/final_test.json').read_text())
        result=paired_interval(original['episodes'],'learned')
        self.assertEqual(result['ci95'][0],0.0)
        self.assertFalse(result['ci95'][0]>0)
        self.assertAlmostEqual(result['delta'],13/120)

    def test_new_research_source_cannot_reuse_prior_frozen_results(self):
        original=json.loads((ROOT/'evidence/v0_3_frozen_original/final_test.json').read_text())
        # Keep this regression independent of a workstation refitting/selecting
        # a different candidate; registry integrity has its own real-file tests.
        current={'source_sha256':source_hash(),'inference_release':original['config']['identity']['inference_release']}
        with patch('blackbox.reanalysis.execution_identity',return_value=current):
            with self.assertRaises(ValueError):binding()
            self.assertFalse(accepts_matrix(original))
            original['episodes'][0]['coverage']=0.123
            self.assertFalse(accepts_matrix(original))

    def test_different_candidate_cannot_reuse_frozen_results(self):
        original=json.loads((ROOT/'evidence/v0_3_frozen_original/final_test.json').read_text())
        changed=copy.deepcopy(original['config']['identity']);changed['inference_release']['deployment']['release_id']='f'*64
        with patch('blackbox.reanalysis.execution_identity',return_value=changed):
            self.assertFalse(accepts_matrix(original))

if __name__=='__main__':unittest.main()
