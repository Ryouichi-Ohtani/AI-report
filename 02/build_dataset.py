"""V2 stimuli contain only opaque ID, prompt, and alphabetical choices.

Gold answers and condition metadata are stored separately from stimuli.
"""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = 'v2'
OPTION_SEED = 240201
ORDER_SEED = 240202


def build():
    items, keys, metadata = [], {}, {}
    option_rng = random.Random(OPTION_SEED)

    def add(logical_id, group, family, story, question, options, answer, **conditions):
        identity = hashlib.sha256(('q02-v2|' + logical_id).encode()).hexdigest()[:16]
        order = list(options)
        option_rng.shuffle(order)
        displayed = {letter: options[old] for letter, old in zip('ABC', order)}
        items.append(dict(id=identity, prompt=story + '\n' + question, options=displayed))
        keys[identity] = 'ABC'[order.index(answer)]
        metadata[identity] = dict(logical_id=logical_id, group=group, family=family, **conditions)

    settings = [('綾', '航', '撮影用レンズ', '赤いケース', '青いロッカー'),
                ('岳', '澪', '実験用センサー', '上段の棚', '机の引き出し'),
                ('杏', '朔', '合奏室の鍵', '黒いポーチ', '白い封筒'),
                ('凛', '悠', '試作品の基板', '箱A', '箱B')]
    for i, (a, b, obj, x, y) in enumerate(settings):
        for seen in range(2):
            access = (f'{a}の端末には移動の通知が送られたが、電源が切れていて読まなかった。' if not seen
                      else f'{a}は室外の端末で移動の映像を最後まで見た。')
            story = f'{a}は{obj}を{x}に入れ退室した。その後{b}が{obj}を{y}へ移した。{access}ほかに{a}が移動を知る出来事はない。'
            add(f'belief{i}-{seen}', f'belief{i}', 'belief', story,
                f'戻った{a}は最初にどこを探すと考えられるか。',
                {'x': x, 'y': y, 'unknown': '記述から決められない'}, 'y' if seen else 'x', seen=seen)

    # A's belief about B and B's actual knowledge vary independently (2 x 2).
    for i, (a, b, obj, x, y) in enumerate(settings):
        for actual_seen in range(2):
            for believed_seen in range(2):
                actual = (f'実際には{b}の画面は故障しており、{b}は移動の映像を見なかった。{b}はほかの経路からも移動を知っていない。' if not actual_seen
                          else f'実際には{b}の画面は正常で、{b}は移動の映像を最後まで見て移動先を知った。')
                report = '見た' if believed_seen else '見ていない'
                story = (f'{a}と{b}は{obj}が{x}にあるのを見た。{b}は別室へ行った。'
                         f'係員が{obj}を{y}へ移す様子を{a}は見た。{actual}'
                         f'{a}は別室の{b}や画面の状態を直接確認できない。'
                         f'係員は{a}に「{b}は移動の映像を{report}」と報告した。'
                         f'{a}はこの報告を完全に信用している。'
                         f'{a}は、{b}が映像以外から移動を知ることはないと考えている。')
                add(f'second{i}-{actual_seen}-{believed_seen}', f'second{i}-actual{actual_seen}', 'second_order', story,
                    f'{a}は「{b}は最初にどこを探す」と予測するか。{b}の実際の行動ではなく、{a}の予測を答えること。',
                    {'x': x, 'y': y, 'unknown': '記述から決められない'}, 'y' if believed_seen else 'x',
                    actual_seen=actual_seen, believed_seen=believed_seen)

    contexts = [('展示会の案内係', '来場者を全員別の階へ案内してしまった', '来場者を全員正しい会場へ案内した', 'さすが、完璧な案内だね'),
                ('共同発表の担当者', '全スライドの順序を逆にしてしまった', '全スライドを予定どおり準備した', 'とても見やすい資料だね'),
                ('料理担当者', '全員分のスープを焦がしてしまった', '全員に好評なスープを作った', '今日も見事な料理だね'),
                ('演奏会の録音担当者', '本番の録音を一秒も保存していなかった', '本番をすべて鮮明に保存した', '実に頼もしい仕事だね')]
    for i, (role, bad, good, line) in enumerate(contexts):
        for success in range(2):
            story = f'{role}が{good if success else bad}。同僚はその結果を確認した直後、本人に「{line}」と言った。二人の関係は普通で、冗談を言う習慣などの追加事情は示されていない。'
            add(f'irony{i}-{success}', f'irony{i}', 'irony', story, 'この文脈で最も自然な発言意図はどれか。',
                {'ironic': '皮肉として仕事の失敗を批判', 'literal': '文字どおり仕事を称賛', 'unknown': '発言意図は一切推定できない'},
                'literal' if success else 'ironic', success=success)

    topics = [('ポスター', '紬', 'このポスターはひどい出来だね'),
              ('陶芸作品', '湊', 'この器は見た目が悪いね'),
              ('校歌の新アレンジ', '葵', 'この編曲は退屈だね'),
              ('会場の装飾', '樹', 'この飾り付けは趣味が悪いね')]
    for i, (obj, person, line) in enumerate(topics):
        for known in range(2):
            access = (f'発言者は{person}本人から作者だと聞き、正しく理解していた。' if known
                      else f'作った人の名前は伏せられており、発言者は{person}が作者だと知らなかった。')
            story = f'{person}は{obj}を作った。発言者は本人の目の前で「{line}」と言った。{access}{person}は傷ついた。'
            add(f'faux{i}-{known}', f'faux{i}', 'faux_pas', story,
                '発言者が相手を傷つけると分かる情報を欠いていた、という説明は成立するか。',
                {'ignorant': '作者を知らないことによる失言として成立', 'informed': '作者を知った上の発言なのでその説明は不成立', 'unknown': '情報不足'},
                'informed' if known else 'ignorant', known=known)
    for i, (role, bad, good, line) in enumerate(contexts):
        story = f'{role}の同僚が本人に「{line}」とだけメッセージを送った。仕事の結果や前後の会話、声の調子は一切記録されていない。'
        add(f'unknown{i}', f'unknown{i}', 'underdetermined', story, '記述だけで称賛か皮肉かを確定できるか。',
            {'ironic': '必ず皮肉', 'literal': '必ず文字どおりの称賛', 'unknown': 'どちらか確定できない'}, 'unknown')
    random.Random(ORDER_SEED).shuffle(items)
    return items, keys, metadata


def main():
    items, keys, metadata = build()
    directory = ROOT / 'data'
    directory.mkdir(exist_ok=True)
    public = json.dumps(items, ensure_ascii=False, indent=2) + '\n'
    (directory / 'prompts.json').write_text(public, encoding='utf-8')
    (directory / 'keys.json').write_text(json.dumps(keys, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (directory / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {'version': VERSION, 'items': len(items), 'sha256': hashlib.sha256(public.encode()).hexdigest(),
                'created': '2026-11-17', 'option_seed': OPTION_SEED, 'order_seed': ORDER_SEED,
                'design': 'opaque IDs; alphabetical choices; shuffled order; actual x believed knowledge 2x2',
                'note': 'No human comparison; authored by same model family as respondents. V1 invalidated and archived.'}
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
