# 05 — Learning, inheritance, and three-dimensional HP folding

Three genuine genetic algorithms search **feasible self-avoiding walks on the cubic lattice**. They differ only in how local learning changes fitness and inherited genes. This is an independently written small research implementation; it does not claim to reproduce a published solver or predict real protein structures.

## Reproduce

From the repository root (Python 3.9+, NumPy and Matplotlib):

```bash
python3 -m unittest discover -s 05 -v
python3 05/exact_toy.py
python3 05/experiment.py --seeds 5 --budget 30000 --population 32 --generations 60
python3 05/analyze.py
python3 05/time_to_threshold.py
```

The experiment resumes existing per-run JSON files only if their population, evaluation-budget and generation settings agree. To run a different configuration, use a separate directory, e.g. `--output 05/results_extended`. The checked-in `results/manifest.json` records settings and host information. Repeated seeds reproduce scores and conformations; runtimes vary with the host. Measured timings start just before initial-population scoring, after the common random-walk initialization, and include subsequent scoring, local search, variation, selection and in-run logging. Other report experiments may share the host.

## What is represented and scored?

For sequence `s` and residue coordinates `r`, the score is minus the number of nonconsecutive H–H contacts at Manhattan distance one. Chain bonds do not count. Every conformation has distinct integer coordinates and unit-length covalent bonds. Off-lattice positions, residue overlap and invalid-fold penalties are absent.

- `hp_model.py`: parser, exact scoring and incremental score differences; feasible variation; exhaustive local neighborhood; strict steepest hill climbing.
- `experiment.py`: population evolution, inheritance rules, independent initialization RNG, counters and raw experiment logging.
- `exact_toy.py`: an exhaustive oracle for the 10-residue easy control.
- `test_hp_model.py`: tests for source-data lengths, structural invariants, exact energy deltas, local optimality, determinism and inheritance distinctions.
- `analyze.py`: summaries, plots and the report table, derived from the raw JSON files.
- `benchmarks.json`: source notation preserved verbatim, including detected inconsistencies.

The genotype is an anchored tuple of 3D coordinates (equivalently, its sequence of cubic-lattice bond directions). Suffix crossover attaches a translated, randomly rotated suffix of parent B to a prefix of parent A. Colliding children are rejected; after eight failed attempts it returns parent A. Mutation uses a feasible suffix pivot (65%) or random regrowth of up to 12 tail residues (35%). Pivot attempts are capped at 12, regrowth attempts at six; failure leaves the parent unchanged. There are 24 proper cubic rotations. All methods have the same variation settings, tournament selection of size three, two elites, crossover probability 0.8, mutation probability 0.9, and 3% immigration. Elites are not reevaluated.

Local learning exhausts end-residue moves, square-corner flips, and two-residue crankshaft moves. It accepts the largest strictly negative energy difference, rescans, and terminates when **no move in this explicitly defined neighborhood improves energy**. There is no iteration cutoff. Energy is integer and bounded below, so strict descent terminates. Equal-energy plateaus and larger pivot/regrowth moves are outside this local-optimality claim. Exact incremental updates touch one or two residues and are checked against full recomputation.

## The three rules

| Rule | Selection energy | Genes used for offspring |
|---|---|---|
| Darwin | Original genotype's energy | Original genotype |
| Baldwin | Locally improved phenotype's energy | Original genotype |
| Lamarck | Locally improved phenotype's energy | Improved genotype |

Baldwin elites retain the **original** genotype. Storing the learned phenotype as the inherited genotype would silently turn this treatment into Lamarck evolution. Both the population's raw genotype scores and learned fitness scores are logged to make this distinction inspectable. A separate best-so-far conformation archive records every evaluated feasible structure; it is used for reporting, never for parent selection or reinjection.

## Fair comparison means specifying the resource

The same five initialization seeds (0–4) are used for every method and sequence; local search is deterministic. Two checkpoints are recorded in each run:

1. Exactly **30,000 scored conformations**, counting all valid local-search probes, including P-only moves with zero energy difference. The archive is snapshotted at the exact threshold, even if that occurs inside local search. Later evaluations never leak into this score.
2. Exactly **60 completed generations**, including the common initial population. Local search still reaches a defined local optimum for every evaluated individual. Runs continue until both checkpoints have been collected; this does not make the checkpoint results interchangeable.

The full runs contain 9,939,381 score evaluations. A complete local-learning operation can continue beyond the first evaluation cutoff so that the separate generation experiment remains well-defined. Results at the evaluation cutoff use only the saved exact-threshold snapshot. This also avoids falsely describing an interrupted local search as locally optimal.

A score evaluation is **not equal CPU work**: an incremental one/two-residue update is much cheaper than rebuilding a full fold's contacts, and feasible crossover/regrowth adds work that the evaluation counter does not capture. Consequently, plots also show measured runtime and a common 0.5-second horizon for each 48-mer. Time comparisons describe this Python implementation and machine, not an algorithm-independent complexity result. Generation count alone favors algorithms that do more work per generation.

## Data validation and outcomes

The assignment's source page was accessed on 2026-11-17. Expanding repetition notation reveals that its nominal 48-mer entries **#1 and #10 contain 47 residues**. They remain in `benchmarks.json` with warnings and are excluded from the 48-mer experiment. Entries #2–#9 have length 48. The experiment uses #2, #3, #4 (reference energies −34, −34, −33 as stated on the assignment page) plus author-created 10- and 20-residue controls. Source reference energies are comparison targets, not proven anew here.

The 10-mer's exact optimum is **−4**: exhaustive enumeration inspects 308,981 complete walks with first bond fixed to +x. All three methods reach it in all five runs. On the 48-mers, the ranking changes with the resource: Darwin is strongest or similar at 30,000 score calls, learned methods improve most of the 60-generation results, and Lamarck is strongest at the common measured 0.5-second horizon in this run. The source's 48-mer reference minima were **not reached**. No global optimality claim is made for the 20-mer or 48-mers.

See `results/summary.csv` / `summary.json` for all means, sample standard deviations and ranges; raw `*_METHOD_SEED.json` files preserve learning and diversity histories. Five seeds support a descriptive comparison, not a universal ordering or a statistical significance claim. Conformation examples in `folds_3d` are the best seed at **generation 60** for each method, not cherry-picked results from unequal checkpoints.

`time_to_threshold.py` adds a supplementary **post-hoc** target of E ≤ −20 for s48_02 within 60 generations. It reports success counts (Darwin 3/5, Baldwin 5/5, Lamarck 5/5), event-based first-hit time and generation-end first-hit records. Medians condition on success; nonhits remain explicitly censored. This target is not the global optimum.

## References

- Assignment and original compressed sequence list: <https://www.iba.t.u-tokyo.ac.jp/iba/AI/report.html>
- R. Unger and J. Moult, “Genetic Algorithms for Protein Folding Simulations,” *Journal of Molecular Biology* 231(1), 75–81 (1993), DOI: [10.1006/jmbi.1993.1258](https://doi.org/10.1006/jmbi.1993.1258). This motivates population-based conformation search; the present representation/operators and learning comparison are independently implemented.
