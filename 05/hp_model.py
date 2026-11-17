"""Feasible cubic-lattice HP folding primitives (no invalid-fold penalties)."""
from __future__ import annotations

import itertools
import random
import re
import time
from typing import Dict, Iterable, Tuple

Point = Tuple[int, int, int]
Fold = Tuple[Point, ...]
DIRECTIONS: Tuple[Point, ...] = ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                (0, -1, 0), (0, 0, 1), (0, 0, -1))


def add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def distance(a: Point, b: Point) -> int:
    return sum(abs(x - y) for x, y in zip(a, b))


def expand_sequence(expression: str) -> str:
    """Expand H2P(PH)3, with recursive groups and explicit input validation."""
    tokens = re.findall(r"[HP()]|\d+", expression)
    if "".join(tokens) != expression or not tokens:
        raise ValueError("Invalid HP expression")
    index = 0

    def parse(group: bool = False) -> str:
        nonlocal index
        chunks = []
        while index < len(tokens) and tokens[index] != ")":
            token = tokens[index]
            index += 1
            if token == "(":
                atom = parse(True)
            elif token in ("H", "P"):
                atom = token
            else:
                raise ValueError("Expected H, P or group")
            repeat = 1
            if index < len(tokens) and tokens[index].isdigit():
                repeat = int(tokens[index])
                index += 1
                if repeat < 1:
                    raise ValueError("Repetitions must be positive")
            chunks.append(atom * repeat)
        if group:
            if index >= len(tokens) or tokens[index] != ")":
                raise ValueError("Unclosed group")
            index += 1
        return "".join(chunks)

    result = parse()
    if index != len(tokens):
        raise ValueError("Unexpected closing group")
    return result


def valid(fold: Fold) -> bool:
    return len(set(fold)) == len(fold) and all(
        distance(a, b) == 1 for a, b in zip(fold, fold[1:]))


def normalize(fold: Fold) -> Fold:
    return tuple(sub(p, fold[0]) for p in fold)


def random_fold(n: int, rng: random.Random) -> Fold:
    for _ in range(1000):
        points = [(0, 0, 0)]
        occupied = set(points)
        while len(points) < n:
            choices = [add(points[-1], d) for d in DIRECTIONS
                       if add(points[-1], d) not in occupied]
            if not choices:
                break
            point = rng.choice(choices)
            points.append(point)
            occupied.add(point)
        if len(points) == n:
            return tuple(points)
    raise RuntimeError("Unable to grow a self-avoiding walk")


def contact_pairs(sequence: str, fold: Fold) -> Tuple[Tuple[int, int], ...]:
    occupied = {point: i for i, point in enumerate(fold)}
    contacts = []
    for i, point in enumerate(fold):
        if sequence[i] != "H":
            continue
        for d in DIRECTIONS:
            j = occupied.get(add(point, d), -1)
            if j > i + 1 and sequence[j] == "H":
                contacts.append((i, j))
    return tuple(sorted(contacts))


class Scorer:
    """Counts every scored structure, including local-neighbour evaluations."""
    def __init__(self, sequence: str, checkpoint: int = 0):
        self.sequence = sequence
        self.calls = 0
        self.started = time.perf_counter()
        self.checkpoint = checkpoint
        self.budget_snapshot = None
        self.best_energy = 0
        self.best_fold = None
        self.best_call = 0
        self.events = []

    def observe(self, fold: Fold, energy: int) -> None:
        if self.best_fold is None or energy < self.best_energy:
            self.best_energy, self.best_fold = energy, normalize(fold)
            self.best_call = self.calls
            self.events.append([self.calls, energy, time.perf_counter() - self.started])
        if self.checkpoint and self.calls == self.checkpoint:
            self.budget_snapshot = {
                "energy": self.best_energy, "fold": self.best_fold,
                "best_call": self.best_call, "calls": self.calls,
                "seconds": time.perf_counter() - self.started,
            }

    def energy(self, fold: Fold) -> int:
        self.calls += 1
        energy = -len(contact_pairs(self.sequence, fold))
        self.observe(fold, energy)
        return energy

    def delta(self, fold: Fold, occupied: Dict[Point, int],
              changes: Dict[int, Point], base_energy: int = None) -> int:
        """Exact incremental energy difference for one/two monomer moves."""
        self.calls += 1
        relocated = {point: i for i, point in changes.items()}
        old_contacts, new_contacts = set(), set()
        for i, new_point in changes.items():
            if self.sequence[i] != "H":
                continue
            for d in DIRECTIONS:
                old_j = occupied.get(add(fold[i], d), -1)
                if old_j >= 0 and abs(old_j - i) > 1 and self.sequence[old_j] == "H":
                    old_contacts.add(tuple(sorted((i, old_j))))
                neighbor = add(new_point, d)
                new_j = relocated.get(neighbor)
                if new_j is None:
                    new_j = occupied.get(neighbor, -1)
                    if new_j in changes:
                        new_j = -1
                if new_j >= 0 and abs(new_j - i) > 1 and self.sequence[new_j] == "H":
                    new_contacts.add(tuple(sorted((i, new_j))))
        delta = len(old_contacts) - len(new_contacts)
        if base_energy is not None:
            energy = base_energy + delta
            if self.best_fold is None or energy < self.best_energy:
                candidate = tuple(changes.get(i, p) for i, p in enumerate(fold))
                self.observe(candidate, energy)
            elif self.checkpoint and self.calls == self.checkpoint:
                self.observe(fold, base_energy)
        return delta


