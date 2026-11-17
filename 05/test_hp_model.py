"""Structural, energy-delta and inheritance-rule regression checks."""
import json
from pathlib import Path
import random
import unittest

from hp_model import (ROTATIONS, Scorer, contact_pairs, crossover, expand_sequence,
                      hill_climb, local_moves, mutate, random_fold, valid)
from experiment import run


class HPModelTests(unittest.TestCase):
    def test_parser(self):
        self.assertEqual(expand_sequence("H2P(PH)2"), "HHPPHPH")
        for expression in ("H0", "(HP", "HP)", "HX", "2H"):
            with self.assertRaises(ValueError):
                expand_sequence(expression)
        data = json.loads((Path(__file__).parent / "benchmarks.json").read_text())
        for row in data["sequences"][2:]:
            self.assertEqual(len(expand_sequence(row["expression"])),
                             47 if "length_warning" in row else 48)

    def test_energy_excludes_chain_bonds(self):
        square = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))
        self.assertEqual(contact_pairs("HHHH", square), ((0, 3),))
        self.assertEqual(Scorer("HHHH").energy(square), -1)

    def test_rotations_and_variation_are_feasible(self):
        self.assertEqual(len(ROTATIONS), 24)
        rng = random.Random(7)
        a, b = random_fold(48, rng), random_fold(48, rng)
        for _ in range(200):
            a = mutate(crossover(a, b, rng), rng)
            self.assertTrue(valid(a))
            self.assertEqual(len(a), 48)
            a, b = b, a

    def test_incremental_energy_matches_full_and_local_optimum(self):
        rng = random.Random(19)
        seq = expand_sequence("(HHP)6HH")
        scorer = Scorer(seq)
        for _ in range(30):
            fold = random_fold(len(seq), rng)
            energy = scorer.energy(fold)
            occupied = {p: i for i, p in enumerate(fold)}
            for changes in local_moves(fold):
                candidate = tuple(changes.get(i, p) for i, p in enumerate(fold))
                self.assertTrue(valid(candidate))
                self.assertEqual(energy + scorer.delta(fold, occupied, changes), scorer.energy(candidate))
            best, best_energy, _ = hill_climb(fold, energy, scorer)
            self.assertLessEqual(best_energy, energy)
            self.assertEqual(best_energy, scorer.energy(best))
            for changes in local_moves(best):
                candidate = tuple(changes.get(i, p) for i, p in enumerate(best))
                self.assertGreaterEqual(scorer.energy(candidate), best_energy)

    def test_three_modes_budget_and_reproducibility(self):
        for method in ("darwin", "baldwin", "lamarck"):
            a = run("HHPPHHPPHH", method, 5, 8, 2, 200)
            b = run("HHPPHHPPHH", method, 5, 8, 2, 200)
            self.assertEqual(a["budget"]["energy"], b["budget"]["energy"])
            self.assertEqual(a["budget"]["fold"], b["budget"]["fold"])
            self.assertEqual(a["budget"]["calls"], 200)
            if method != "baldwin":
                for h in a["history"]:
                    self.assertEqual(h["population_best_raw"], h["population_best_fitness"])


if __name__ == "__main__":
    unittest.main()
