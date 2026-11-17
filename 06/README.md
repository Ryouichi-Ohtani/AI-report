# 06 — Triangle approximation with a reproducible genetic algorithm

Three original 64 × 64 RGB targets isolate different image properties: a hard-edged landscape, a curved fruit illustration, and a smooth color gradient with a small sharp disk. No external images, personal photos or copyrighted reference artwork are required.

## Reproduce

From the repository root, with NumPy, Pillow and Matplotlib installed:

```sh
python3 -m unittest discover -s 06 -p 'test_*.py' -v
MPLCONFIGDIR=/tmp/ai-report-mpl python3 06/run_experiments.py
python3 06/run_experiments.py --plot-only
python3 06/render_genome.py 06/results/runs/landscape_noisy_mae24_0.json --out 06/results/export_landscape
```

The main command resumes by skipping completed run JSON files. To change the experiment parameters, use a **new results directory or move the existing `results/runs/` aside**: the run filename is a stable dataset/configuration/seed identifier, not a complete configuration hash. `--plot-only` regenerates publication figures and summary tables from raw runs. The default is 205 runs, each at exactly 12,000 candidate renders, with seeds 0–4.

## Implementation

`triangle_ga.py` contains the genome, deterministic renderer, objective functions, genetic operators and steady-state `(mu + 1)` optimizer. `targets.py` creates all references. `run_experiments.py` fits genomes, evaluates frozen genomes against all test references, writes raw JSON/CSV and generates figures. `render_genome.py` exports the genome to PNG and SVG without optimization.

Each gene stores six vertex coordinates and three RGB values. Triangles are opaque and ordered: later triangles occlude earlier ones. A train-image-median background is fixed for each run. Grid initialization and occasional mean/median color repair use **training pixels only**; this is an image-informed hybrid GA, not a claim that random evolutionary search alone discovers a good initialization. Rasterization rounds vertex coordinates to pixel integers. The SVG export retains continuous coordinates and may therefore differ slightly along edges from the 64 × 64 evaluated raster.

Parents are selected by three-way tournament from a population of 12. One-point list crossover is attempted with probability 0.15. Every child is mutated and evaluated once. Elitist survival replaces the worst member only with a strictly better, nonduplicate objective value. Coordinates, colors and drawing order mutate; variable-length experiments also insert and delete triangles. The initial population is included in the render budget.

## Experiment matrix

The main 180 runs are 3 targets × 2 training conditions (clean / Gaussian noise with sigma=22 on the 0–255 scale) × 6 configurations × 5 seeds. The configurations are fixed 8/24/48 triangles with MAE; 24 with MSE; 24 with a declared edge-aware perceptual surrogate; and variable 2–48 triangles with that surrogate plus a 0.0007-per-triangle penalty (initialized with 12). Another 25 runs on the clean landscape vary population size (4/36), disable image-guided recoloring, or vary the variable-length penalty (0 / 0.0015). The guided flag affects mutation and insertion, while all variants share image-informed initialization.

The perceptual surrogate is weighted RGB MAE plus 0.35 × RGB finite-difference edge MAE. Pixel weights are 1 plus 3 times the local training-image edge magnitude. It is a transparent design choice, not a validated model of human beauty. The objective comparison also changes its corresponding color estimator: MSE uses mean colors, whereas MAE and the perceptual surrogate use median colors in initialization and guided color repair. It therefore compares these combined settings rather than isolating the effect of the loss alone. No human ratings or IEC experiment are claimed.

Independent noisy test data use a different noise seed. For noisy-training runs, the clean reference remains outside `evolve()` and measures denoising. For clean-training runs, that same reference is the training target, so clean-reference MAE is a training reconstruction error rather than a held-out score. The independently corrupted test reference, shifted related scenes and unrelated scenes remain outside `evolve()` in both conditions. These comparisons measure denoising and sensitivity to a frozen target, not a universal image-recognition model. All metrics use normalized [0,1] RGB. PSNR derives from MSE. Means and sample standard deviations across the five search seeds are in `results/summary.csv`; raw results retain genomes, render counts, attempted/surviving crossovers and complete sampled convergence traces. Wall time is machine-dependent and was measured while other report experiments could run concurrently.

## Outputs

- `results/reconstructions.pdf`: target/noise/three objectives/variable-length comparison (seed 0, declared in advance).
- `results/complexity.pdf`: triangle-count tradeoff, mean ± sample SD; clean training uses reconstruction error, while noisy training uses a held-out clean reference.
- `results/objectives.pdf`: held-out clean color and edge errors for noisy-training runs, mean ± sample SD; objectives are paired with their corresponding mean/median color estimators.
- `results/evolution_pareto.pdf`: normalized training convergence and penalty/count tradeoff. Different objectives are normalized to their own initial value, not equated as one metric.
- `results/progression.pdf`: one fixed seed at initialization and 3,000/6,000/12,000 renders.
- `results/runs/*.json`, `summary.csv`, `summary.json`, `metadata.json`: numerical provenance.
- `section.tex`: report section including findings and limitations.

## Primary reference

J. Berg et al., *Evolved Art with Transparent, Overlapping, and Geometric Shapes*, NAIS 2019, [arXiv:1904.06110](https://arxiv.org/abs/1904.06110). The use of geometric chromosomes and evolving drawing order follows the general approach discussed there; the present implementation is original and restricts opacity to one for efficient controlled comparisons.
