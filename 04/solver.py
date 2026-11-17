"""Exact, bounded arithmetic-expression search for the Komachi puzzle.

No eval(), floating-point state keys, hidden random seeds, or tolerance-based
deduplication are used. A restricted grammar makes every comparison finite.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import deque
from dataclasses import dataclass
from fractions import Fraction
from heapq import heappop, heappush
from itertools import count
from math import factorial, sqrt
from time import perf_counter
from typing import Dict, Iterable, List, Optional, Tuple

TARGET = sqrt(2)
LIMIT = 10**9
OPS = ("+", "-", "*", "/")


@dataclass(frozen=True)
class Expr:
    value: Fraction
    text: str
    operators: int = 0


def combine(a: Expr, b: Expr, op: str) -> Optional[Expr]:
    if op == "+":
        value = a.value + b.value
    elif op == "-":
        value = a.value - b.value
    elif op == "*":
        value = a.value * b.value
    elif op == "/" and b.value:
        value = a.value / b.value
    else:
        return None
    if abs(value) > LIMIT or value.denominator.bit_length() > 80:
        return None
    return Expr(value, f"({a.text}{op}{b.text})", a.operators + b.operators + 1)


def leaves(digits: str) -> Iterable[Expr]:
    """Concatenation, at most one decimal point, or a single-digit factorial.

    A trailing decimal point is omitted because it duplicates the integer.
    Decimal digits are exact rationals; e.g. .12 == 3/25.
    """
    yield Expr(Fraction(int(digits)), digits)
    for place in range(len(digits)):
        text = digits[:place] + "." + digits[place:]
        yield Expr(Fraction(int(digits), 10 ** (len(digits) - place)), text)
    if len(digits) == 1:
        yield Expr(Fraction(factorial(int(digits))), digits + "!", 1)


@dataclass(frozen=True)
class State:
    position: int
    stack: Tuple[Expr, ...]

    def key(self) -> tuple:
        return self.position, tuple(e.value for e in self.stack)


def successors(state: State, digits: str) -> Iterable[State]:
    # Fixed ordering is shared by all frontier policies.
    for end in range(state.position + 1, len(digits) + 1):
        for expr in leaves(digits[state.position:end]):
            yield State(end, state.stack + (expr,))
    if len(state.stack) >= 2:
        for op in OPS:
            expr = combine(state.stack[-2], state.stack[-1], op)
            if expr is not None:
                yield State(state.position, state.stack[:-2] + (expr,))


def lower_bound(state: State, digits: str) -> int:
    """Admissible and consistent lower bound on remaining RPN actions.

    If digits remain, one push can consume the whole suffix and k reductions
    merge it with a k-entry stack. Otherwise k-1 reductions are necessary.
    Any actual completion uses at least that many actions.
    """
    k = len(state.stack)
    return k + 1 if state.position < len(digits) else max(0, k - 1)


def guidance(state: State, digits: str) -> float:
    """Non-admissible *tie breaker*, never part of A*'s primary f score.

    It checks proximity after a relaxed single binary operation with a suffix
    leaf. This changes ordering inside one f contour, not A* optimality.
    """
    if not state.stack:
        return float("inf")
    candidates = [abs(float(state.stack[-1].value) - TARGET)]
    if state.position < len(digits):
        for b in leaves(digits[state.position:]):
            for op in OPS:
                expr = combine(state.stack[-1], b, op)
                if expr is not None:
                    candidates.append(abs(float(expr.value) - TARGET))
    elif len(state.stack) >= 2:
        for op in OPS:
            expr = combine(state.stack[-2], state.stack[-1], op)
            if expr is not None:
                candidates.append(abs(float(expr.value) - TARGET))
    return min(candidates)


def search(digits: str, method: str, tolerance: float, budget: int) -> dict:
    """Return first goal or a right-censored result after ``budget`` expansions.

    Goal tests occur on pop. Expanded counts only non-stale states whose
    successors were enumerated; generated counts admitted frontier entries.
    Peak frontier counts entries, including stale A* entries. CPU cost of the
    heuristic is included in wall time. Memory includes the closed dictionary.
    """
    if method not in {"bfs", "dfs", "astar", "astar_guided"}:
        raise ValueError(method)
    start = State(0, ())
    serial = count()
    fifo = deque([(start, 0)])
    heap = []
    is_astar = method.startswith("astar")
    if is_astar:
        heappush(heap, (lower_bound(start, digits), 0.0, next(serial), 0, start))
    best_g = {start.key(): 0}
    expanded, generated, peak = 0, 1, 1
    best = None
    found = None
    begin = perf_counter()
    while (heap if is_astar else fifo):
        if is_astar:
            _, _, _, g, state = heappop(heap)
        elif method == "bfs":
            state, g = fifo.popleft()
        else:
            state, g = fifo.pop()
        if g != best_g.get(state.key()):
            continue
        if state.position == len(digits) and len(state.stack) == 1:
            expr = state.stack[0]
            if best is None or abs(float(expr.value) - TARGET) < abs(float(best.value) - TARGET):
                best = expr
            if abs(float(expr.value) - TARGET) <= tolerance:
                found = expr
                break
        if expanded >= budget:
            break
        expanded += 1
        children = list(successors(state, digits))
        # DFS pops from the right, so reverse to respect the common order.
        if method == "dfs":
            children.reverse()
        for child in children:
            key, new_g = child.key(), g + 1
            if key in best_g and (not is_astar or best_g[key] <= new_g):
                continue
            best_g[key] = new_g
            generated += 1
            if is_astar:
                tie = guidance(child, digits) if method == "astar_guided" else 0.0
                heappush(heap, (new_g + lower_bound(child, digits), tie, next(serial), new_g, child))
            else:
                fifo.append((child, new_g))
        peak = max(peak, len(heap if is_astar else fifo))
    expr = found or best
    return {
        "digits": digits, "method": method, "tolerance": tolerance,
        "budget": budget, "success": found is not None, "expanded": expanded,
        "generated": generated, "peak_frontier": peak, "visited_states": len(best_g),
        "seconds": perf_counter() - begin, "actions": g if found else None,
        "expression": expr.text if expr else None,
        "value": float(expr.value) if expr else None,
        "numerator": expr.value.numerator if expr else None,
        "denominator": expr.value.denominator if expr else None,
        "absolute_error": abs(float(expr.value) - TARGET) if expr else None,
    }


def catalogue(digits: str) -> Dict[Fraction, Expr]:
    """Exact interval DP; all parenthesizations and grammar leaves, no beam.

    Different syntactic expressions with the same rational value are merged,
    keeping the expression with the fewest printed operators then characters.
    LIMIT and denominator bit bounds are the same as in RPN search.
    """
    table: Dict[Tuple[int, int], Dict[Fraction, Expr]] = {}
    for width in range(1, len(digits) + 1):
        for start in range(len(digits) - width + 1):
            end = start + width
            values: Dict[Fraction, Expr] = {}

            def insert(expr: Expr) -> None:
                old = values.get(expr.value)
                if old is None or (expr.operators, len(expr.text), expr.text) < (old.operators, len(old.text), old.text):
                    values[expr.value] = expr

            for expr in leaves(digits[start:end]):
                insert(expr)
            for split in range(start + 1, end):
                for a in table[start, split].values():
                    for b in table[split, end].values():
                        for op in OPS:
                            expr = combine(a, b, op)
                            if expr is not None:
                                insert(expr)
            table[start, end] = values
    return table[0, len(digits)]


def meet_in_middle(digits: str, split: int = 4) -> dict:
    """Search four root operations via sorted right-side values.

    For fixed left value a, an optimal b for each root operation is adjacent to
    the ideal inverse target b*. Division's pole at zero and a == 0 are handled
    by searching both signs plus interval endpoints. float is only the index
    estimate; exact rationals and high-precision Decimal verify final errors.
    """
    from decimal import Decimal, localcontext

    begin = perf_counter()
    left, right = catalogue(digits[:split]), catalogue(digits[split:])
    right_values = sorted(right)
    right_floats = [float(v) for v in right_values]
    best = None
    top: List[Expr] = []
    probes = 0
    for a in left.values():
        x = float(a.value)
        for op in OPS:
            ideal = TARGET - x if op == "+" else x - TARGET if op == "-" else TARGET / x if op == "*" and x else x / TARGET if op == "/" else None
            if ideal is None:
                continue
            index = bisect_left(right_floats, ideal)
            candidates = {0, len(right_values) - 1}
            candidates.update(range(max(0, index - 2), min(len(right_values), index + 3)))
            for i in candidates:
                probes += 1
                expr = combine(a, right[right_values[i]], op)
                if expr is not None:
                    error = abs(float(expr.value) - TARGET)
                    if best is None or (error, expr.operators, len(expr.text)) < (abs(float(best.value) - TARGET), best.operators, len(best.text)):
                        best = expr
                        top.append(expr)
    assert best is not None
    with localcontext() as ctx:
        ctx.prec = 60
        value = Decimal(best.value.numerator) / Decimal(best.value.denominator)
        error = abs(value - Decimal(2).sqrt())
    return {
        "digits": digits, "split": split, "left_values": len(left),
        "right_values": len(right), "probes": probes,
        "expression": best.text, "numerator": best.value.numerator,
        "denominator": best.value.denominator, "operators": best.operators,
        "value_decimal": str(value), "error_decimal": str(error),
        "seconds": perf_counter() - begin,
        "improvements": [{"expression": e.text, "error": abs(float(e.value) - TARGET), "operators": e.operators} for e in top],
    }
