# AI-report — 人工知能レポート実験集

東京大学・伊庭研究室「人工知能」第1問〜第6問に対応する、再現可能なコード・データ・TeX本文です。
課題ページ：https://www.iba.t.u-tokyo.ac.jp/iba/AI/report.html

**現在の状態：第2〜6問は実験・本文を作成済み。第1問の本人によるFoldit記録は追記待ち。GitHub公開を確認済みです：https://github.com/Ryouichi-Ohtani/AI-report 。**
実装・分析・初稿の作成にCodexを利用しました。ToMの被験モデルも同じ系列です。
提出前に著者が文章・記録・講義で示された最新条件を確認する必要があります。

| 問題 | 内容 | 実装と主な検証 |
|---|---|---|
| [01](01/) | Foldit | 本人用の操作ログCLI、実プレー記録待ち |
| [02](02/) | LLMの心の理論 | 独自44項目、二次信念の2×2対照、最小対、新規文脈2回の生回答と完全一致採点 |
| [03](03/) | 進化計算の説明と応用 | 弁当GA、突然変異の除去比較、全245157解の厳密対照、Xenobot概念図 |
| [04](04/) | √2を作る小町算 | 共通RPN状態グラフのDFS/BFS/A*、許容的下界と同点整列、厳密有理数DP |
| [05](05/) | 3次元HP folding | Darwin/Baldwin/Lamarck、75試行、同評価数・同世代・同時間、小規模全列挙 |
| [06](06/) | 画像の三角近似 | 可変長GA、複数適合度、205試行、246万描画、ノイズと類似画像の評価 |

各フォルダのREADMEに、表現・評価・制約・完全な再実行コマンドがあります。
計算済みの生データと図を同梱しており、長時間の実験を再実行しなくても検査できます。
図の帯は課題ごとに四分位範囲、最小〜最大、標本標準偏差のいずれかです。各図の説明に明記しています。

## セットアップと確認

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 tools/check.py
```

Python 3.9+。実測環境はPython3.9.6 / NumPy2.0.2 / Matplotlib3.9.4 / Pillow11.3.0 / macOS15.5 arm64。
24件の不変条件テストを実行し、JSONと全6節のリンクも検査します。
GitHub Actionsはコードの検査のみで、実験全体や日本語PDFは自動再計算しません。

## TeXレポート

ルートの `report.tex` をコンパイルします。A4・2段組、中央縦線、全幅タイトル下の横線を実装しています。
各問題の末尾に対応ディレクトリへのURLを置き、公開の確認前は「公開予定・未公開」と表示します。

```sh
python3 tools/build.py              # Tectonicを使用
python3 tools/build.py --offline    # このホストのキャッシュだけでビルド
```

出力：`output/pdf/report.pdf`。既定の日本語フォントはmacOSのHiragino Mincho ProN、欧文はTimes New Romanです。
別OSでは `report.tex` のフォント指定を利用可能な日本語フォントへ変更してください。
`report-support.sty` はオフラインの最小TeX環境でも、ベクター図・折返しURL・クリック可能リンクを出力するXeTeX補助実装です。
描画確認にはmacOS付属のPDFKitを使えます：

```sh
CLANG_MODULE_CACHE_PATH=/private/tmp/ai-report-clang-cache SWIFT_MODULECACHE_PATH=/private/tmp/ai-report-swift-cache swift tools/render_pdf.swift output/pdf/report.pdf tmp/pdf-preview
```

## 個人情報と公開

氏名・学籍番号は追跡対象外の `author-local.tex` に分離しています。GitHubへ個人用PDFをpushしません。
ファイルがない環境では氏名はRyouichi Ohtani、学籍番号は空欄でビルドされます。
Foldit画像は本人が保存したものだけを追加し、他人の情報がある画面は公開前に確認します。

GitHub CLIでRyouichi-Ohtaniに認証済みなら、依頼された公開先を作成・pushし、検証後だけリンクの状態を更新できます。

```sh
gh auth login -h github.com         # 未認証の場合に本人が実施
python3 tools/publish.py
python3 tools/build.py --offline
```

公開先予定：`https://github.com/Ryouichi-Ohtani/AI-report`。
別アカウント、異なるorigin、既存の非公開リポジトリ、未コミット変更がある場合は停止します。
認証トークンやパスワードをリポジトリに保存しません。
この作成環境では `.git` の作成とGitHubへの通信が制限されました。公開用スクリプトは本人の通常のターミナルで実行してください。
未初期化の場合はローカルGitを初期化し、GitHubの非公開メールアドレス表記を使って初回コミットを作ります。
GitHub側を先に作った場合は、初期READMEが見出し `# -` または `# AI-report` のみであることを検査し、その初期コミットを親にしてコードを追加します。既存の履歴は残り、force pushは行いません。
それ以外のファイルやREADME本文がリモートにある場合、または既存ローカル履歴とリモート履歴がつながっていない場合は停止します。既存データを自動で置換・統合しません。

公開対象だけをZIPにまとめる場合は `python3 tools/package.py` を実行します。
学籍番号の設定、個人用PDF、フォントの一時ファイル、キャッシュは含みません。

## 結果の解釈

高精度の式は大域最適解の証明ではありません。48残基HPモデルの課題参照値には未到達です。
ToMの全問正解はこの短い独自テストの結果で、人間との同等性や主観的な心を証明しません。
画像の知覚代理目的は人間の美しさの評価を測定したものではありません。
失敗した工夫、打切り、入力配列の長さの不整合も本文・生データに残しています。
