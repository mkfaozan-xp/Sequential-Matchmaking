import unittest
from train import select_fit


class TrainingSelectionTests(unittest.TestCase):
    def test_cross_validation_excludes_entire_seed_and_keeps_feature_schema(self):
        rows=[{'seed':seed,'x':[float(i%2)],'label':int(i%3==0)} for seed in (1101,1102,1103) for i in range(12)]
        head,selection=select_fit(rows,['observed'])
        self.assertEqual(head['n'],36)
        self.assertEqual(head['feature_names'],['observed'])
        self.assertIn(head['l2'],(1,10,100))
        for candidate in selection['candidates']:
            for fold in candidate['folds']:
                self.assertNotIn(fold['held_out_seed'],fold['training_seeds'])
                self.assertEqual(fold['score']['n'],12)
        self.assertEqual(head['l2'],min(selection['candidates'],key=lambda c:(c['mean_seed_log_loss'],-c['l2']))['l2'])

    def test_insufficient_independent_training_seeds_rejected(self):
        with self.assertRaises(ValueError):select_fit([{'seed':1101,'x':[0],'label':0}],['x'])

if __name__=='__main__':unittest.main()
