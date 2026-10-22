"""画面の動作テスト（ブラウザで画面を開き、4つの機能を一通り操作して JavaScript のエラーが出ないか見る）。

Python 側は tests/ui/mock_api.js の「にせ Python」に置き換えます。
playwright が入っていない環境では自動でスキップします（pip install playwright && playwright install chromium）。
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "app" / "ui" / "index.html").as_uri()
MOCK = (ROOT / "tests" / "ui" / "mock_api.js").read_text(encoding="utf-8")

sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def page():
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # ブラウザ本体が無い
            pytest.skip(f"chromium を起動できません: {e}")
        pg = browser.new_page(viewport={"width": 1280, "height": 860})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
        pg.add_init_script(MOCK)
        pg.goto(INDEX)
        pg.wait_for_function("window.__calls.includes('tpl_list')")
        pg.errors = errors
        yield pg
        browser.close()


def _toast(pg):
    pg.wait_for_selector("#toast:not([hidden])")
    return pg.inner_text("#toast")


def test_start(page):
    assert page.inner_text("#version") == "バージョン 0.0.0-test"
    assert page.is_visible("#view-csv")
    assert page.errors == []


def test_csv(page):
    page.click(".nav-item[data-view=csv]")
    page.evaluate("window.onFilesDropped(['/a.csv','/b.csv'])")
    page.wait_for_selector("#csv-files tr:nth-child(2)")
    assert page.inner_text("#csv-count") == "2"
    assert page.inner_text("#csv-run") == "結合して保存"
    page.click("button[data-fmt=csv_sjis]")
    page.wait_for_selector("#csv-notices .notice.warn")
    page.click("#csv-run")
    assert "保存しました" in _toast(page)
    page.click("#csv-clear")
    assert page.is_disabled("#csv-run")
    assert page.errors == []


def test_image(page):
    page.click(".nav-item[data-view=image]")
    page.evaluate("window.onFilesDropped(['/1.png','/2.png'])")
    page.wait_for_selector("#img-grid .thumb >> nth=1")
    assert page.inner_text("#img-run") == "2枚を変換"
    page.click("#img-fmt button[data-fmt=webp]")
    assert page.is_visible("#img-lossless-wrap")
    page.check("#img-seq")
    assert page.is_visible("#img-prefix-wrap")
    page.click("#img-run")
    assert "2枚を保存しました" in _toast(page)
    assert page.errors == []


def test_map(page):
    page.click(".nav-item[data-view=map]")
    page.evaluate("window.onFilesDropped(['/src.csv'])")
    page.wait_for_function("document.querySelector('#map-src-info').textContent.includes('src.csv')")
    page.click("#map-copy-all")
    page.wait_for_selector("#map-rows input[data-map=target] >> nth=1")
    page.select_option("select[data-map=source][data-i='1']", "__fixed__")
    page.fill("input[data-map=fixed][data-i='1']", "固定")
    page.wait_for_selector("#map-preview td:has-text('固定')")
    assert page.locator("#map-rows input[data-op=remove_comma]").count() == 2
    page.select_option("#map-tpl", "テスト")
    page.wait_for_function("document.querySelector('#map-tpl-name').value === 'テスト'")
    assert page.input_value("#map-enc") == "cp932"
    page.click("#map-run")
    assert "保存しました" in _toast(page)
    assert page.errors == []


def test_pdf(page):
    page.click(".nav-item[data-view=pdf]")
    page.evaluate("window.onFilesDropped(['/a.pdf','/b.pdf'])")
    page.wait_for_selector("#pdf-list .pdf-file >> nth=1")
    assert not page.is_disabled("#pdf-run")
    page.click("#pdf-modes button[data-mode=extract]")
    page.fill("#pdf-ranges", "1, 3")
    assert page.locator("#pdf-list .pdf-file.target .page.sel").count() == 2
    page.click("#pdf-run")
    assert "抜き出して保存しました" in _toast(page)
    page.click("#pdf-modes button[data-mode=split]")
    page.click("#pdf-run")
    assert "分けて保存しました" in _toast(page)
    assert page.errors == []
