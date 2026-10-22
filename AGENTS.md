# AGENTS.md ― このアプリを修正する AI への作業ルール

Claude、ChatGPT、Codex、Copilot など、どの AI・どのセッションでも、作業の前にこのファイルを最後まで読んでください。
人間の開発者にも同じルールが当てはまります。

## 0. 最初に読むもの（この順番）

1. このファイル（AGENTS.md）
2. `PC環境.md` … 持ち主の PC のスペックと、入っているソフト（Python・WebView2 など）。
   セットアップのたびに自動で更新されます。**無い場合は「セットアップ（Windows）.bat」を実行すると作られます。**
   GitHub には上げていません（個人の PC 情報のため）。
3. `docs/ARCHITECTURE.md` … 全体の仕組みとファイルの役割
4. `docs/EXTENDING.md` … 機能や形式を追加するときの手順
5. `CHANGELOG.md` … これまでの変更履歴

## 1. このアプリについて

- 名前：まとめて変換（MatometeHenkan）
- 中身：CSV・画像・PDF の変換を行うデスクトップアプリ（Windows 11 / Mac）
- 作り：Python（変換処理）＋ HTML/JavaScript（画面）を pywebview でつないでいる
- 持ち主の環境：Windows 11 x64。アプリ本体は `C:\Users\weyeo\tools\MatometeHenkan`
- 起動：デスクトップの「まとめて変換」アイコン（中身は `.venv\Scripts\pythonw.exe app\main.py`）
- 利用者は日本語話者。**画面の文言・エラーメッセージ・説明書はすべて日本語**で書く

## 2. 守ること（壊さないためのルール）

1. **修正したら必ず全体チェックを実行し、「合格」を確認してから終わる。**
   ```
   .venv\Scripts\python.exe scripts\check.py      （Windows）
   python scripts/check.py                       （Mac・Linux）
   ```
   不合格のまま作業を終えない。検査を消したり弱めたりして合格させない。
2. **変換処理は `app/converters/` に書く。** 画面（`app/ui/`）や `app/main.py` に変換の中身を書かない。
3. **画面と Python の名前は一対一。** 片方だけ変えない（`tests/test_contract.py` が見張っている）。
   - `app.js` の `call('名前')` ⇔ `main.py` の `Api.名前()`
   - `app.js` の `$('#id')` ⇔ `index.html` の `id="..."`
   - 出力形式のボタン（`data-fmt`）⇔ `csv_tools.FORMATS` / `image_tools.OUT_EXT`
4. **新しい処理には必ずテストを足す**（`tests/test_converters.py`）。Api に関数を足したら `tests/ui/mock_api.js` にも足す。
5. **ファイルの文字コードと改行を変えない。**
   - `*.bat`：Shift_JIS（cp932）＋ CRLF　← UTF-8 にすると日本語が化けて動かない
   - `*.ps1`：BOM 付き UTF-8 ＋ CRLF
   - それ以外：UTF-8（BOM なし）＋ LF
   - `.bat` を編集するときは、Python で `open(p, encoding="cp932", newline="")` のように読み書きする。
6. **元のファイルを上書きしない設計を守る。** 変換結果は必ず別名・別フォルダに保存する。
7. **ファイルはインターネットに送らない。** 外部 API・クラウド変換を勝手に追加しない。
8. **バージョンと記録を更新する。** 機能を変えたら `app/version.py` の番号を上げ、`CHANGELOG.md` に日本語で追記する
   （`tests/test_files.py` が CHANGELOG に今のバージョンがあるか見ている）。
9. **git で記録する。** （持ち主の PC では、セットアップが `変更履歴.bundle` から `.git` を自動で復元する。
   `.git` が無い場合は git をインストールしてから「セットアップ（Windows）.bat」を実行し直す） 作業の前に `git status` で状態を確認し、区切りごとにコミットする。
   壊れたら `git log` と `git diff` で原因を探し、必要なら `git restore` / `git revert` で戻す。
10. 大きな作り替え（フォルダ構成の変更、ライブラリの入れ替え）は、持ち主に確認してから行う。

## 3. よく使うコマンド（Windows、アプリのフォルダで実行）

| やりたいこと | コマンド |
|---|---|
| 必要なものを入れる・アイコンを作る・PC環境を更新 | `セットアップ（Windows）.bat` をダブルクリック |
| 開発用の部品を入れる | `.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` |
| 画面テスト用ブラウザを入れる | `.venv\Scripts\python.exe -m playwright install chromium` |
| 全体チェック | `.venv\Scripts\python.exe scripts\check.py` |
| アプリを起動（エラーが見える） | `.venv\Scripts\python.exe app\main.py` |
| 開発者ツール付きで起動 | `set MATOMETE_DEBUG=1` のあと上と同じ |
| 配布用 .exe を作る | `.venv\Scripts\python.exe build.py` |

## 4. テスト用ファイル

- `samples/` に4機能それぞれの動作確認用ファイルがある（すべて架空のデータ）。確認項目は `samples/読んでください.txt`。
- 作り直すとき：`python scripts/make_samples.py`（`requirements-dev.txt` の reportlab が必要）。
- `tests/test_samples.py` が「読んでください.txt」の内容どおりに変換されるかを検査している。
  機能を足したら、サンプル・確認項目・この検査の3つをそろえて足す。
- **サンプルに実在の個人情報（名前・電話番号・口座番号・メールアドレスなど）を入れない。**

## 5. 困ったとき

- 画面が真っ白：`MATOMETE_DEBUG=1` で起動し、開発者ツールのコンソールのエラーを見る。
- アイコンから起動して何も出ない：`python.exe app\main.py`（pythonw ではなく）で起動するとエラーが表示される。
- 部品が壊れた：`.venv` フォルダを削除して「セットアップ（Windows）.bat」をもう一度実行する。
- 判断に迷う仕様：`docs/ARCHITECTURE.md` の「設計の決まりごと」を見る。それでも決まらなければ持ち主に聞く。
