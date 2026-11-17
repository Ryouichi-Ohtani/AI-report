"""Small exhaustive invariants rather than snapshots of experiment output."""
import unittest
from fractions import Fraction
from solver import Expr, State, catalogue, combine, leaves, lower_bound, search, successors


class SolverTests(unittest.TestCase):
    def test_decimal_and_factorial(self):
        self.assertIn(Expr(Fraction(3, 25), ".12"), list(leaves("12")))
        self.assertIn(Expr(Fraction(720), "6!", 1), list(leaves("6")))

    def test_no_zero_division(self):
        self.assertIsNone(combine(Expr(Fraction(1), "1"), Expr(Fraction(0), "0"), "/"))

    def test_consistent_heuristic(self):
        pending, seen = [State(0, ())], set()
        while pending:
            state = pending.pop()
            if state.key() in seen:
                continue
            seen.add(state.key())
            for child in successors(state, "12"):
                self.assertLessEqual(lower_bound(state, "12"), 1 + lower_bound(child, "12"))
                pending.append(child)

    def test_dp_matches_rpn_terminal_values(self):
        for digits in ("12", "123"):
            pending, seen, final = [State(0, ())], set(), set()
            while pending:
                state = pending.pop()
                if state.key() in seen:
                    continue
                seen.add(state.key())
                if state.position == len(digits) and len(state.stack) == 1:
                    final.add(state.stack[0].value)
                pending.extend(successors(state, digits))
            self.assertEqual(final, set(catalogue(digits)))

    def test_astar_has_bfs_optimal_action_cost(self):
        bfs = search("123", "bfs", 0.1, 100000)
        for method in ["astar", "astar_guided"]:
            result = search("123", method, 0.1, 100000)
            self.assertTrue(result["success"])
            self.assertEqual(result["actions"], bfs["actions"])


if __name__ == "__main__":
    unittest.main()
