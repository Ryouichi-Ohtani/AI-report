"""Original, paired ToM items; public prompts and scoring keys are separate."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build():
    items, keys = [], {}

    def add(group, family, variant, story, question, options, answer):
        identity = f'{group}-{variant}'
        items.append(dict(id=identity, group=group, family=family,
                          prompt=story + '\n' + question,
                          options=options))
        keys[identity] = answer

    # Change only the epistemic access while keeping object locations fixed.
    settings = [('綾', '航', '撮影用レンズ', '赤いケース', '青いロッカー'),
                ('岳', '澪', '実験用センサー', '上段の棚', '机の引き出し'),
                ('杏', '朔', '合奏室の鍵', '黒いポーチ', '白い封筒'),
                ('凛', '悠', '試作品の基板', '箱A', '箱B')]
    for i, (a, b, obj, x, y) in enumerate(settings):
        for v in range(2):
            access = (f'{a}の端末には移動の通知が送られたが、電源が切れていて読まなかった。' if v == 0
                      else f'{a}は室外の端末で移動の映像を最後まで見た。')
            story = f'{a}は{obj}を{x}に入れ退室した。その後{b}が{obj}を{y}へ移した。{access}ほかに{a}が移動を知る出来事はない。'
            add(f'belief{i}', 'belief', v, story, f'戻った{a}は最初にどこを探すと考えられるか。',
                {'A': x, 'B': y, 'C': '記述から決められない'}, 'A' if v == 0 else 'B')
    # Second-order belief: knowledge about another observer's access.
    for i, (a, b, obj, x, y) in enumerate(settings):
        for v in range(2):
            access = (f'{a}は、{b}の画面が故障しており映像が届かないことを知っている。' if v == 0
                      else f'{a}は、{b}の画面に移動の映像が届き、{b}が見たことを確認した。')
            story = f'{a}と{b}は{obj}が{x}にあるのを見た。{b}は別室へ行った。係員が{obj}を{y}へ移す様子を{a}は見た。{access}{b}がほかから情報を得たとは{a}は考えていない。'
            add(f'second{i}', 'second_order', v, story, f'{a}は「{b}は最初にどこを探す」と予測するか。',
                {'A': x, 'B': y, 'C': '記述から決められない'}, 'A' if v == 0 else 'B')
    contexts = [('展示会の案内係', '来場者を全員別の階へ案内してしまった', '来場者を全員正しい会場へ案内した', 'さすが、完璧な案内だね'),
                ('共同発表の担当者', '全スライドの順序を逆にしてしまった', '全スライドを予定どおり準備した', 'とても見やすい資料だね'),
                ('料理担当者', '全員分のスープを焦がしてしまった', '全員に好評なスープを作った', '今日も見事な料理だね'),
                ('演奏会の録音担当者', '本番の録音を一秒も保存していなかった', '本番をすべて鮮明に保存した', '実に頼もしい仕事だね')]
    for i, (role, bad, good, line) in enumerate(contexts):
        for v in range(2):
            story = f'{role}が{bad if v == 0 else good}。同僚はその結果を確認した直後、本人に「{line}」と言った。二人の関係は普通で、冗談を言う習慣などの追加事情は示されていない。'
            add(f'irony{i}', 'irony', v, story, 'この文脈で最も自然な発言意図はどれか。',
                {'A': '皮肉として仕事の失敗を批判', 'B': '文字どおり仕事を称賛', 'C': '発言意図は一切推定できない'},
                'A' if v == 0 else 'B')
    topics = [('ポスター', '紬', 'このポスターはひどい出来だね'),
              ('陶芸作品', '湊', 'この器は見た目が悪いね'),
              ('校歌の新アレンジ', '葵', 'この編曲は退屈だね'),
              ('会場の装飾', '樹', 'この飾り付けは趣味が悪いね')]
    for i, (obj, person, line) in enumerate(topics):
        for v in range(2):
            access = (f'作った人の名前は伏せられており、発言者は{person}が作者だと知らなかった。' if v == 0
                      else f'発言者は{person}本人から作者だと聞き、正しく理解していた。')
            story = f'{person}は{obj}を作った。発言者は本人の目の前で「{line}」と言った。{access}{person}は傷ついた。'
            add(f'faux{i}', 'faux_pas', v, story, '発言者が相手を傷つけると分かる情報を欠いていた、という説明は成立するか。',
                {'A': '作者を知らないことによる失言として成立', 'B': '作者を知った上の発言なのでその説明は不成立', 'C': '情報不足'},
                'A' if v == 0 else 'B')
    for i, (role, bad, good, line) in enumerate(contexts):
        story = f'{role}の同僚が本人に「{line}」とだけメッセージを送った。仕事の結果や前後の会話、声の調子は一切記録されていない。'
        add(f'unknown{i}', 'underdetermined', 0, story, '記述だけで称賛か皮肉かを確定できるか。',
            {'A': '必ず皮肉', 'B': '必ず文字どおりの称賛', 'C': 'どちらか確定できない'}, 'C')
    # Shuffle options by deterministic rotations to avoid an A/B sequence shortcut.
    for j, item in enumerate(items):
        shift = j % 3
        mapping = {old: 'ABC'[('ABC'.index(old) + shift) % 3] for old in 'ABC'}
        item['options'] = {mapping[k]: v for k, v in item['options'].items()}
        keys[item['id']] = mapping[keys[item['id']]]
    return items, keys


def main():
    items, keys = build()
    directory = ROOT / 'data'
    directory.mkdir(exist_ok=True)
    public = json.dumps(items, ensure_ascii=False, indent=2) + '\n'
    (directory / 'prompts.json').write_text(public, encoding='utf-8')
    (directory / 'keys.json').write_text(json.dumps(keys, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {'items': len(items), 'sha256': hashlib.sha256(public.encode()).hexdigest(),
                'created': '2026-11-17', 'design': 'original paired interventions + uncertainty controls',
                'note': 'No human comparison group; model generating items is same family as respondents.'}
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
