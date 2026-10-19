"""Focused batch-information tests for the frozen shared-objective controller."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'));sys.path.insert(0,str(ROOT))
from coordinated import engine
from blackbox.domain import HARD


class JointQuestionTests(unittest.TestCase):
    def setUp(self):
        self.edges=[(('a','b'),.05,10,frozenset({'a','b'}))]
        self.scenarios=[self.edges,self.edges,self.edges]

    def test_complementary_endpoints_are_selected_together(self):
        with patch.object(engine,'load_artifact',return_value={'donors':[{}]}),patch.object(engine,'draws',return_value=(self.scenarios,.5)):
            actions,diag=engine.ask({'day':0,'ask_budget_remaining':6},self.edges)
        self.assertEqual(actions,[{'member_id':'a','field':'constraints'},{'member_id':'b','field':'constraints'}])
        self.assertEqual(diag['planned_question_cost'],6)
        self.assertGreater(diag['estimated_information_gain'],0)

    def test_unaffordable_complementary_batch_is_not_half_asked(self):
        actions,diag=engine.ask({'day':0,'ask_budget_remaining':3},self.edges)
        self.assertEqual(actions,[]);self.assertEqual(diag['planned_question_cost'],0)

    def test_response_learning_ignores_future_log_entries(self):
        complete={'field':'constraints','observed_day':0,'statuses':{k:'observed' for k in HARD}}
        future={'field':'constraints','observed_day':1,'statuses':{k:'declined' for k in HARD}}
        self.assertEqual(engine.response_probability({'day':0,'ask_log':[complete,complete,complete,future]}),.8)


if __name__=='__main__':unittest.main(verbosity=2)
