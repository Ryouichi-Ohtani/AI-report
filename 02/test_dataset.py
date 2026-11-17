import collections
import unittest
from build_dataset import build


class DatasetTest(unittest.TestCase):
    def test_keys_controls_and_public_schema(self):
        items, keys, metadata = build()
        self.assertEqual(len(items), 44)
        self.assertEqual(len({r['id'] for r in items}), 44)
        self.assertEqual(set(keys), set(metadata))
        for item in items:
            self.assertEqual(set(item), {'id', 'prompt', 'options'})
            self.assertRegex(item['id'], r'^[0-9a-f]{16}$')
            self.assertEqual(list(item['options']), list('ABC'))
            self.assertIn(keys[item['id']], item['options'])
        families = collections.Counter(m['family'] for m in metadata.values())
        self.assertEqual(families, {'belief': 8, 'second_order': 16, 'irony': 8, 'faux_pas': 8, 'underdetermined': 4})

    def test_second_order_factorial_design(self):
        _, _, metadata = build()
        second = [m for m in metadata.values() if m['family'] == 'second_order']
        self.assertEqual(collections.Counter((m['actual_seen'], m['believed_seen']) for m in second),
                         {(0, 0): 4, (0, 1): 4, (1, 0): 4, (1, 1): 4})
        groups = collections.Counter(m['group'] for m in metadata.values())
        self.assertEqual(sum(n == 2 for n in groups.values()), 20)

    def test_condition_and_option_order_not_deterministic_keys(self):
        items, keys, metadata = build()
        for family in ['belief', 'second_order', 'irony', 'faux_pas']:
            labels = {keys[i['id']] for i in items if metadata[i['id']]['family'] == family}
            self.assertGreater(len(labels), 1)
        self.assertNotEqual([metadata[i['id']]['family'] for i in items],
                            sorted(metadata[i['id']]['family'] for i in items))


if __name__ == '__main__':
    unittest.main()
