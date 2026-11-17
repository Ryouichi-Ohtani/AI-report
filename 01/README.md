# 01 — Foldit：本人の実プレーと操作ログ

FolditはWindows/macOS/Linux用のデスクトップゲームです。公式サイト https://fold.it/ から起動してください。
このフォルダは実プレーの代替ではありません。順位や感想を自動生成していません。

## 記録するもの

1. チュートリアルを含む開始・終了時刻、累積プレー時間。
2. Science puzzleのID・正式名・締切・solo/evolver区分。
3. スコア、パズル内順位、参加人数（全体soloist順位と区別）。
4. 手操作・Shake・Wiggleの直前／直後のスクリーンショット。
5. 直観が当たった／外れた具体例、競争や協力で行動が変わった場面。

`data/events.csv` のヘッダーに従って追記するか、次のCLIを使います。

```sh
python3 01/foldit_log.py add --puzzle 'ID: title' --action wiggle --before 1000 --after 1050 --seconds 30 --rank 20 --players 100 --screenshot 01/screenshots/example.png --note '実際の観察内容'
python3 01/foldit_log.py analyze
python3 -m unittest discover -s 01 -p 'test_*.py'
```

上記数値はコマンドの使い方の例であり、実測値ではありません。初期データはヘッダーだけです。
スクリーンショットにメール・チャット・他人の個人情報が映る場合、公開前に除いてください。
大きなファイルやプレー画面の権利が気になる場合、GitHubには操作ログのみを置きます。

## 公平なShake/Wiggle比較

同じ保存状態から、手操作／Shakeのみ／Wiggleのみ／Shake→Wiggleを各5回程度試します。
各試行を同時間にし、成功スコアだけを残さず全試行を記録します。順番は無作為化し、
異なるパズルのスコアは直接平均しません。局所解脱出は単なるスコア増加と同義ではありません。
構造が変わった後に再最適化して以前より高いスコアへ到達した証拠も保存します。

## 提出前の差し込み

`01/section.tex` の「実プレー記録待ち」を本人の記録と図に置換します。
`python3 01/foldit_log.py analyze` はログが空なら結果を捏造せず終了します。
