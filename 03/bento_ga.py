"""A reproducible evolutionary-computing analogy using a synthetic bento model."""
import json
import platform
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
NAMES = ['Rice', 'Chicken', 'Egg', 'Tofu', 'Broccoli', 'Carrot', 'Bean', 'Fruit']
COLORS = ['#e9ddbe', '#c78460', '#edba38', '#e3d2a2', '#4b916b', '#dc7944', '#8d664e', '#c7586b']
# Deliberately synthetic values per one of 16 equal-volume portions.
KCAL = np.array([50, 38, 36, 18, 8, 12, 28, 20])
PROTEIN = np.array([.7, 5., 2.8, 2., .8, .3, 1.8, .1])
COST = np.array([15, 44, 30, 23, 27, 17, 24, 32])


def counts(genomes):
    a = np.atleast_2d(genomes)
    return (a[:, :, None] == np.arange(8)[None, None, :]).sum(axis=1)


def score_counts(c):
    """Lower is better; preference penalties are author's educational model."""
    c = np.atleast_2d(c)
    calories = (c * KCAL).sum(axis=1)
    protein = (c * PROTEIN).sum(axis=1)
    cost = (c * COST).sum(axis=1)
    vegetables = c[:, 4] + c[:, 5]
    return (((calories - 520) / 45) ** 2
            + (np.maximum(0, 30 - protein) / 3) ** 2
            + (np.maximum(0, cost - 480) / 30) ** 2
            + np.maximum(0, 4 - vegetables) ** 2
            + .15 * np.maximum(0, c - 5).sum(axis=1)
            + .25 * (8 - (c > 0).sum(axis=1)))


def fitness(genomes):
    return score_counts(counts(genomes))


def compositions(total, parts, prefix=()):
    if parts == 1:
        yield prefix + (total,)
    else:
        for k in range(total + 1):
            yield from compositions(total - k, parts - 1, prefix + (k,))


def run(seed, mode, population=48, generations=60):
    rng = np.random.default_rng(seed)
    pop = rng.integers(0, 8, (population, 16))
    values = fitness(pop)
    best_index = values.argmin()
    best, best_score = pop[best_index].copy(), float(values[best_index])
    history = [best_score]
    start = time.perf_counter()
    for _ in range(generations):
        if mode == 'random':
            children = rng.integers(0, 8, (population, 16))
        else:
            contenders = rng.integers(0, population, (population, 2, 3))
            winner = np.argmin(values[contenders], axis=2)
            parents = contenders[np.arange(population)[:, None], np.arange(2)[None, :], winner]
            cuts = rng.integers(1, 16, population)
            children = np.where(np.arange(16)[None, :] < cuts[:, None], pop[parents[:, 0]], pop[parents[:, 1]])
            if mode == 'ga':
                mask = rng.random(children.shape) < 1 / 16
                children = np.where(mask, rng.integers(0, 8, children.shape), children)
        child_values = fitness(children)
        index = child_values.argmin()
        if child_values[index] < best_score:
            best, best_score = children[index].copy(), float(child_values[index])
        if mode != 'random':
            # Elitism reuses an already evaluated genome, no additional evaluation.
            worst = child_values.argmax()
            children[worst], child_values[worst] = best, best_score
        pop, values = children, child_values
        history.append(best_score)
    return dict(seed=seed, mode=mode, evaluations=population * (generations + 1),
                seconds=time.perf_counter() - start, history=history,
                best_genome=best.tolist(), counts=counts(best)[0].tolist(), score=best_score)


