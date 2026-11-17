"""Three inheritance rules on exactly the same feasible 3D HP search space.

Run from anywhere: python3 05/experiment.py --seeds 5 --budget 30000
Every scored feasible conformation counts toward the evaluation budget, including
local search probes. Population RNG uses a separate initialization stream.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import platform
import random
import statistics
import time

from hp_model import (Fold, Scorer, contact_pairs, contact_signature, crossover,
                      expand_sequence, hill_climb, mutate, normalize, random_fold,
                      valid)

HERE = Path(__file__).resolve().parent
METHODS = ("darwin", "baldwin", "lamarck")


@dataclass
class Individual:
    genotype: Fold
    phenotype: Fold
    raw_energy: int
    fitness_energy: int


def run(sequence: str, method: str, seed: int, population_size: int,
        generations: int, budget: int) -> dict:
    rng = random.Random(seed + 104729)
    init_rng = random.Random(seed)
    starts = [random_fold(len(sequence), init_rng) for _ in range(population_size)]
    scorer = Scorer(sequence, checkpoint=budget)

    def evaluate(genotype: Fold) -> Individual:
        genotype = normalize(genotype)
        raw = scorer.energy(genotype)
        if method == "darwin":
            return Individual(genotype, genotype, raw, raw)
        learned, energy, _ = hill_climb(genotype, raw, scorer)
        if method == "lamarck":
            return Individual(learned, learned, energy, energy)
        return Individual(genotype, learned, raw, energy)

    population = [evaluate(fold) for fold in starts]
    history = []
    generation = 0
    generation_snapshot = None

    def record() -> dict:
        signatures = {contact_signature(sequence, x.genotype) for x in population}
        return {
            "generation": generation, "calls": scorer.calls,
            "best_energy": scorer.best_energy,
            "population_best_raw": min(x.raw_energy for x in population),
            "population_best_fitness": min(x.fitness_energy for x in population),
            "population_mean_raw": statistics.mean(x.raw_energy for x in population),
            "population_mean_fitness": statistics.mean(x.fitness_energy for x in population),
            "contact_map_diversity": len(signatures) / population_size,
            "seconds": time.perf_counter() - scorer.started,
        }

    history.append(record())

    def tournament() -> Individual:
        return min(rng.sample(population, 3), key=lambda x: x.fitness_energy)

    while generation < generations or scorer.calls < budget:
        # Elites retain their original genotype (critical for Baldwin).
        children = sorted(population, key=lambda x: x.fitness_energy)[:2]
        while len(children) < population_size:
            parent_a, parent_b = tournament(), tournament()
            offspring = (crossover(parent_a.genotype, parent_b.genotype, rng)
                         if rng.random() < 0.8 else parent_a.genotype)
            if rng.random() < 0.9:
                offspring = mutate(offspring, rng)
            # A small fixed immigration rate is identical for all three rules.
            if rng.random() < 0.03:
                offspring = random_fold(len(sequence), rng)
            children.append(evaluate(offspring))
        population = children
        generation += 1
        row = record()
        history.append(row)
        if generation == generations:
            generation_snapshot = dict(row)
            generation_snapshot["fold"] = scorer.best_fold
        if generation > 10000:
            raise RuntimeError("No termination: check evaluation counter")

    assert scorer.budget_snapshot is not None
    for snapshot in (scorer.budget_snapshot, generation_snapshot):
        fold = tuple(tuple(p) for p in snapshot["fold"])
        assert valid(fold)
        assert -len(contact_pairs(sequence, fold)) == snapshot.get("energy", snapshot.get("best_energy"))
    return {
        "method": method, "seed": seed, "population_size": population_size,
        "generation_checkpoint": generations, "evaluation_budget": budget,
        "budget": scorer.budget_snapshot, "generation": generation_snapshot,
        "history": history, "improvement_events": scorer.events,
        "total_generations": generation, "total_calls": scorer.calls,
        "total_seconds": time.perf_counter() - scorer.started,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--budget", type=int, default=30000)
    parser.add_argument("--population", type=int, default=32)
    parser.add_argument("--generations", type=int, default=60)
    parser.add_argument("--names", nargs="+", default=["toy10", "toy20", "s48_02", "s48_03", "s48_04"])
    parser.add_argument("--output", type=Path, default=HERE / "results")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    benchmarks = json.loads((HERE / "benchmarks.json").read_text())
    selected = [b for b in benchmarks["sequences"] if b["name"] in args.names]
    if len(selected) != len(args.names):
        parser.error("Unknown or duplicate sequence names")
    manifest = {
        "timestamp_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": platform.python_version(), "platform": platform.platform(),
        "processor": platform.processor(), "population": args.population,
        "generations": args.generations, "budget": args.budget,
        "seeds": list(range(args.seeds)), "methods": METHODS,
        "timer_scope": "Starts immediately before initial population scoring, after the common random-walk initialization; includes all scoring, local search, variation, selection and logging in the run.",
        "notes": "Exact threshold best-so-far snapshots; complete local descent continues beyond cutoff for the separate generation experiment. CPU times are sequential per-run wall times on a shared host.",
        "sequences": selected,
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    rows = []
    for benchmark in selected:
        sequence = expand_sequence(benchmark["expression"])
        assert len(sequence) == (int(benchmark["name"][3:]) if benchmark["name"].startswith("toy") else 48)
        for seed in range(args.seeds):
            for method in METHODS:
                filename = args.output / (benchmark["name"] + "_" + method + "_" + str(seed) + ".json")
                if filename.exists():
                    result = json.loads(filename.read_text())
                    if (result["evaluation_budget"], result["population_size"], result["generation_checkpoint"]) != (args.budget, args.population, args.generations):
                        raise ValueError("Existing result has different settings: " + str(filename))
                else:
                    result = run(sequence, method, seed, args.population, args.generations, args.budget)
                    result["sequence_name"] = benchmark["name"]
                    result["sequence"] = sequence
                    result["reference_energy"] = benchmark.get("reference_energy")
                    filename.write_text(json.dumps(result, indent=2) + "\n")
                rows.append(result)
                print("{:<7} {:<7} seed={} E@eval={:3} E@gen={:3} calls={} seconds={:.2f}".format(
                    benchmark["name"], method, seed, result["budget"]["energy"],
                    result["generation"]["best_energy"], result["total_calls"], result["total_seconds"]), flush=True)
    (args.output / "all_results.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
