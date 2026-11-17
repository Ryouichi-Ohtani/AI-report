"""Reproducible, train-only genetic fitting of ordered opaque RGB triangles.

The renderer is intentionally small and deterministic.  Mutation may use the
training image, but never a held-out clean image.  Genomes remain explicit
triangle lists so insertion/deletion genuinely changes their length.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
import json
import time

import numpy as np
from PIL import Image, ImageDraw


@dataclass
class Genome:
    triangles: np.ndarray  # n x 9: 3 vertex (x,y), followed by RGB

    def copy(self):
        return Genome(self.triangles.copy())


def render(genome: Genome, size: int, background: np.ndarray) -> np.ndarray:
    image = Image.new("RGB", (size, size), tuple(np.rint(background).astype(int)))
    draw = ImageDraw.Draw(image)
    for gene in genome.triangles:
        points = [tuple(x) for x in np.rint(gene[:6].reshape(3, 2)).astype(int)]
        draw.polygon(points, fill=tuple(np.rint(gene[6:]).astype(int)))
    return np.asarray(image, dtype=np.float32) / 255.0


def gradients(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    # RGB gradients avoid silently discarding a chromatic edge.
    return np.diff(image, axis=1), np.diff(image, axis=0)


class Objective:
    def __init__(self, train: np.ndarray, kind: str, penalty: float = 0.0):
        self.train = np.asarray(train, np.float32) / 255.0
        self.kind = kind
        self.penalty = penalty
        gx, gy = gradients(self.train)
        edge = np.zeros(self.train.shape[:2], np.float32)
        edge[:, :-1] += np.mean(np.abs(gx), axis=2)
        edge[:-1, :] += np.mean(np.abs(gy), axis=2)
        self.weights = 1.0 + 3.0 * edge
        self.target_gradients = (gx, gy)

    def __call__(self, image: np.ndarray, count: int) -> float:
        delta = image - self.train
        if self.kind == "mse":
            loss = np.mean(delta * delta)
        elif self.kind == "mae":
            loss = np.mean(np.abs(delta))
        elif self.kind == "perceptual":
            # A declared surrogate, not a measured human preference model.
            color = np.sum(np.mean(np.abs(delta), axis=2) * self.weights)
            color /= np.sum(self.weights)
            gx, gy = gradients(image)
            tx, ty = self.target_gradients
            edge = 0.5 * (np.mean(np.abs(gx - tx)) + np.mean(np.abs(gy - ty)))
            loss = color + 0.35 * edge
        else:
            raise ValueError("Unknown objective: " + self.kind)
        return float(loss + self.penalty * count)


def polygon_mask(gene: np.ndarray, size: int) -> np.ndarray:
    image = Image.new("1", (size, size))
    ImageDraw.Draw(image).polygon(
        [tuple(x) for x in np.rint(gene[:6].reshape(3, 2)).astype(int)], fill=1
    )
    return np.asarray(image, dtype=bool)


def fit_color(gene: np.ndarray, train: np.ndarray, kind: str) -> np.ndarray:
    mask = polygon_mask(gene, len(train))
    pixels = train[mask]
    if len(pixels):
        gene[6:] = np.mean(pixels, axis=0) if kind == "mse" else np.median(pixels, axis=0)
    return gene


def initialize(count: int, size: int, train: np.ndarray, kind: str,
               rng: np.random.Generator) -> Genome:
    # Equal-area grid gives all objectives the same image-informed baseline.
    # It is initialization, and is included in the stated evaluation budget.
    columns = max(1, int(np.sqrt(count / 2)))
    rows = max(1, int(np.ceil(count / (2 * columns))))
    genes = []
    for row in range(rows):
        for column in range(columns):
            x0, x1 = column * size / columns, (column + 1) * size / columns
            y0, y1 = row * size / rows, (row + 1) * size / rows
            for coordinates in ([x0,y0,x1,y0,x1,y1], [x0,y0,x1,y1,x0,y1]):
                gene = np.array(coordinates + [0, 0, 0], dtype=float)
                # Small independent jitter diversifies the common grid layout.
                gene[:6] += rng.normal(0, 0.7, 6)
                gene[:6] = np.clip(gene[:6], 0, size - 1)
                genes.append(fit_color(gene, train, kind))
    return Genome(np.array(genes[:count]))


def crossover(a: Genome, b: Genome, rng: np.random.Generator) -> Genome:
    count = min(len(a.triangles), len(b.triangles))
    if count < 2:
        return a.copy()
    cut = int(rng.integers(1, count))
    return Genome(np.concatenate((a.triangles[:cut], b.triangles[cut:])).copy())


def mutate(parent: Genome, train: np.ndarray, kind: str, rng: np.random.Generator,
           variable: bool, max_triangles: int, guided: bool,
           parent_image: np.ndarray) -> Genome:
    child = parent.copy()
    size = len(train)
    n = len(child.triangles)
    operation = rng.random()
    if variable and operation < 0.08 and n < max_triangles:
        if guided:
            residual = np.mean(np.abs(parent_image - train / 255.0), axis=2)
            probability = residual.ravel() + 0.005
            pixel = int(rng.choice(size * size, p=probability / probability.sum()))
            y, x = divmod(pixel, size)
        else:
            x, y = rng.integers(0, size, 2)
        radius = rng.uniform(3, size / 3)
        angles = rng.uniform(0, 2 * np.pi) + np.arange(3) * (2 * np.pi / 3)
        vertices = np.column_stack((x + radius * np.cos(angles), y + radius * np.sin(angles)))
        gene = np.concatenate((vertices.ravel(), train[y, x].astype(float)))
        gene[:6] = np.clip(gene[:6], 0, size - 1)
        child.triangles = np.vstack((child.triangles, fit_color(gene, train, kind)))
    elif variable and operation < 0.15 and n > 2:
        child.triangles = np.delete(child.triangles, int(rng.integers(n)), axis=0)
    else:
        index = int(rng.integers(n))
        gene = child.triangles[index]
        mode = rng.random()
        if mode < 0.60:
            vertex = int(rng.integers(3))
            scale = rng.choice([0.9, 2.5, 7.0], p=[0.55, 0.35, 0.10])
            gene[2*vertex:2*vertex+2] += rng.normal(0, scale, 2)
        elif mode < 0.78:
            gene[:6] += np.tile(rng.normal(0, 2.5, 2), 3)
        elif mode < 0.90:
            gene[6:] += rng.normal(0, 18, 3)
        else:
            # Occlusion order is part of the genotype.
            other = int(rng.integers(n))
            child.triangles[[index, other]] = child.triangles[[other, index]]
        child.triangles[:, :6] = np.clip(child.triangles[:, :6], 0, size - 1)
        child.triangles[:, 6:] = np.clip(child.triangles[:, 6:], 0, 255)
        if guided and rng.random() < 0.35:
            fit_color(child.triangles[index], train, kind)
    return child


def metrics(image: np.ndarray, target: np.ndarray) -> dict:
    truth = target.astype(np.float32) / 255.0
    delta = image - truth
    mse = float(np.mean(delta * delta))
    gx, gy = gradients(image)
    tx, ty = gradients(truth)
    return {"mae": float(np.mean(np.abs(delta))), "mse": mse,
            "psnr": float(-10 * np.log10(max(mse, 1e-12))),
            "edge_mae": float(0.5 * (np.mean(np.abs(gx-tx)) + np.mean(np.abs(gy-ty))))}


def evolve(train: np.ndarray, seed: int = 0, evaluations: int = 6000,
           count: int = 24, kind: str = "mae", variable: bool = False,
           penalty: float = 0.0007, population: int = 12,
           guided: bool = True, max_triangles: int = 48) -> dict:
    if evaluations < population or count < 2 or (variable and count > max_triangles):
        raise ValueError("Invalid experiment parameters")
    rng = np.random.default_rng(seed)
    size = len(train)
    background = np.median(train.reshape(-1, 3), axis=0)
    objective = Objective(train, kind, penalty if variable else 0.0)
    started = time.perf_counter()
    members = []
    for _ in range(population):
        genome = initialize(count, size, train, kind, rng)
        image = render(genome, size, background)
        members.append((objective(image, len(genome.triangles)), genome, image))
    members.sort(key=lambda item: item[0])
    trace = [{"evaluations": population, "loss": members[0][0], "triangles": count}]
    snapshots = {"initial": members[0][2].copy()}
    successful_crossovers = 0
    attempted_crossovers = 0
    # A steady-state (mu + 1) GA: one new child and one replacement each step.
    # Three-way tournament, elitist survival, occasional recombination.
    for used in range(population, evaluations):
        contenders = rng.integers(0, population, 3)
        parent = members[int(np.min(contenders))]
        crossed = rng.random() < 0.15
        if crossed:
            mate = members[int(np.min(rng.integers(0, population, 3)))][1]
            genome = crossover(parent[1], mate, rng)
            attempted_crossovers += 1
        else:
            genome = parent[1].copy()
        genome = mutate(genome, train, kind, rng, variable, max_triangles,
                        guided, parent[2])
        image = render(genome, size, background)
        score = objective(image, len(genome.triangles))
        # Equal-score duplicates are rejected to avoid taking over the population.
        if score < members[-1][0] and all(abs(score-x[0]) > 1e-12 for x in members):
            if crossed:
                successful_crossovers += 1
            members[-1] = (score, genome, image)
            members.sort(key=lambda item: item[0])
        if (used + 1) % 100 == 0 or used + 1 == evaluations:
            trace.append({"evaluations": used + 1, "loss": members[0][0],
                          "triangles": len(members[0][1].triangles)})
        if used + 1 in (evaluations // 4, evaluations // 2):
            snapshots[str(used + 1)] = members[0][2].copy()
    best_score, best_genome, best_image = members[0]
    snapshots["final"] = best_image.copy()
    return {"seed": seed, "evaluations": evaluations, "objective": kind,
            "variable": variable, "initial_count": count,
            "count": len(best_genome.triangles), "loss": best_score,
            "penalty": penalty if variable else 0.0, "population": population,
            "guided": guided, "seconds": time.perf_counter() - started,
            "attempted_crossovers": attempted_crossovers,
            "successful_crossovers": successful_crossovers,
            "background": background.tolist(), "genome": best_genome.triangles.tolist(),
            "trace": trace, "snapshots": snapshots, "image": best_image}


def save_run(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in result.items() if k not in ("image", "snapshots")}
    path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")