def plots(result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Wedge, Circle
    out = ROOT / 'results'
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    for mode, color in [('ga', '#206b70'), ('no_mutation', '#c2872f'), ('random', '#8a6b9a')]:
        h = np.array([r['history'] for r in result['runs'] if r['mode'] == mode])
        ax.plot(np.arange(h.shape[1]) * 48 + 48, np.median(h, axis=0), label=mode, color=color)
        ax.fill_between(np.arange(h.shape[1]) * 48 + 48, np.percentile(h, 25, axis=0), np.percentile(h, 75, axis=0), alpha=.15, color=color)
    ax.axhline(result['exact']['score'], ls='--', color='black', label='exact optimum')
    ax.set(xlabel='Fitness evaluations', ylabel='Best penalty (lower is better)', title='Bento optimization: median and IQR, 10 seeds')
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out / 'convergence.pdf'); plt.close(fig)
    best = min(result['runs'], key=lambda r: r['score'])
    fig, axs = plt.subplots(2, 1, figsize=(6.4, 5.2))
    for ax, genome, title in [(axs[0], result['initial_example'], 'Initial candidate'), (axs[1], best['best_genome'], 'Evolved candidate')]:
        for j, ingredient in enumerate(genome):
            x, y = j % 8, j // 8
            ax.add_patch(Rectangle((x, y), .95, .95, facecolor=COLORS[ingredient], edgecolor='white'))
            ax.text(x + .475, y + .475, NAMES[ingredient][:3], ha='center', va='center', fontsize=9)
        ax.set(xlim=(0, 8), ylim=(0, 2), aspect='equal', title=title)
        ax.axis('off')
    fig.tight_layout(); fig.savefig(out / 'bento.pdf'); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    labels = ['Initialize\n48 menus', 'Evaluate\npenalties', 'Select\ntournament', 'Crossover\nmix parts', 'Mutate\nreplace food', 'Next\ngeneration']
    for i, label in enumerate(labels):
        x, y = (i % 3) * 2.1, -(i // 3) * 1.2
        ax.text(x, y, label, ha='center', va='center', bbox=dict(boxstyle='round,pad=.4', fc='#e3efed', ec='#236a6c'))
        if i % 3 != 2:
            ax.annotate('', xy=(x + 1.4, y), xytext=(x + .65, y), arrowprops=dict(arrowstyle='->'))
    ax.set(xlim=(-1, 5.3), ylim=(-1.9, .7)); ax.axis('off')
    fig.tight_layout(); fig.savefig(out / 'evolution_cycle.pdf'); plt.close(fig)
    fig, axs = plt.subplots(1, 3, figsize=(7, 2.6))
    rng = np.random.default_rng(0)
    for i, ax in enumerate(axs):
        if i != 2:
            ax.add_patch(Circle((.35, .5), .26, color='#46958d') if i == 0 else Wedge((.35, .5), .29, 45, 315, color='#46958d'))
            pts = rng.uniform(.55, .95, (20, 2)); ax.scatter(pts[:, 0], pts[:, 1], s=10, color='#dc9c48')
        else:
            ax.add_patch(Circle((.5, .5), .17, color='#dc9c48'))
        ax.set(xlim=(0, 1), ylim=(0, 1), aspect='equal', title=['Shape candidate', 'Collect loose cells', 'Assembled cluster'][i]); ax.axis('off')
    fig.suptitle('Xenobot mechanism: original conceptual schematic, not experimental data', fontsize=9)
    fig.tight_layout(); fig.savefig(out / 'xenobot_schematic.pdf'); plt.close(fig)


def main():
    out = ROOT / 'results'; out.mkdir(exist_ok=True)
    candidates = np.array(list(compositions(16, 8)))
    scores = score_counts(candidates); index = scores.argmin()
    result = {'model': 'author-defined synthetic food values, not nutritional advice',
              'environment': {'python': platform.python_version(), 'numpy': np.__version__},
              'exact': {'candidates': len(candidates), 'score': float(scores[index]), 'counts': candidates[index].tolist()},
              'initial_example': np.random.default_rng(0).integers(0, 8, 16).tolist(),
              'runs': [run(seed, mode) for mode in ['ga', 'no_mutation', 'random'] for seed in range(10)]}
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    plots(result)
    print(json.dumps({'exact': result['exact'], 'summary': {m: {'median':float(np.median([r['score'] for r in result['runs'] if r['mode']==m])), 'success':sum(abs(r['score']-result['exact']['score'])<1e-9 for r in result['runs'] if r['mode']==m)} for m in ['ga','no_mutation','random']}}))


if __name__ == '__main__':
    main()
