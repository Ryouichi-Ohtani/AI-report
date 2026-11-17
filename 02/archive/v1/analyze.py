"""Exact-choice scoring and pair consistency; raw model answers remain untouched."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent


def score(items, keys, answers):
    by_id = {row['id']: row for row in answers}
    if len(by_id) != len(answers) or set(by_id) != set(keys):
        raise ValueError('Duplicate, missing, or unexpected response IDs')
    correct = {i['id']: by_id[i['id']]['answer'] == keys[i['id']] for i in items}
    families, groups = defaultdict(list), defaultdict(list)
    for item in items:
        families[item['family']].append(correct[item['id']])
        groups[item['group']].append(correct[item['id']])
    paired = [all(v) for v in groups.values() if len(v) == 2]
    return {'correct': sum(correct.values()), 'total': len(items),
            'families': {k: {'correct': sum(v), 'total': len(v)} for k, v in families.items()},
            'strict_pairs_correct': sum(paired), 'strict_pairs_total': len(paired),
            'correct_by_id': correct}


def main():
    items = json.loads((ROOT / 'data/prompts.json').read_text())
    keys = json.loads((ROOT / 'data/keys.json').read_text())
    responses = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / 'responses').glob('trial*.json'))}
    if not responses:
        raise RuntimeError('No real model responses found')
    summary = {k: score(items, keys, r['answers']) for k, r in responses.items()}
    baseline = [{'id': i['id'], 'answer': 'A'} for i in items]
    summary['always_A'] = score(items, keys, baseline)
    # Reality leakage baseline for the two belief families: always choose final location.
    belief = [i for i in items if i['family'] in ['belief', 'second_order']]
    reality_correct = 0
    for item in belief:
        group_number = int(item['group'][-1])
        final = ['青いロッカー', '机の引き出し', '白い封筒', '箱B'][group_number]
        choice = next(k for k, value in item['options'].items() if value == final)
        reality_correct += choice == keys[item['id']]
    agreement = []
    names = list(responses)
    if len(names) == 2:
        maps = [{r['id']: r['answer'] for r in responses[n]['answers']} for n in names]
        agreement = [maps[0][i['id']] == maps[1][i['id']] for i in items]
    output = {'trials': summary, 'reality_baseline': {'correct': reality_correct, 'total': len(belief)},
              'between_context_agreement': sum(agreement), 'agreement_total': len(agreement),
              'model_metadata': {k: r['metadata'] for k, r in responses.items()},
              'sampling_note': '36 authored items, not a random sample; paired items and contexts are not independent subjects.'}
    out = ROOT / 'results'; out.mkdir(exist_ok=True)
    (out / 'summary.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    families = ['belief', 'second_order', 'irony', 'faux_pas', 'underdetermined']
    labels = ['First-order', 'Second-order', 'Irony', 'Faux pas', 'Uncertainty']
    fig, ax = plt.subplots(figsize=(6.4, 3.5))
    for j, name in enumerate(summary):
        values = [summary[name]['families'][f]['correct'] / summary[name]['families'][f]['total'] for f in families]
        ax.bar(np.arange(5) + (j - 1) * .23, values, .23, label=name)
    ax.set(xticks=np.arange(5), xticklabels=labels, ylim=(0, 1.2), ylabel='Exact-choice accuracy', title='36 original ToM items; 2 fresh contexts')
    ax.legend(loc='upper center', ncol=3, fontsize=8); ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout(); fig.savefig(out / 'accuracy.pdf'); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    for i, text in enumerate(['Reality: lens in blue locker', 'Observer: power off → red case', 'Observer: video seen → blue locker']):
        ax.text(.5, .82 - i * .3, text, ha='center', va='center', fontsize=10,
                bbox=dict(boxstyle='round,pad=.6', fc=['#dde9ee', '#f3e4d9', '#dfecdf'][i], ec='#687b81'))
    ax.text(.5, -.03, 'Changing information access changes belief, while reality stays fixed.', ha='center', fontsize=9)
    ax.set(xlim=(0, 1), ylim=(-.1, 1)); ax.axis('off'); fig.tight_layout(); fig.savefig(out / 'belief_intervention.pdf'); plt.close(fig)
    maps = {n: {r['id']:r['answer'] for r in responses[n]['answers']} for n in names}
    table = ['\\begin{tabular}{lccc}\\toprule', '項目ID & 正解 & 文脈1 & 文脈2\\\\\\midrule']
    for item in items:
        ident = item['id']
        table.append(ident.replace('_', '\\_') + ' & ' + keys[ident] + ' & ' + maps[names[0]][ident] + ' & ' + maps[names[1]][ident] + '\\\\')
    table += ['\\bottomrule\\end{tabular}']
    (out / 'audit_table.tex').write_text('\n'.join(table) + '\n')
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
