import unittest
from foldit_log import validate, analyze, ROOT


class LogTest(unittest.TestCase):
    def test_gain(self):
        self.assertEqual(validate({'seconds': 30, 'before': 4, 'after': 3}), -1)

    def test_rank(self):
        with self.assertRaises(ValueError):
            validate({'seconds': 1, 'before': 0, 'after': 1, 'rank': 5, 'players': 4})

    def test_empty_log_is_explicit(self):
        result = analyze(ROOT / 'data' / 'events.csv')
        self.assertIn(result['status'], ['awaiting_real_play', 'observed'])
