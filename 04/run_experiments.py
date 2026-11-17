"""Reproduce exact search comparisons, decimal verification, and figures."""
from __future__ import annotations

import argparse
import csv
import json
import platform
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from solver import meet_in_middle, search

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
METHODS = ["dfs", "bfs", "astar", "astar_guided"]
LABELS = ["DFS", "BFS", "A*", "A* + informed tie"]
COLORS = ["#8894a7", "#ea9650", "#3a9e91", "#3368a5"]


def decimal_error(value: Fraction) -> dict:
    with localcontext() as ctx:
        ctx.prec = 60
        val = Decimal(value.numerator) / Decimal(value.denominator)
        return {"fraction": str(value), "decimal": str(val), "absolute_error": str(abs(val - Decimal(2).sqrt()))}


def verify_course_examples() -> dict:
    """Transcribe the three expressions explicitly; never use eval()."""
    ordered = 1 + Fraction(2 * 6, 24 + 5 - Fraction(720 * (7 + 8), 362880))
    reordered_a = (3 - Fraction(1, 10)) * (2 - Fraction(4, Fraction(40320, 6) + 7)) / (5 - Fraction(9, 10))
    reordered_b = (Fraction(9, 10) * (5 + 6)) / (7 + Fraction(6) * Fraction(24, 10) / (40320 + 1))
    return {"ordered": decimal_error(ordered), "reordered_a": decimal_error(reordered_a), "reordered_b": decimal_error(reordered_b)}


def plot_search(rows: list) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.3, 3.8))
    cases = list(dict.fromkeys(r["digits"] for r in rows))
    width = .19
    for i, (method, label, color) in enumerate(zip(METHODS, LABELS, COLORS)):
        subset = [r for r in rows if r["method"] == method]
        x = np.arange(len(cases)) + (i - 1.5) * width
        bars = axes[0].bar(x, [r["expanded"] for r in subset], width, color=color, label=label)
        for bar, result in zip(bars, subset):
            if not result["success"]:
                bar.set_hatch("///")
                bar.set_edgecolor("white")
        axes[1].bar(x, [r["peak_frontier"] for r in subset], width, color=color)
    for ax in axes:
        ax.set_xticks(np.arange(len(cases)))
        ax.set_xticklabels([f"n={len(x)}" for x in cases])
        ax.set_yscale("log")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.15)
    axes[0].set_ylabel("Expanded states (log scale)")
    axes[1].set_ylabel("Peak frontier entries (log scale)")
    axes[0].set_title("Common graph, fixed successor order")
    axes[1].set_title("Frontier is not total memory")
    axes[0].legend(fontsize=8, loc="upper left")
    fig.text(.5, .015, "Hatching: no goal within 100,000 expansions. Tolerances: 0.1, 0.01, 0.001, 0.001.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(OUT / "search_comparison.pdf", bbox_inches="tight")
    fig.savefig(OUT / "search_comparison.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_precision(results: list) -> None:
    fig, ax = plt.subplots(figsize=(7.3, 3.7))
    for i, result in enumerate(results):
        ordered = result["digits"] == "123456789"
        ax.scatter(result["operators"], float(result["error_decimal"]), s=75,
                   color=COLORS[3] if ordered else COLORS[1], marker="o" if ordered else "D")
        ax.annotate(f'{result["digits"]} / {result["split"]}',
                    (result["operators"], float(result["error_decimal"])),
                    xytext=(5, (i % 2) * 10 - 15), textcoords="offset points", fontsize=7)
    reference_error = float(verify_course_examples()["ordered"]["absolute_error"])
    ax.axhline(reference_error, color="#8b95a3", linestyle="--", lw=1, label="Course ordered example")
    ax.set_yscale("log")
    ax.set_xlabel("Arithmetic operators + factorials")
    ax.set_ylabel("Absolute error against sqrt(2)")
    ax.set_title("Accuracy and syntactic simplicity are different objectives")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.15)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "precision.pdf", bbox_inches="tight")
    fig.savefig(OUT / "precision.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(4, 4.8))
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 6)
    ax.axis("off")
    boxes = [(.25, 4.9, 3.5, .8, "Ordered digits: 1234 | 56789"),
             (.25, 3.5, 3.5, .8, "Exact interval DP\nFraction -> shortest witness"),
             (.25, 2.1, 3.5, .8, "Sort right values\nSearch inverse target"),
             (.25, .15, 3.5, 1.35, "a / b ≈ sqrt(2)\nSearch b near a / sqrt(2).\nCheck adjacent candidates.\nVerify at 60 decimal digits.")]
    for x, y, w, h, text in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=.06", edgecolor="#3368a5", facecolor="#edf3f9"))
        ax.text(x + w / 2, y + h / 2, text, va="center", ha="center", fontsize=11)
    for start, end in [((2, 4.8), (2, 4.4)), ((2, 3.4), (2, 3)), ((2, 2), (2, 1.6))]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, color="#3368a5"))
    fig.tight_layout()
    fig.savefig(OUT / "mitm_pipeline.pdf", bbox_inches="tight")
    fig.savefig(OUT / "mitm_pipeline.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=100000)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    rows = []
    for digits, eps in [("123", .1), ("1234", .01), ("12345", .001), ("123456789", .001)]:
        for method in METHODS:
            result = search(digits, method, eps, args.budget)
            rows.append(result)
            print(digits, method, result["success"], result["expanded"], flush=True)
    approximations = []
    for digits, split in [("123456789", 4), ("123456789", 5), ("987654321", 4), ("371526498", 4), ("824613975", 4)]:
        result = meet_in_middle(digits, split)
        approximations.append(result)
        print(digits, split, result["error_decimal"], result["expression"], flush=True)
    payload = {
        "python": platform.python_version(), "platform": platform.platform(),
        "budget": args.budget, "grammar": "ordered leaves, decimal or single-digit factorial; binary + - * /",
        "absolute_value_bound": 10**9, "denominator_bits": 80,
        "search": rows, "mitm": approximations, "course_examples": verify_course_examples(),
        "total_seconds": perf_counter() - start,
    }
    (OUT / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    with (OUT / "search.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plot_search(rows)
    plot_precision(approximations)
    plot_pipeline()
    print("saved", OUT, flush=True)


if __name__ == "__main__":
    main()
