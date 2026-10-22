"""画面（app/ui）と Python（app/main.py・converters）の「約束」が守られているかの検査。

AI や人が片方だけを書き換えたときに起きやすい食い違いを、起動する前に見つけます。
ここが失敗したら、どちらか一方だけを変更していないか確認してください。
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "app" / "ui"
JS = (UI / "app.js").read_text(encoding="utf-8")
HTML = (UI / "index.html").read_text(encoding="utf-8")


def _api_methods():
    pytest.importorskip("webview")
    import main

    return {n for n in dir(main.Api) if not n.startswith("_") and callable(getattr(main.Api, n))}


def test_js_calls_exist_in_python_api():
    """app.js の call('xxx') で呼んでいる名前が、すべて main.Api に存在する。"""
    called = set(re.findall(r"\bcall\(\s*'([a-z_]+)'", JS))
    assert called, "app.js から call('...') が見つかりません"
    missing = called - _api_methods()
    assert not missing, f"Python 側に無い関数を画面が呼んでいます: {sorted(missing)}"


def test_python_api_is_used_by_ui():
    """main.Api の公開関数は、画面から使われている（使われない関数の放置を防ぐ）。"""
    called = set(re.findall(r"\bcall\(\s*'([a-z_]+)'", JS))
    unused = _api_methods() - called
    assert not unused, f"画面から使われていない Api 関数があります（不要なら削除、必要なら画面から呼ぶ）: {sorted(unused)}"


def test_js_ids_exist_in_html():
    """app.js が $('#id') で参照している要素が index.html に存在する。"""
    ids_in_html = set(re.findall(r'\bid="([^"]+)"', HTML))
    # 画面の操作中に JavaScript が作る要素（index.html には無いのが正しい）
    created_by_js = {"toast-open", "pdf-every", "pdf-ranges"}
    used = set(re.findall(r"\$\('#([A-Za-z0-9_-]+)", JS))
    missing = used - ids_in_html - created_by_js
    assert not missing, f"index.html に無い id を app.js が使っています: {sorted(missing)}"
    for i in created_by_js:
        assert f'id="{i}"' in JS, f"{i} は app.js が作るはずですが、作っている箇所が見つかりません"


def test_html_ids_are_unique():
    ids = re.findall(r'\bid="([^"]+)"', HTML)
    dup = {i for i in ids if ids.count(i) > 1}
    assert not dup, f"index.html に同じ id が複数あります: {sorted(dup)}"


def test_views_and_nav_match():
    """左メニューのボタン（data-view）と画面（id="view-xxx"）が1対1で対応している。"""
    nav = set(re.findall(r'data-view="([a-z]+)"', HTML))
    views = set(re.findall(r'id="view-([a-z]+)"', HTML))
    assert nav == views, f"メニュー {sorted(nav)} と画面 {sorted(views)} が一致しません"


def test_csv_formats_match():
    from converters import csv_tools

    html = set(re.findall(r'id="csv-fmt".*?</div>', HTML, re.S)[0].split('data-fmt="')[1:])
    html = {h.split('"')[0] for h in html}
    assert html == set(csv_tools.FORMATS), f"CSV の出力形式ボタン {sorted(html)} と csv_tools.FORMATS {sorted(csv_tools.FORMATS)} が一致しません"


def test_image_formats_match():
    from converters import image_tools

    block = re.findall(r'id="img-fmt".*?</div>', HTML, re.S)[0]
    html = set(re.findall(r'data-fmt="([a-z]+)"', block))
    assert html == set(image_tools.OUT_EXT), f"画像の出力形式ボタン {sorted(html)} と image_tools.OUT_EXT {sorted(image_tools.OUT_EXT)} が一致しません"


def test_map_encodings_match():
    from converters import text_io

    block = re.findall(r'id="map-enc".*?</select>', HTML, re.S)[0]
    html = set(re.findall(r'value="([^"]+)"', block))
    assert html == set(text_io.OUTPUT_ENCODINGS)


def test_op_labels_cover_ops():
    from converters import normalize

    assert set(normalize.OP_LABELS) == set(normalize.OPS), "normalize.OPS と OP_LABELS のキーをそろえてください"


def test_csv_options_known_to_python():
    """CSV 画面の整形オプション（app.js の csvOptions）の名前を、Python 側が理解している。"""
    from converters import normalize

    body = re.findall(r"function csvOptions\(\) \{(.*?)\n  \}", JS, re.S)[0]
    keys = set(re.findall(r"^\s*([a-z_]+):", body, re.M))
    handled = {"trim", "hankaku", "kana_zenkaku", "kishu", "wareki"}
    assert handled <= set(normalize.OPS)
    other = keys - handled
    assert other == {"protect_zero", "add_source"}, f"Python 側で扱っていないオプションがあります: {sorted(other - {'protect_zero', 'add_source'})}"
    src = (ROOT / "app" / "converters" / "normalize.py").read_text(encoding="utf-8")
    assert all(f'"{k}"' in src for k in handled)
