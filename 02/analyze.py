"""Score only the blinded v2 responses; v1 is archived and invalidated."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
FAMILIES = ['belief', 'second_order', 'irony', 'faux_pas', 'underdetermined']
FAMILY_LABELS = ['一次信念', '二次信念', '皮肉', '失言の知識', '情報不足']


def score(items, keys, metadata, answers):
    by_id = {row['id']: row for row in answers}
    if len(by_id) != len(answers) or set(by_id) != set(keys):
        raise ValueError('Duplicate, missing, or unexpected response IDs')
    if any(row['answer'] not in 'ABC' or len(row['answer']) != 1 for row in answers):
        raise ValueError('Each answer must be A, B, or C')
    correct = {i['id']: by_id[i['id']]['answer'] == keys[i['id']] for i in items}
    families, groups = defaultdict(list), defaultdict(list)
    second_congruent, second_incongruent = [], []
    for item in items:
        ident = item['id']
        meta = metadata[ident]
        families[meta['family']].append(correct[ident])
        groups[meta['group']].append(correct[ident])
        if meta['family'] == 'second_order':
            dest = second_congruent if meta['actual_seen'] == meta['believed_seen'] else second_incongruent
            dest.append(correct[ident])
    paired = [all(v) for v in groups.values() if len(v) == 2]
    return {'correct': sum(correct.values()), 'total': len(items),
            'families': {k: {'correct': sum(v), 'total': len(v)} for k, v in families.items()},
            'strict_pairs_correct': sum(paired), 'strict_pairs_total': len(paired),
            'second_congruent': {'correct': sum(second_congruent), 'total': len(second_congruent)},
            'second_incongruent': {'correct': sum(second_incongruent), 'total': len(second_incongruent)},
            'correct_by_id': correct}


def main():
    public_bytes = (ROOT / 'data/prompts.json').read_bytes()
    items = json.loads(public_bytes)
    stimulus_sha = hashlib.sha256(public_bytes).hexdigest()
    keys = json.loads((ROOT / 'data/keys.json').read_text())
    metadata = json.loads((ROOT / 'data/metadata.json').read_text())
    responses = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / 'responses').glob('v2_trial*.json'))}
    if len(responses) != 2:
        raise RuntimeError('Exactly two v2 response trials are required')
    for name, trial in responses.items():
        if trial['metadata'].get('version') != 'v2' or trial['metadata'].get('stimulus_sha256') != stimulus_sha:
            raise ValueError(f'{name}: wrong version or stimulus digest')
    trials = {k: score(items, keys, metadata, r['answers']) for k, r in responses.items()}
    baselines = {f'always_{letter}': score(items, keys, metadata,
                 [{'id': i['id'], 'answer': letter} for i in items]) for letter in 'ABC'}

    # Final-location baseline on first- and second-order belief items.
    # A second control predicts B's actual knowledge, ignoring A's false belief.
    final_correct = belief_total = actual_correct = second_total = 0
    destinations = ['青いロッカー', '机の引き出し', '白い封筒', '箱B']
    for item in items:
        ident, meta = item['id'], metadata[item['id']]
        if meta['family'] not in ['belief', 'second_order']:
            continue
        setting = int(meta['logical_id'].split('-')[0][-1])
        final = destinations[setting]
        final_choice = next(k for k, value in item['options'].items() if value == final)
        final_correct += final_choice == keys[ident]
        belief_total += 1
        if meta['family'] == 'second_order':
            original = ['赤いケース', '上段の棚', '黒いポーチ', '箱A'][setting]
            actual = final if meta['actual_seen'] else original
            actual_choice = next(k for k, value in item['options'].items() if value == actual)
            actual_correct += actual_choice == keys[ident]
            second_total += 1
    names = list(responses)
    maps = {n: {r['id']: r['answer'] for r in responses[n]['answers']} for n in names}
    agreement = [maps[names[0]][i['id']] == maps[names[1]][i['id']] for i in items]
    output = {'version': 'v2', 'stimulus_sha256': stimulus_sha, 'trials': trials, 'baselines': baselines,
              'reality_baseline': {'correct': final_correct, 'total': belief_total},
              'actual_B_knowledge_baseline': {'correct': actual_correct, 'total': second_total},
              'between_context_agreement': sum(agreement), 'agreement_total': len(agreement),
              'model_metadata': {k: r['metadata'] for k, r in responses.items()},
              'sampling_note': '44 authored items in each of two fresh contexts; items share one batch, not independent subjects.',
              'v1_status': 'Archived and invalidated due to metadata/option-order shortcut; no v1 scores pooled here.'}
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    (out / 'summary.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    display = [(names[0], trials[names[0]]), (names[1], trials[names[1]]), ('always_A', baselines['always_A'])]
    for j, (name, data) in enumerate(display):
        values = [data['families'][f]['correct'] / data['families'][f]['total'] for f in FAMILIES]
        ax.bar(np.arange(5) + (j - 1) * .24, values, .24,
               label=['Context 1', 'Context 2', 'Always A'][j], color=['#356a9b', '#51a697', '#b4b8c0'][j])
    ax.set(xticks=np.arange(5), xticklabels=['First', 'Second', 'Irony', 'Faux pas', 'Unknown'],
           ylim=(0, 1.24), ylabel='Exact-choice accuracy')
    ax.set_title('44 v2 items; 2 fresh batch contexts', fontsize=10)
    ax.tick_params(axis='x', labelsize=8)
    ax.legend(loc='upper center', ncol=3, fontsize=7)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout(); fig.savefig(out / 'accuracy.pdf'); plt.close(fig)

    fig, ax = plt.subplots(figsize=(4.5, 4.4))
    rows = ['Reality: lens in blue locker', 'B actually watched?  no / yes',
            'A trusts report: B watched / did not watch', "Ask A's prediction, not B's actual action"]
    for i, text in enumerate(rows):
        ax.text(.5, .86 - i * .24, text, ha='center', va='center', fontsize=8,
                bbox=dict(boxstyle='round,pad=.55', fc=['#dde9ee', '#f3e4d9', '#dfecdf', '#ece5f2'][i], ec='#687b81'))
    ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis('off')
    fig.tight_layout(); fig.savefig(out / 'belief_intervention.pdf'); plt.close(fig)

    # Main-text audit table is by family; all 44 individual answers remain JSON.
    table = ['\\begin{tabular}{lrrr}\\toprule', '項目群 & 項目数 & 文脈1 & 文脈2\\\\\\midrule']
    for family, label in zip(FAMILIES, FAMILY_LABELS):
        a, b = trials[names[0]]['families'][family], trials[names[1]]['families'][family]
        table.append(f"{label} & {a['total']} & {a['correct']} & {b['correct']}\\\\")
    table += ['\\midrule', f"最小対の両問正解 & 20組 & {trials[names[0]]['strict_pairs_correct']} & {trials[names[1]]['strict_pairs_correct']}\\\\",
              '\\bottomrule\\end{tabular}']
    (out / 'audit_table.tex').write_text('\n'.join(table) + '\n')
    print(json.dumps({k: v for k, v in output.items() if k not in ['trials', 'baselines', 'model_metadata']}, ensure_ascii=False))
    print({name: (data['correct'], data['total'], data['strict_pairs_correct']) for name, data in trials.items()})


if __name__ == '__main__':
    main()
