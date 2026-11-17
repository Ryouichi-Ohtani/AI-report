"""Supplemental time-to-target analysis of existing runs; no new optimization."""
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent


def main():
    threshold = -20
    rows = []
    for method in ['darwin', 'baldwin', 'lamarck']:
        trials = []
        for seed in range(5):
            run = json.loads((ROOT / f'results/s48_02_{method}_{seed}.json').read_text())
            cutoff = run['generation']['calls']
            event = next((e for e in run['improvement_events'] if e[0] <= cutoff and e[1] <= threshold), None)
            if event:
                generation = next(h['generation'] for h in run['history'] if h['calls'] >= event[0])
                trials.append({'seed': seed, 'reached': True, 'calls': event[0], 'seconds': event[2], 'generation_end': generation})
            else:
                trials.append({'seed': seed, 'reached': False, 'censored_generation': 60})
        successes = [t for t in trials if t['reached']]
        rows.append({'method': method, 'successes': len(successes), 'total': 5,
                     'median_seconds_given_success': median(t['seconds'] for t in successes) if successes else None,
                     'median_generation_given_success': median(t['generation_end'] for t in successes) if successes else None,
                     'trials': trials})
    result = {'sequence': 's48_02', 'threshold': threshold, 'horizon_generations': 60,
              'note': 'Supplementary post-hoc target; nonhits are censored, medians condition on success.', 'rows': rows}
    (ROOT / 'results/time_to_threshold.json').write_text(json.dumps(result, indent=2) + '\n')
    table = ['\\begin{tabular}{lrrr}\\hline', '手法 & 到達数 & 世代 & 秒\\\\\\hline']
    for row in rows:
        generation = row['median_generation_given_success']
        seconds = row['median_seconds_given_success']
        generation_text = f'{generation:g}' if generation is not None else '--'
        seconds_text = f'{seconds:.3f}' if seconds is not None else '--'
        table.append(f"{row['method'].capitalize()} & {row['successes']}/5 & {generation_text} & {seconds_text}" + '\\\\')
    table.append('\\hline\\end{tabular}')
    (ROOT / 'results/time_to_threshold.tex').write_text('\n'.join(table) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
