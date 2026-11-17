import unittest
import numpy as np
from bento_ga import compositions, run, counts


class BentoTest(unittest.TestCase):
    def test_simplex(self):
        c = list(compositions(3, 3))
        self.assertEqual(len(c), 10)
        self.assertTrue(all(sum(x) == 3 for x in c))

    def test_monotone_archive(self):
        r = run(1, 'ga', population=12, generations=10)
        self.assertTrue(all(a >= b for a, b in zip(r['history'], r['history'][1:])))
        self.assertEqual(sum(r['counts']), 16)
        self.assertEqual(r['evaluations'], 132)

    def test_representation(self):
        self.assertEqual(counts(np.zeros(16, dtype=int))[0].tolist(), [16,0,0,0,0,0,0,0])
