# まとめて変換

CSV・画像・PDF の「ちょっと面倒な変換」をまとめて片づける、Windows／Mac 両対応のデスクトップアプリです。
ファイルはすべて自分のPCの中だけで処理され、インターネットには送信されません。

## できること

| 機能 | 内容 |
|---|---|
| ① CSV 変換・結合 | 文字コード（Shift_JIS／UTF-8）を自動判定。複数のCSVを見出し名でそろえて1つに結合。全角→半角、和暦→西暦、㈱→(株) などの整形。Excel／CSV（UTF-8 BOM付き・Shift_JIS）／JSON で保存。Excel 出力では先頭の0を保護 |
| ② 画像一括変換 | JPEG／PNG／WebP（無劣化も可）へ一括変換。長辺サイズの統一、白い余白での正方形化、スマホ写真の向き補正、位置情報の削除、連番ファイル名。iPhone の HEIC も読み込み可 |
| ③ CSV 形式変換 | 「元の列 → 変換先の列」を対応付けて別形式のCSVを作成。固定値の挿入、カンマ除去などの加工。対応付けはテンプレートとして保存して繰り返し使用 |
| ④ PDF 結合・分割 | 複数PDFの結合（並べ替え可）、Nページごとの分割、指定ページの抜き出し（例：`1-3, 5`）。画質は変わりません |

変換で情報が失われる場合（JPEG で透明部分が白になる、Shift_JIS で表せない文字が「?」になる など）は、保存する前に画面に注意が表示されます。

## ダウンロード（使うだけの人）

[Releases](../../releases) ページから、自分のPCに合うファイルをダウンロードしてください。

### Windows

1. `MatometeHenkan-windows.zip` をダウンロードして展開します。
2. 中の `MatometeHenkan.exe` をダブルクリックします。
3. 「Windows によって PC が保護されました」と表示されたら、「詳細情報」→「実行」を押します（署名のない新しいアプリに出る表示です）。

Windows 10 で画面が表示されない場合は、Microsoft の「WebView2 ランタイム」をインストールしてください（Windows 11 には最初から入っています）。

### Mac

1. `MatometeHenkan-macos.zip` をダウンロードして展開し、`MatometeHenkan.app` を「アプリケーション」フォルダに移します。
2. 初回だけ、アプリを **右クリック →「開く」** で起動します（ダブルクリックだと「開発元を確認できない」と止められます）。
3. それでも開けない場合は、ターミナルで次を実行してから開きます。

   ```
   xattr -cr /Applications/MatometeHenkan.app
   ```

配布している Mac 版は Apple シリコン（M1 以降）用です。Intel の Mac では、下の「ソースから動かす」方法で使えます。

### ビルドせずにそのまま使う（Windows・Mac 共通のおすすめ）

1. このページの緑の「Code」ボタン →「Download ZIP」でダウンロードし、好きな場所に展開します（場所はどこでも構いません）。
2. 展開したフォルダの中のセットアップを実行します。
   - **Windows**：`セットアップ（Windows）.bat` をダブルクリック
     （Python が無ければ python.org の公式版を自動でインストールします。詳しくは `使い方（Windows）.txt`）
   - **Mac**：`セットアップ（Mac）.command` を **右クリック →「開く」**
     （Python 3.10 以上が必要です。無ければ https://www.python.org/downloads/macos/ から入れてください）
3. 終わるとアプリが起動し、デスクトップに「まとめて変換」ができます。次からはそれで起動します。

動作確認用のファイルが `samples/` に入っています（`samples/読んでください.txt` に確認手順があります）。

## ソースから動かす（開発する人）

Python 3.10 以上が必要です。

```bash
git clone https://github.com/<あなたのユーザー名>/matomete-henkan.git
cd matomete-henkan
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac:      source .venv/bin/activate
pip install -r requirements-dev.txt
python app/main.py
```

全体チェック（修正したら必ず実行）：

```bash
python -m playwright install chromium   # 初回だけ（画面テスト用）
python scripts/check.py
```

画面の開発中は環境変数 `MATOMETE_DEBUG=1` を付けて起動すると、開発者ツールが使えます。

