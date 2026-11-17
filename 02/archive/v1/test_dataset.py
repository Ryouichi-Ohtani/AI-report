import unittest
from build_dataset import build


class DatasetTest(unittest.TestCase):
    def test_keys_and_controls(self):
        items, keys = build()
        self.assertEqual(len(items), 36)
        self.assertEqual(len({r['id'] for r in items}), 36)
        for item in items:
            self.assertIn(keys[item['id']], item['options'])
        self.assertEqual(sum(i['family'] == 'underdetermined' for i in items), 4)
