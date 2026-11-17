"""Generate publication figures and descriptive statistics from saved runs."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/ai05-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

from hp_model import contact_pairs, expand_sequence

HERE = Path(__file__).resolve().parent
METHODS = ("darwin", "baldwin", "lamarck")
LABELS = {"darwin": "Darwin", "baldwin": "Baldwin", "lamarck": "Lamarck"}
COLORS = {"darwin": "#2878B5", "baldwin": "#E58A2B", "lamarck": "#349D83"}


def stats(values):
    values = np.array(values, dtype=float)
    return {"mean": float(values.mean()), "median": float(np.median(values)),
            "min": float(values.min()), "max": float(values.max()),
            "sd": float(values.std(ddof=1)) if len(values) > 1 else 0.0}


def step_values(events, grid):
    values = []
    for x in grid:
        eligible = [row[1] for row in events if row[0] <= x]
        values.append(min(eligible) if eligible else 0)
    return np.array(values)


def save(fig, path):
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(path.with_suffix(".png"), dpi=190, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "results")
    args = parser.parse_args()
    out = args.results
    runs = json.loads((out / "all_results.json").read_text())
    manifest = json.loads((out / "manifest.json").read_text())
    sequences = manifest["sequences"]
    groups = {(b["name"], m): sorted([r for r in runs if r["sequence_name"] == b["name"] and r["method"] == m], key=lambda r: r["seed"])
              for b in sequences for m in METHODS}
    summary = []
    for benchmark in sequences:
        name = benchmark["name"]
        target = -3 if name == "toy10" else (-10 if name == "toy20" else -20)
        horizon = 0.1 if name.startswith("toy") else 0.5
        for method in METHODS:
            sample = groups[name, method]
            hits = [[ev for ev in r["improvement_events"] if ev[1] <= target and ev[0] <= manifest["budget"]] for r in sample]
            row = {
                "sequence": name, "n": len(expand_sequence(benchmark["expression"])),
                "method": method, "seeds": len(sample),
                "reference_energy": benchmark.get("reference_energy"),
                "energy_at_budget": stats([r["budget"]["energy"] for r in sample]),
                "energy_at_generation": stats([r["generation"]["best_energy"] for r in sample]),
                "seconds_at_budget": stats([r["budget"]["seconds"] for r in sample]),
                "seconds_at_generation": stats([r["generation"]["seconds"] for r in sample]),
                "calls_at_generation": stats([r["generation"]["calls"] for r in sample]),
                "diversity_at_generation": stats([r["generation"]["contact_map_diversity"] for r in sample]),
                "target": target, "hit_count_at_budget": sum(bool(h) for h in hits),
                "wall_horizon_seconds": horizon,
                "energy_at_wall_horizon": stats([min(ev[1] for ev in r["improvement_events"] if ev[2] <= horizon) for r in sample]),
                "first_target_calls_successes": [h[0][0] for h in hits if h],
                "first_target_seconds_successes": [h[0][2] for h in hits if h],
            }
            summary.append(row)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (out / "summary.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["sequence", "method", "budget_energy_mean", "budget_energy_min", "budget_energy_max", "generation_energy_mean", "budget_seconds_mean", "generation_seconds_mean", "generation_calls_mean", "generation_diversity_mean", "target", "target_hit_count", "seeds"])
        for row in summary:
            writer.writerow([row["sequence"], row["method"], row["energy_at_budget"]["mean"], row["energy_at_budget"]["min"], row["energy_at_budget"]["max"], row["energy_at_generation"]["mean"], row["seconds_at_budget"]["mean"], row["seconds_at_generation"]["mean"], row["calls_at_generation"]["mean"], row["diversity_at_generation"]["mean"], row["target"], row["hit_count_at_budget"], row["seeds"]])

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "figure.facecolor": "white"})
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.7))
    grid = np.arange(0, manifest["budget"] + 1, max(1, manifest["budget"] // 200))
    for ax, benchmark in zip(axes.flat, sequences):
        for method in METHODS:
            values = np.array([step_values(r["improvement_events"], grid) for r in groups[benchmark["name"], method]])
            ax.step(grid, np.median(values, axis=0), where="post", color=COLORS[method], label=LABELS[method])
            ax.fill_between(grid, values.min(axis=0), values.max(axis=0), color=COLORS[method], alpha=0.10, step="post")
        ax.set_title(benchmark["name"])
        ax.set_xlabel("Scored conformations (including local probes)")
        ax.set_ylabel("Best energy (lower is better)")
        ax.grid(alpha=.2)
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(handles, labels, loc="upper center", bbox_to_anchor=(.5, .8), frameon=False, fontsize=13)
    axes.flat[-1].text(.5, .12, "Lines: median of 5 seeds\nShading: min-max range", ha="center", transform=axes.flat[-1].transAxes)
    fig.tight_layout()
    save(fig, out / "convergence_evaluations")

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    for ax, benchmark in zip(axes, sequences[2:]):
        for method in METHODS:
            sample = groups[benchmark["name"], method]
            values = np.array([[r["history"][g]["best_energy"] for g in range(manifest["generations"] + 1)] for r in sample])
            grid_g = np.arange(manifest["generations"] + 1)
            ax.plot(grid_g, np.median(values, axis=0), color=COLORS[method], label=LABELS[method])
            ax.fill_between(grid_g, values.min(axis=0), values.max(axis=0), color=COLORS[method], alpha=.10)
        ax.set_title(benchmark["name"])
        ax.set_xlabel("Generations")
        ax.set_ylabel("Best energy")
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    save(fig, out / "convergence_generations")

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    time_grid = np.linspace(0.005, .5, 200)
    for ax, benchmark in zip(axes, sequences[2:]):
        for method in METHODS:
            values = np.array([step_values([[ev[2], ev[1]] for ev in r["improvement_events"]], time_grid)
                               for r in groups[benchmark["name"], method]])
            ax.plot(time_grid, np.median(values, axis=0), color=COLORS[method], label=LABELS[method])
            ax.fill_between(time_grid, values.min(axis=0), values.max(axis=0), color=COLORS[method], alpha=.10)
        ax.set_title(benchmark["name"])
        ax.set_xlabel("Measured wall seconds")
        ax.set_ylabel("Best energy")
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    save(fig, out / "convergence_time")

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    labels = [b["name"] for b in sequences]
    x = np.arange(len(labels))
    for offset, method in enumerate(METHODS):
        rows = [next(row for row in summary if row["sequence"] == name and row["method"] == method) for name in labels]
        for ax, key in zip(axes, ("seconds_at_budget", "calls_at_generation")):
            ax.bar(x + (offset - 1) * .25, [r[key]["mean"] for r in rows], .25,
                   color=COLORS[method], label=LABELS[method])
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.set_yscale("log")
            ax.grid(axis="y", alpha=.2)
    axes[0].set_ylabel("Mean wall seconds at evaluation cutoff")
    axes[1].set_ylabel("Mean scored conformations at generation 60")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    save(fig, out / "effort")

    # A matched seed demonstrates the difference between genotype and phenotype.
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for method in METHODS:
        run = groups["s48_02", method][0]
        history = run["history"][:manifest["generations"] + 1]
        axes[0].plot([h["generation"] for h in history], [h["contact_map_diversity"] for h in history], color=COLORS[method], label=LABELS[method])
    run = groups["s48_02", "baldwin"][0]
    history = run["history"][:manifest["generations"] + 1]
    axes[1].plot([h["generation"] for h in history], [h["population_mean_raw"] for h in history], color="#91454D", label="Mean genotype energy")
    axes[1].plot([h["generation"] for h in history], [h["population_mean_fitness"] for h in history], color=COLORS["baldwin"], label="Mean learned fitness energy")
    axes[0].set_ylabel("Distinct genotype contact maps /\npopulation size")
    axes[1].set_ylabel("Population mean energy")
    for ax in axes:
        ax.set_xlabel("Generations (s48_02, seed 0)")
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.tight_layout()
    save(fig, out / "learning_and_diversity")

    fig = plt.figure(figsize=(12, 4))
    for i, method in enumerate(METHODS):
        run = min(groups["s48_02", method], key=lambda r: r["generation"]["best_energy"])
        fold = np.array(run["generation"]["fold"])
        sequence = run["sequence"]
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        ax.plot(fold[:, 0], fold[:, 1], fold[:, 2], color="#8A93A0", linewidth=1.3, zorder=1)
        for a, b in contact_pairs(sequence, tuple(map(tuple, fold))):
            ax.plot(fold[[a, b], 0], fold[[a, b], 1], fold[[a, b], 2], "--", color="#D15B5B", alpha=.5, linewidth=.8)
        h = np.array([c == "H" for c in sequence])
        ax.scatter(*fold[h].T, c="#E36649", s=45, edgecolor="white", linewidth=.3, depthshade=False)
        ax.scatter(*fold[~h].T, c="#83B9CE", s=27, edgecolor="white", linewidth=.3, depthshade=False)
        ax.set_title("{}: E={} (seed {})".format(LABELS[method], run["generation"]["best_energy"], run["seed"]))
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z")
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            axis.set_major_locator(MaxNLocator(nbins=4, integer=True))
        spans = np.ptp(fold, axis=0)
        ax.set_box_aspect(np.maximum(spans, 1))
        ax.view_init(25, 38)
    fig.tight_layout()
    save(fig, out / "folds_3d")

    # Report table is generated from the same raw JSON as the plots.
    lines = ["\\begin{tabular}{llrrr}", "\\hline", "配列 & 手法 & 同評価数 & 同世代数 & 秒\\\\", "\\hline"]
    for row in summary:
        name = row["sequence"].replace("_", r"\_")
        lines.append("{} & {} & {:.1f} & {:.1f} & {:.2f}\\\\".format(name, LABELS[row["method"]], row["energy_at_budget"]["mean"], row["energy_at_generation"]["mean"], row["seconds_at_generation"]["mean"]))
    lines += ["\\hline", "\\end{tabular}"]
    (out / "table.tex").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
