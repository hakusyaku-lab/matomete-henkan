"""samples/（テスト用ファイル）が「読んでください.txt」に書いた通りに変換されるかの検査。

サンプルを作り直したら（scripts/make_samples.py）、ここも通ることを確認してください。
"""
from pathlib import Path

import pytest
from PIL import Image, ImageOps

from converters import csv_tools, image_tools, mapping, normalize, pdf_tools, text_io

S = Path(__file__).resolve().parents[1] / "samples"
CSV = S / "1_CSV変換・結合"
IMG = S / "2_画像一括変換"
MAP = S / "3_CSV形式変換"
PDF = S / "4_PDF結合・分割"

pytestmark = pytest.mark.skipif(not S.exists(), reason="samples/ がありません（python scripts/make_samples.py）")


def test_csv_samples(tmp_path):
    a = text_io.read_table(CSV / "売上_店舗A_ShiftJIS.csv")
    b = text_io.read_table(CSV / "売上_店舗B_UTF8BOM.csv")
    c = text_io.read_table(CSV / "売上_店舗C_タブ区切り.txt")
    assert (a["encoding_label"], b["encoding_label"], c["encoding_label"]) == ("Shift_JIS", "UTF-8（BOM付き）", "UTF-8")
    assert c["delimiter"] == "\t" and "\n" in c["rows"][2][3]
    merged = csv_tools.merge_tables([a, b, c])
    head = merged[0]
    assert head[:8] == a["rows"][0] and head[-1] == "備考" and len(merged) == 1 + 4 + 3 + 2
    rows = normalize.normalize_rows(merged, {"hankaku": True, "kishu": True, "wareki": True})
    first = dict(zip(head, rows[1]))
    assert first["日付"] == "2024/04/01" and first["伝票番号"] == "0001"
    assert first["商品コード"] == "AB－100" and first["取引先"] == "(株)サンプル商事"
    assert dict(zip(head, rows[4]))["日付"] == "2024/04/04"
    assert {u["char"] for u in text_io.find_unencodable(rows)} == {"🚚"}
    out = tmp_path / "o.xlsx"
    csv_tools.export_rows(out, rows, "xlsx")
    from openpyxl import load_workbook

    assert load_workbook(out).active["B2"].value == "0001"
    text_io.read_table(CSV / "壊れたファイル.csv")  # 落ちない


def test_image_samples(tmp_path):
    files = sorted(IMG.iterdir())
    imgs = [p for p in files if p.suffix.lower() in image_tools.IMAGE_EXTS]
    assert len(imgs) == len(files) - 1  # .txt だけ除外
    info = {p.name: image_tools.inspect_image(p) for p in imgs}
    assert all("error" not in i for i in info.values()), info
    assert info["ロゴ_透明あり.png"]["has_alpha"] and info["アニメーション.gif"]["animated"]
    assert (info["写真_スマホ縦向き.jpg"]["width"], info["写真_スマホ縦向き.jpg"]["height"]) == (900, 1200)
    opts = {"fmt": "jpeg", "max_side": 1200, "square": False, "strip_gps": True}
    res = {p.name: image_tools.convert_image(p, tmp_path, opts) for p in imgs}
    size = lambda n: Image.open(res[n]["output"]).size
    assert size("写真_横長_位置情報あり.jpg") == (1200, 750)
    assert size("小さい画像_400x300.bmp") == (400, 300)
    assert size("写真_スマホ縦向き.jpg") == (900, 1200)
    assert ImageOps.exif_transpose(Image.open(res["写真_スマホ縦向き.jpg"]["output"])).size == (900, 1200)
    assert 0x8825 not in Image.open(res["写真_横長_位置情報あり.jpg"]["output"]).getexif()
    assert "透明部分を白にしました" in res["ロゴ_透明あり.png"]["notes"]
    assert "アニメーションは1コマ目だけになりました" in res["アニメーション.gif"]["notes"]
    sq = image_tools.convert_image(IMG / "商品_縦長.png", tmp_path / "sq", {"fmt": "png", "square": True, "max_side": 0})
    im = Image.open(sq["output"])
    assert im.size == (1200, 1200) and im.getpixel((5, 600))[:3] == (255, 255, 255)


def test_mapping_samples():
    src = text_io.read_table(MAP / "元データ_モールA商品一覧.csv")
    target = text_io.read_table(MAP / "変換先の見本_モールB形式.csv")["rows"][0]
    auto = {m["target"]: m["source"] for m in mapping.auto_mapping(src["rows"][0], target)}
    assert auto["商品名"] == "商品名" and auto["発売日"] == "発売日" and auto["商品コード"] == ""
    m = [
        {"target": "商品コード", "source": "商品管理番号", "ops": []},
        {"target": "商品名", "source": "商品名", "ops": ["hankaku", "kana_zenkaku", "kishu"]},
        {"target": "価格", "source": "販売価格", "ops": ["remove_comma"]},
        {"target": "説明", "source": "商品説明文", "ops": ["remove_newline", "trim"]},
        {"target": "送料区分", "source": "__fixed__", "fixed": "送料無料", "ops": []},
        {"target": "発売日", "source": "発売日", "ops": ["wareki"]},
    ]
    out = mapping.apply_mapping(src["rows"], m)
    assert out[1] == ["A-0001", "TシャツLサイズ ホワイト", "2980", "綿100％。 洗濯機で洗えます。", "送料無料", "2024/05/01"]
    assert out[2][1] == "マグカップ(株)オリジナル" and out[3][3] == "前後に空白あり"


def test_pdf_samples(tmp_path):
    inv, dlv, doc = PDF / "請求書_サンプル_4ページ.pdf", PDF / "納品書_サンプル_3ページ.pdf", PDF / "資料_サンプル_10ページ.pdf"
    assert [pdf_tools.inspect_pdf(p, with_thumbs=False)["pages"] for p in (inv, dlv, doc)] == [4, 3, 10]
    assert "error" in pdf_tools.inspect_pdf(PDF / "壊れたPDF.pdf", with_thumbs=False)
    assert pdf_tools.merge_pdfs([str(dlv), str(inv)], tmp_path / "m.pdf") == 7
    assert len(pdf_tools.split_pdf(doc, tmp_path / "s", every=3)) == 4
    assert pdf_tools.extract_pages(doc, "1-3, 5", tmp_path / "e.pdf") == 4
    with pytest.raises(ValueError, match="範囲外"):
        pdf_tools.parse_ranges("12", 10)