def local_moves(fold: Fold) -> Iterable[Dict[int, Point]]:
    """Complete end, square-corner and two-site crankshaft neighborhood."""
    n = len(fold)
    occupied = set(fold)
    for endpoint, anchor in ((0, 1), (n - 1, n - 2)):
        for d in DIRECTIONS:
            candidate = add(fold[anchor], d)
            if candidate not in occupied:
                yield {endpoint: candidate}
    for i in range(1, n - 1):
        if distance(fold[i - 1], fold[i + 1]) == 2:
            candidate = sub(add(fold[i - 1], fold[i + 1]), fold[i])
            if candidate not in occupied and distance(candidate, fold[i - 1]) == 1:
                yield {i: candidate}
    for i in range(1, n - 2):
        a, b = fold[i - 1], fold[i + 2]
        if distance(a, b) != 1:
            continue
        axis = sub(b, a)
        for d in DIRECTIONS:
            if sum(x * y for x, y in zip(axis, d)):
                continue
            c, e = add(a, d), add(b, d)
            if c not in occupied and e not in occupied:
                yield {i: c, i + 1: e}


def hill_climb(fold: Fold, energy: int, scorer: Scorer) -> Tuple[Fold, int, int]:
    """Steepest strict descent to a true optimum of local_moves, no cutoff.

    Equal-energy plateaus are deliberately not traversed. Since E is an integer
    bounded below, this procedure terminates after finitely many improvements.
    """
    improvements = 0
    while True:
        occupied = {point: i for i, point in enumerate(fold)}
        best_delta, best_change = 0, None
        for change in local_moves(fold):
            delta = scorer.delta(fold, occupied, change, energy)
            if delta < best_delta:
                best_delta, best_change = delta, change
        if best_change is None:
            return normalize(fold), energy, improvements
        fold = tuple(best_change.get(i, point) for i, point in enumerate(fold))
        energy += best_delta
        improvements += 1


def rotations() -> Tuple[Tuple[Tuple[int, ...], Tuple[int, ...]], ...]:
    result = []
    for permutation in itertools.permutations(range(3)):
        inversions = sum(permutation[i] > permutation[j]
                         for i in range(3) for j in range(i + 1, 3))
        parity = (-1) ** inversions
        for signs in itertools.product((-1, 1), repeat=3):
            if parity * signs[0] * signs[1] * signs[2] == 1:
                result.append((permutation, signs))
    return tuple(result)


ROTATIONS = rotations()


def rotate(point: Point, rotation) -> Point:
    permutation, signs = rotation
    return tuple(point[permutation[k]] * signs[k] for k in range(3))


def pivot_mutation(fold: Fold, rng: random.Random) -> Fold:
    for _ in range(12):
        pivot = rng.randrange(len(fold) - 1)
        rotation = rng.choice(ROTATIONS)
        anchor = fold[pivot]
        suffix = tuple(add(anchor, rotate(sub(p, anchor), rotation))
                       for p in fold[pivot + 1:])
        if not set(fold[:pivot + 1]).intersection(suffix):
            candidate = fold[:pivot + 1] + suffix
            if candidate != fold:
                return candidate
    return fold


def regrow_mutation(fold: Fold, rng: random.Random) -> Fold:
    cut = rng.randrange(max(1, len(fold) - 12), len(fold))
    prefix = fold[:cut]
    for _ in range(6):
        points, occupied = list(prefix), set(prefix)
        while len(points) < len(fold):
            choices = [add(points[-1], d) for d in DIRECTIONS
                       if add(points[-1], d) not in occupied]
            if not choices:
                break
            point = rng.choice(choices)
            points.append(point)
            occupied.add(point)
        if len(points) == len(fold):
            return tuple(points)
    return fold


def crossover(a: Fold, b: Fold, rng: random.Random) -> Fold:
    """Prefix of A plus translated/rotated suffix of B, reject collisions."""
    for _ in range(8):
        cut = rng.randrange(1, len(a) - 1)
        rotation = rng.choice(ROTATIONS)
        suffix = tuple(add(a[cut], rotate(sub(p, b[cut]), rotation))
                       for p in b[cut + 1:])
        if not set(a[:cut + 1]).intersection(suffix):
            return a[:cut + 1] + suffix
    return a


def mutate(fold: Fold, rng: random.Random) -> Fold:
    return pivot_mutation(fold, rng) if rng.random() < 0.65 else regrow_mutation(fold, rng)


def contact_signature(sequence: str, fold: Fold) -> Tuple[Tuple[int, int], ...]:
    """Rigid-rotation-invariant diversity summary (not a unique conformation ID)."""
    return contact_pairs(sequence, fold)
