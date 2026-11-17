"""Exhaustive cubic-lattice SAW oracle for the 10-residue control only.

Fix first bond to +x: every unanchored conformation has a rigid rotation with
this first bond, so this symmetry reduction preserves the optimum.
"""
import json
from pathlib import Path
import time

from hp_model import DIRECTIONS, add, contact_pairs, expand_sequence, valid


def main():
    started = time.perf_counter()
    sequence = expand_sequence("H2P2H2P2H2")
    path = [(0, 0, 0), (1, 0, 0)]
    occupied = {point: i for i, point in enumerate(path)}
    complete = nodes = 0
    best_energy, best_fold = 0, None

    def visit(energy):
        nonlocal complete, nodes, best_energy, best_fold
        nodes += 1
        if len(path) == len(sequence):
            complete += 1
            if best_fold is None or energy < best_energy:
                best_energy, best_fold = energy, tuple(path)
            return
        i = len(path)
        for d in DIRECTIONS:
            candidate = add(path[-1], d)
            if candidate in occupied:
                continue
            new_contacts = 0
            if sequence[i] == "H":
                for direction in DIRECTIONS:
                    j = occupied.get(add(candidate, direction), -1)
                    if j >= 0 and j < i - 1 and sequence[j] == "H":
                        new_contacts += 1
            occupied[candidate] = i
            path.append(candidate)
            visit(energy - new_contacts)
            path.pop()
            del occupied[candidate]

    visit(0)
    assert valid(best_fold)
    assert -len(contact_pairs(sequence, best_fold)) == best_energy
    result = {"sequence": sequence, "optimal_energy": best_energy,
              "complete_walks_first_bond_fixed": complete,
              "expanded_partial_walks": nodes, "fold": best_fold,
              "seconds": time.perf_counter() - started,
              "proof_scope": "All self-avoiding cubic-lattice walks of length 10, first bond fixed to +x by rotational symmetry."}
    path = Path(__file__).resolve().parent / "results" / "exact_toy10.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
