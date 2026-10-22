# 変更履歴

新しいものが上。書き方：`## [バージョン] - 日付` の下に「追加」「変更」「修正」「削除」で分けて日本語で書く。

## [0.3.0] - 2026-10-22

### 追加
- 動作確認用のテストファイル一式（`samples/`、すべて架空のデータ）と確認項目の一覧（`samples/読んでください.txt`）
- テストファイルを作り直すスクリプト（`scripts/make_samples.py`）
- テストファイルが確認項目どおりに変換されるかの検査（`tests/test_samples.py`）

## [0.2.1] - 2026-10-22

### 修正
- winget が無い PC でセットアップが「Python が見つからない」で止まる不具合を修正。
  Python の検索・インストールを `scripts/find_python.ps1` に分け、見つからなければ python.org 公式の
  Python 3.12.10 を直接ダウンロードし、署名（Python Software Foundation）を確認してからこのユーザー用にインストールするように変更
- Python インストールマネージャー（`py install`）で入れた Python も見つけられるように変更

### 追加
- セットアップの .bat が参照するファイルの実在と、winget を使っていないことの検査（`tests/test_files.py`）

## [0.2.0] - 2026-10-22

### 追加
- Windows 用セットアップ（`セットアップ（Windows）.bat`）：Python と部品の自動インストール、デスクトップ・スタートメニューへのアイコン作成
- アプリのアイコン（`icon.ico`）
- PC 環境の自動記録（`scripts/collect_pc_info.ps1` → `PC環境.md`）
- AI・開発者向けの説明書：`AGENTS.md`、`CLAUDE.md`、`docs/ARCHITECTURE.md`、`docs/EXTENDING.md`、この `CHANGELOG.md`
- 壊れ防止の自動チェック：画面と Python の名前の一致（`tests/test_contract.py`）、文字コード・改行（`tests/test_files.py`）、
  画面の操作テスト（`tests/test_ui_smoke.py`）、まとめて実行する `scripts/check.py`
- `.gitattributes` / `.editorconfig`（改行コード・文字コードの固定）

### 変更
- ③ の「加工」の一覧を、画面と Python の二重管理から Python 側（`normalize.OP_LABELS`）だけで管理するように変更

## [0.1.0] - 2026-10-22

### 追加
- ① CSV 変換・結合、② 画像一括変換、③ CSV 形式変換、④ PDF 結合・分割の4機能
- GitHub Actions による Windows / Mac 版の自動ビルド
