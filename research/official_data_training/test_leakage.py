"""Regression checks against future disclosure and right-censoring leakage."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('public_fit', HERE/'train_public.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LeakageTests(unittest.TestCase):
    def setUp(self):
        self.state = json.loads((HERE.parent/'starter/data/public_01/state.json').read_text())

    def test_future_disclosure_values_do_not_change_features(self):
        before, _ = module.rows_for_pool(self.state, 'public_01')
        changed = copy.deepcopy(self.state)
        # Day 30 is later than every mature cohort's assignment (<=23).
        for member in changed['members']:
            for field in ('relationship_goal', 'relationship_pace'):
                member['field_observed_day'][field] = 30
                member['fields'][field] = 'future_sentinel_one'
        first, _ = module.rows_for_pool(changed, 'public_01')
        for member in changed['members']:
            for field in ('relationship_goal', 'relationship_pace'):
                member['fields'][field] = 'future_sentinel_two'
        second, _ = module.rows_for_pool(changed, 'public_01')
        self.assertEqual(first, second)
        self.assertEqual(len(before), len(first))

    def test_pending_cohorts_excluded_even_when_positive_arrives_early(self):
        changed = copy.deepcopy(self.state)
        intro = copy.deepcopy(changed['introductions'][0])
        intro.update(introduction_id='pending', assigned_day=28, response_deadline_day=35)
        changed['introductions'].append(intro)
        changed['feedback'].append({'introduction_id':'pending','member_id':intro['user_a'],
            'event':'introduction_response','observed_day':29,'occurred_day':29,'value':'yes'})
        original, excluded = module.rows_for_pool(self.state, 'public_01')
        actual, pending = module.rows_for_pool(changed, 'public_01')
        self.assertEqual(original, actual)
        self.assertEqual(excluded + 2, pending)

    def test_future_feedback_never_changes_historical_features(self):
        first, _ = module.rows_for_pool(self.state, 'public_01')
        changed = copy.deepcopy(self.state)
        for event in changed['feedback']:
            if event['observed_day'] > 23:
                event['value'] = 'future_sentinel'
        second, _ = module.rows_for_pool(changed, 'public_01')
        self.assertEqual([r['x'] for r in first], [r['x'] for r in second])

    def test_evaluation_does_not_mutate_fitted_artifact(self):
        head = json.loads((HERE/'results/response_model.json').read_text())['direction']
        original = copy.deepcopy(head)
        rows, _ = module.rows_for_pool(self.state, 'public_01')
        module.evaluate(rows, head)
        self.assertEqual(head, original)


if __name__ == '__main__':
    unittest.main()