## 配布用アプリを作る

### 自分のPCで作る

```bash
python build.py
```

- Windows：`dist/MatometeHenkan/MatometeHenkan.exe`（フォルダごと配布）
- Mac：`dist/MatometeHenkan.app`

Windows 版は Windows で、Mac 版は Mac でビルドする必要があります。

### GitHub に自動で作らせる（おすすめ）

`.github/workflows/build.yml` が、Windows と Mac の両方でテストとビルドを自動で行います。

新しい版を公開するときは、次の3つだけです（タグを付ける必要はありません）。

1. `app/version.py` のバージョン番号を上げる
2. `CHANGELOG.md` にそのバージョンの変更内容を書く
3. `main` ブランチに push する

まだ公開していないバージョンなら、テスト → Windows 版・Mac 版のビルド → `v番号` のタグ付きで Releases に公開、まで自動で進みます。
リリースノートには `CHANGELOG.md` のそのバージョンの部分が使われます。

## 修正・機能追加をする人へ（AI を含む）

作業の前に [AGENTS.md](AGENTS.md) を読んでください。仕組みは [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)、
追加の手順は [docs/EXTENDING.md](docs/EXTENDING.md)、変更の記録は [CHANGELOG.md](CHANGELOG.md) にあります。
修正したら必ず `python scripts/check.py` を実行し、「合格」になることを確認してください。

## フォルダ構成

```
AGENTS.md            修正する AI・開発者への作業ルール（最初に読む）
CLAUDE.md            Claude 用の入口（AGENTS.md を読み込む）
CHANGELOG.md         変更履歴
PC環境.md            持ち主の PC のスペック（セットアップで自動作成。GitHub には上げない）
docs/
  ARCHITECTURE.md    全体の仕組みとファイルの役割
  EXTENDING.md       機能・形式を追加する手順
app/
  main.py            アプリの入口（ウィンドウ表示・画面との橋渡し）
  version.py         バージョン番号
  converters/        変換処理（画面とは独立）
    text_io.py       文字コード判定・CSV の読み書き
    normalize.py     全角→半角、和暦→西暦などの整形
    csv_tools.py     ① 結合と Excel／CSV／JSON 出力
    image_tools.py   ② 画像変換
    mapping.py       ③ 列の対応付けとテンプレート
    pdf_tools.py     ④ PDF の結合・分割・抜き出し
  ui/                画面（HTML／CSS／JavaScript）
samples/             動作確認用のテストファイル（架空のデータ）と確認項目
tests/               自動テスト（変換処理・名前の一致・文字コード・画面操作）
scripts/
  check.py           全体チェック（修正したら必ず実行）
  make_samples.py    samples/ の作り直し
  create_shortcut.ps1  デスクトップ／スタートメニューのアイコン作成
  collect_pc_info.ps1  PC環境.md の作成
セットアップ（Windows）.bat   Windows でのインストール
セットアップ（Mac）.command  Mac でのインストール
使い方（Windows）.txt        利用者向けの説明
build.py             配布用アプリの作成
.github/workflows/   Windows／Mac の自動テスト・ビルド
```

## 設定の保存場所

③ のテンプレートは次の場所に保存されます。

- Windows：`%APPDATA%\MatometeHenkan\templates`
- Mac：`~/Library/Application Support/MatometeHenkan/templates`

## 使用しているライブラリ

[pywebview](https://github.com/r0x0r/pywebview)（BSD）、[Pillow](https://python-pillow.org/)（MIT-CMU）、[pillow-heif](https://github.com/bigcat88/pillow_heif)（BSD、同梱の libheif は LGPL）、[pypdf](https://github.com/py-pdf/pypdf)（BSD）、[pypdfium2](https://github.com/pypdfium2-team/pypdfium2)（Apache-2.0 / BSD）、[openpyxl](https://openpyxl.readthedocs.io/)（MIT）、[charset-normalizer](https://github.com/jawah/charset_normalizer)（MIT）

## ライセンス

MIT License（[LICENSE](LICENSE)）
