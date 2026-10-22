# 全体の仕組み

## 3つの層

```
┌─────────────────────────────┐
│ 画面  app/ui/                │  index.html（見た目の骨組み）
│                             │  style.css（色・配置）
│                             │  app.js（ボタンの動き・注意書きの表示）
└──────────────┬──────────────┘
               │ window.pywebview.api.名前(...)   ※app.js では call('名前', [...])
               │ 戻り値は必ず {ok: true, ...} か {ok: false, error: "日本語の説明"}
┌──────────────┴──────────────┐
│ 橋渡し  app/main.py          │  Api クラス：ファイル選択ダイアログ、進み具合の表示、
│                             │  エラーを日本語メッセージに変換（@safe）
└──────────────┬──────────────┘
               │ 普通の Python 関数呼び出し
┌──────────────┴──────────────┐
│ 変換処理  app/converters/    │  画面のことを何も知らない。テストはここを直接呼ぶ
└─────────────────────────────┘
```

画面は Windows では Edge（WebView2）、Mac では Safari（WebKit）の部品で表示されます。

## ファイルの役割

| ファイル | 役割 | 主な関数 |
|---|---|---|
| `app/main.py` | アプリの起動、Api（画面から呼ばれる関数）、ドラッグ＆ドロップ | `Api.*`, `main()` |
| `app/version.py` | バージョン番号（ここだけで管理） | `__version__` |
| `app/converters/text_io.py` | 文字コード判定、CSV の読み書き | `read_table`, `write_csv`, `find_unencodable` |
| `app/converters/normalize.py` | 整形（全角→半角、和暦→西暦、機種依存文字など） | `OPS`, `OP_LABELS`, `apply_ops`, `normalize_rows` |
| `app/converters/csv_tools.py` | ① 結合、Excel/CSV/JSON への出力 | `merge_tables`, `export_rows`, `FORMATS` |
| `app/converters/image_tools.py` | ② 画像の変換 | `inspect_image`, `convert_image`, `OUT_EXT` |
| `app/converters/mapping.py` | ③ 列の対応付け、テンプレート保存 | `apply_mapping`, `save_template` など |
| `app/converters/pdf_tools.py` | ④ PDF の結合・分割・抜き出し | `merge_pdfs`, `split_pdf`, `extract_pages` |
| `app/ui/index.html` | 4画面の HTML（`id="view-csv"` など） | |
| `app/ui/app.js` | 画面の状態（`S`）と動き。機能ごとに区切ってある | `csv*`, `img*`, `map*`, `pdf*` |
| `tests/test_converters.py` | 変換処理のテスト | |
| `tests/test_contract.py` | 画面と Python の名前の食い違い検査 | |
| `tests/test_files.py` | 文字コード・改行・必要ファイル・CHANGELOG の検査 | |
| `tests/test_ui_smoke.py` + `tests/ui/mock_api.js` | 画面を実際に操作する検査（Python はにせ物） | |
| `tests/test_samples.py` | テスト用ファイルが確認項目どおりに変換されるかの検査 | |
| `scripts/check.py` | 上の検査をまとめて実行 | |
| `scripts/make_samples.py` | `samples/`（テスト用ファイル）の作成 | |
| `samples/` | 動作確認用ファイル（架空のデータ）と確認項目 `読んでください.txt` | |
| `scripts/create_shortcut.ps1` | デスクトップ／スタートメニューのアイコン作成 | |
| `scripts/collect_pc_info.ps1` | `PC環境.md` の作成 | |
| `セットアップ（Windows）.bat` | Python・部品のインストール → PC環境の記録 → アイコン作成 → 起動 | |
| `build.py` | 配布用 .exe / .app の作成（PyInstaller） | |
| `.github/workflows/build.yml` | GitHub 上でのテストと Windows/Mac 版の自動ビルド | |

## データの流れ（例：① CSV を結合して Excel で保存）

1. 画面にファイルをドロップ → `main.bind_drop` が本当のパスを `window.onFilesDropped(paths)` に渡す
2. `app.js` の `csvAdd` → `call('csv_load', [paths])` → `text_io.read_table` が文字コードを判定して読む（結果は `Api._tables` に保存）
3. 「保存」→ `call('csv_export', [paths, options, 'xlsx'])` → 保存先ダイアログ →
   `csv_tools.merge_tables` → `normalize.normalize_rows` → `csv_tools.export_rows`
4. 戻り値 `{ok: true, path, rows}` を受けて、画面右下に「保存先を開く」付きのお知らせを出す

## 設計の決まりごと

- **元のファイルは絶対に書き換えない。** 保存はダイアログで選んだ別の場所へ。同じ名前があれば `_1` を付ける（画像）。
- **失われる情報は保存前に知らせる。** ◎（無劣化）○（わずかに劣化）△（条件付きで失われる）の3段階で、画面下に表示する。
- **値は基本すべて文字列として扱う。** 先頭の 0（電話番号・郵便番号）や長い番号を守るため。数値にするのは利用者が選んだときだけ。
- **Excel 出力では「=」で始まる値を数式にしない**（CSV インジェクション対策）。
- **CSV の書き出しは CRLF 改行**（Excel・業務システムとの相性）。
- **エラーは日本語で、利用者が次にどうすればよいか分かる文にする。** Python 側で例外を投げれば `@safe` が `{ok: false, error}` にする。
  利用者向けの説明は `ValueError("…")` で投げる。
- **設定の保存場所**：Windows `%APPDATA%\MatometeHenkan`、Mac `~/Library/Application Support/MatometeHenkan`
  （テストでは環境変数 `MATOMETE_CONFIG_DIR` で一時フォルダに切り替える）。
- **ネットワークは使わない。** 画面のフォントも OS 標準（游ゴシック・ヒラギノ）を使う。
