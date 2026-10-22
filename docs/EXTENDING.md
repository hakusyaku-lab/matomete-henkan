# 機能を追加・修正する手順

どの作業も、最後は `scripts/check.py` が「合格」になること。git で区切りごとにコミットすること。

## A. 既存の画面に「出力形式」を足す（例：CSV を TSV でも保存したい）

1. `app/converters/csv_tools.py`
   - `FORMATS` に `"tsv": (".tsv", "TSV")` を追加
   - `export_rows` に `elif fmt == "tsv": write_csv(path, rows, "utf-8-sig", delimiter="\t")` を追加
2. `app/ui/index.html` の `id="csv-fmt"` の中にボタンを追加：`<button type="button" data-fmt="tsv">TSV</button>`
3. `app/ui/app.js` の `renderCsvNotices` に、その形式の注意書き（◎○△）を追加
4. `tests/test_converters.py` に、書き出した結果を読み戻して確かめるテストを追加
5. `CHANGELOG.md` と `app/version.py` を更新 → `scripts/check.py`

画像の出力形式なら `image_tools.OUT_EXT` と `convert_image`、`index.html` の `id="img-fmt"` が対象です。

## B. 「列の加工」を足す（③ CSV 形式変換、例：「ハイフン除去」）

1. `app/converters/normalize.py`
   - 変換する関数を書く（文字列を受け取って文字列を返す）
   - `OPS` と `OP_LABELS` の両方に同じキーで登録する（画面のボタンは `OP_LABELS` から自動で作られる）
2. `tests/test_converters.py` にテストを追加
3. ① の整形オプションにも出したい場合は、`index.html` にチェックボックス、`app.js` の `csvOptions()`、
   `normalize.normalize_rows` の対象リストの3か所を変更

## C. 新しい機能の画面を足す（例：⑤ Excel → PDF）

1. **変換処理**：`app/converters/新しいファイル.py` を作る。画面のことは書かない。
2. **テスト**：`tests/test_converters.py`（または新しいテストファイル）に、小さなサンプルを作って変換を確かめるテストを書く。
3. **Api**：`app/main.py` の `Api` に関数を追加し、`@safe` を付ける。
   - 戻り値は辞書（`{"path": ..., "count": ...}`）。キャンセルは `{"cancelled": True}`。
   - 保存先は `self._save_dialog(...)` か `FOLDER_DIALOG` で利用者に選ばせる。
   - 時間がかかる処理は `self._progress(i, total, "ファイル名")` で進み具合を出す。
4. **画面**：
   - `index.html`：左メニューに `<button class="nav-item" data-view="新しい名前">`、本文に `<section class="view" id="view-新しい名前">`
   - `app.js`：`// ===== ⑤ ...` の区切りを作り、`S` に状態を追加、`bind()` にイベント、`init()` に最初の描画を追加
5. **にせ Python**：`tests/ui/mock_api.js` に、追加した Api 関数のにせ物を追加
6. **画面テスト**：`tests/test_ui_smoke.py` に、その画面を操作するテストを追加
7. 依存ライブラリを足した場合は `requirements.txt`（＋ PyInstaller で必要なら `build.py` の `--collect-all`）
8. `README.md` の「できること」の表、`docs/ARCHITECTURE.md` のファイル表、`CHANGELOG.md`、`app/version.py` を更新
9. `scripts/check.py` → 合格したらコミット

## D. 不具合を直す

1. まず、その不具合を再現する**失敗するテスト**を書く。
2. 直す。
3. そのテストを含めて `scripts/check.py` が合格することを確認。
4. `CHANGELOG.md` に「修正」として記録（バージョンの3つ目の数字を上げる：0.2.0 → 0.2.1）。

## バージョン番号の付け方

`大.中.小`
- 小：不具合の修正だけ（0.2.0 → 0.2.1）
- 中：機能の追加・変更（0.2.1 → 0.3.0）
- 大：使い方が大きく変わる・設定の互換がなくなる（0.x → 1.0.0）
