"""動作確認用のテストファイルを samples/ に作り直すスクリプト。

    python scripts/make_samples.py

中身はすべて架空のデータです（実在の人・会社・番号は使わない）。
作られるファイルと確認ポイントは samples/読んでください.txt にまとめています。
新しい機能を足したら、ここにその機能用のサンプルも足してください。
"""
from __future__ import annotations

import csv
import io
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples"
D_CSV = OUT / "1_CSV変換・結合"
D_IMG = OUT / "2_画像一括変換"
D_MAP = OUT / "3_CSV形式変換"
D_PDF = OUT / "4_PDF結合・分割"


# ---------------------------------------------------------------- 共通
def write_csv(path: Path, rows: list[list[str]], encoding: str, delimiter: str = ",") -> None:
    buf = io.StringIO()
    csv.writer(buf, delimiter=delimiter, lineterminator="\r\n").writerows(rows)
    data = buf.getvalue()
    if encoding == "utf-8-sig":
        path.write_bytes(b"\xef\xbb\xbf" + data.encode("utf-8"))
    else:
        path.write_bytes(data.encode(encoding))


def jp_font(size: int):
    """日本語が書けるフォント（無ければ英字だけの標準フォント）。"""
    for cand in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    ]:
        if Path(cand).exists():
            try:
                return ImageFont.truetype(cand, size)
            except OSError:
                pass
    return ImageFont.load_default()


# ---------------------------------------------------------------- ① CSV
def make_csv() -> None:
    D_CSV.mkdir(parents=True)
    # 店舗A：Excel でよくある Shift_JIS。先頭0・全角英数・㈱・和暦を含む
    write_csv(D_CSV / "売上_店舗A_ShiftJIS.csv", [
        ["日付", "伝票番号", "商品コード", "商品名", "数量", "金額", "取引先", "電話番号"],
        ["令和6年4月1日", "0001", "ＡＢ－１００", "ボールペン（黒）", "10", "1,100", "㈱サンプル商事", "03-0000-0001"],
        ["令和6年4月2日", "0002", "ＡＢ－２００", "ノート Ａ５", "5", "750", "㈲テスト文具", "06-0000-0002"],
        ["令和6年4月3日", "0003", "CD-300", "クリアファイル①", "20", "2,000", "サンプル工業㈱", "0120-000-003"],
        ["R6.4.4", "0004", "CD-400", "付箋 ｲｴﾛｰ", "8", "640", "架空物産", "090-0000-0004"],
    ], "cp932")
    # 店舗B：UTF-8（BOM付き）。列の並びが店舗Aと違い、「備考」列が増えている。絵文字入り
    write_csv(D_CSV / "売上_店舗B_UTF8BOM.csv", [
        ["伝票番号", "日付", "商品名", "商品コード", "金額", "数量", "取引先", "電話番号", "備考"],
        ["0101", "2024/04/05", "ホッチキス", "EF-500", "980", "2", "サンプル商事", "011-000-0101", "急ぎ🚚"],
        ["0102", "2024/04/06", "髙橋さん用 名札", "EF-600", "300", "3", "テスト商店", "052-000-0102", "旧字体（髙・﨑）"],
        ["0103", "2024/04/07", "電卓", "GH-700", "1,980", "1", "架空商会", "092-000-0103", "値の中に,カンマ"],
    ], "utf-8-sig")
    # 店舗C：タブ区切りの UTF-8 テキスト（BOM なし）
    write_csv(D_CSV / "売上_店舗C_タブ区切り.txt", [
        ["日付", "伝票番号", "商品コード", "商品名", "数量", "金額", "取引先", "電話番号"],
        ["2024/04/08", "0201", "IJ-800", "マスキングテープ", "6", "720", "テスト雑貨", "075-000-0201"],
        ["2024/04/09", "0202", "IJ-900", "セロハンテープ\n（改行入り）", "4", "400", "架空ストア", "045-000-0202"],
    ], "utf-8", delimiter="\t")
    # 壊れたファイル（エラー表示の確認用）
    (D_CSV / "壊れたファイル.csv").write_bytes(bytes(range(256)) * 4)


# ---------------------------------------------------------------- ② 画像
def _photo(w: int, h: int, c1, c2, label: str) -> Image.Image:
    """グラデーションと文字の入った写真風の画像。"""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x / w + y / h) / 2
            px[x, y] = tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
    d = ImageDraw.Draw(img)
    d.ellipse((w * 0.3, h * 0.25, w * 0.7, h * 0.75), fill=(255, 255, 255))
    d.text((w * 0.05, h * 0.05), label, fill=(20, 20, 20), font=jp_font(max(w // 16, 14)))
    d.text((w * 0.05, h * 0.88), f"{w}x{h}", fill=(20, 20, 20), font=jp_font(max(w // 24, 12)))
    return img


def make_images() -> None:
    D_IMG.mkdir(parents=True)
    # 横長の写真（位置情報つき）
    img = _photo(1600, 1000, (70, 130, 180), (240, 200, 120), "横長の写真（位置情報あり）")
    exif = img.getexif()
    exif[0x010F] = "SampleCamera"
    exif[0x8825] = {1: "N", 2: (35.0, 0.0, 0.0), 3: "E", 4: (135.0, 0.0, 0.0)}  # 架空の位置情報
    img.save(D_IMG / "写真_横長_位置情報あり.jpg", quality=92, exif=exif)

    # 縦向きで撮ったスマホ写真（向き情報で回転させる必要がある）
    portrait = _photo(900, 1200, (180, 90, 90), (250, 230, 200), "向き補正のテスト")
    raw = portrait.rotate(90, expand=True)  # 画素は横倒し（1200x900）で保存し、表示時に右へ90度回す
    exif = raw.getexif()
    exif[0x0112] = 6  # 「90度回して表示」の指定
    raw.save(D_IMG / "写真_スマホ縦向き.jpg", quality=92, exif=exif)

    # 透明部分のある PNG（JPEG にすると透明が白になる）
    logo = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
    d = ImageDraw.Draw(logo)
    d.rounded_rectangle((100, 100, 700, 700), radius=120, fill=(31, 79, 184, 255))
    d.text((180, 360), "透明あり", fill=(255, 255, 255, 255), font=jp_font(80))
    logo.save(D_IMG / "ロゴ_透明あり.png")

    # 縦長の商品画像（正方形化の確認）
    _photo(600, 1200, (90, 160, 110), (230, 240, 230), "縦長").save(D_IMG / "商品_縦長.png")

    # 小さい画像（拡大しないことの確認）
    _photo(400, 300, (200, 200, 90), (250, 250, 220), "小さい").save(D_IMG / "小さい画像_400x300.bmp")

    # WebP
    _photo(1000, 1000, (120, 80, 160), (230, 210, 240), "WebP").save(D_IMG / "正方形.webp", quality=90)

    # アニメーション GIF（1コマ目だけになる）
    frames = []
    for i, col in enumerate([(220, 60, 60), (60, 160, 60), (60, 90, 220)]):
        f = Image.new("RGB", (300, 300), col)
        ImageDraw.Draw(f).text((110, 120), f"{i + 1}", fill=(255, 255, 255), font=jp_font(60))
        frames.append(f.convert("P"))
    frames[0].save(D_IMG / "アニメーション.gif", save_all=True, append_images=frames[1:], duration=500, loop=0)

    # iPhone の HEIC
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
        _photo(1200, 900, (40, 110, 140), (200, 230, 240), "iPhone の HEIC").save(D_IMG / "iPhone写真.heic", quality=80)
    except Exception as e:  # pragma: no cover
        print("HEIC は作れませんでした:", e)

    # 画像ではないファイル（外されることの確認）
    (D_IMG / "画像ではないファイル.txt").write_text("これは画像ではありません。\n", encoding="utf-8")


# ---------------------------------------------------------------- ③ CSV 形式変換
def make_mapping() -> None:
    D_MAP.mkdir(parents=True)
    write_csv(D_MAP / "元データ_モールA商品一覧.csv", [
        ["商品管理番号", "商品名", "販売価格", "在庫数", "商品説明文", "発売日"],
        ["A-0001", "ＴシャツＬサイズ ﾎﾜｲﾄ", "2,980", "15", "綿100％。\n洗濯機で洗えます。", "令和6年5月1日"],
        ["A-0002", "マグカップ㈱オリジナル", "1,200", "0", "電子レンジ可", "令和6年6月15日"],
        ["A-0003", "トートバッグ", "3,500", "8", " 前後に空白あり ", "2024/07/01"],
    ], "cp932")
    write_csv(D_MAP / "変換先の見本_モールB形式.csv", [
        ["商品コード", "商品名", "価格", "在庫", "説明", "送料区分", "発売日"],
    ], "utf-8-sig")


# ---------------------------------------------------------------- ④ PDF
def make_pdfs() -> None:
    D_PDF.mkdir(parents=True)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfgen import canvas
    except ImportError:
        sys.exit("PDF の作成には reportlab が必要です: pip install reportlab")
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

    def make(path: Path, title: str, pages: int, color) -> None:
        c = canvas.Canvas(str(path), pagesize=A4)
        w, h = A4
        for i in range(1, pages + 1):
            c.setFillColorRGB(*color)
            c.rect(0, h - 90, w, 90, fill=1, stroke=0)
            c.setFillColorRGB(1, 1, 1)
            c.setFont("HeiseiKakuGo-W5", 26)
            c.drawString(40, h - 58, title)
            c.setFillColorRGB(0.1, 0.1, 0.1)
            c.setFont("HeiseiKakuGo-W5", 120)
            c.drawCentredString(w / 2, h / 2, f"{i} / {pages}")
            c.setFont("HeiseiKakuGo-W5", 14)
            c.drawCentredString(w / 2, h / 2 - 60, f"{title} の {i} ページ目（架空のサンプルです）")
            c.showPage()
        c.save()

    make(D_PDF / "請求書_サンプル_4ページ.pdf", "請求書（サンプル）", 4, (0.12, 0.31, 0.72))
    make(D_PDF / "納品書_サンプル_3ページ.pdf", "納品書（サンプル）", 3, (0.06, 0.48, 0.42))
    make(D_PDF / "資料_サンプル_10ページ.pdf", "資料（サンプル）", 10, (0.71, 0.33, 0.06))
    (D_PDF / "壊れたPDF.pdf").write_bytes(b"%PDF-1.4\nbroken file\n")


# ---------------------------------------------------------------- 説明書
README = """まとめて変換 ― テスト用ファイル

中身はすべて架空のデータです。アプリにドラッグ＆ドロップして、下の「確認すること」を試してください。
このフォルダは scripts\\make_samples.py で作り直せます。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① CSV 変換・結合（「1_CSV変換・結合」フォルダ）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・売上_店舗A_ShiftJIS.csv      Shift_JIS。先頭0の伝票番号、全角英数、㈱、和暦、半角カナ
・売上_店舗B_UTF8BOM.csv       UTF-8（BOM付き）。列の並びが違い「備考」列がある。絵文字・旧字体・値の中のカンマ
・売上_店舗C_タブ区切り.txt     タブ区切り。値の中に改行
・壊れたファイル.csv            わざと壊したファイル

確認すること
□ 3つ入れると、文字コードが「Shift_JIS」「UTF-8（BOM付き）」「UTF-8」と表示される
□ 「結合して保存」→ Excel で開くと、伝票番号の「0001」の0が消えていない
□ 列の並びが違っても、同じ見出しの列にそろって結合されている（店舗Bの「備考」は他の店舗では空欄）
□ 整形オプション：「全角の英数字を半角」で ＡＢ－１００ → AB－100、「機種依存文字」で ㈱ → (株)
□ 「和暦を西暦に変換」をオンにすると 令和6年4月1日 → 2024/04/01、R6.4.4 → 2024/04/04
□ 出力形式を「CSV（Shift_JIS）」にすると、絵文字（🚚）が「?」になる注意が出る
□ 壊れたファイルを入れても、アプリが止まらない

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
② 画像一括変換（「2_画像一括変換」フォルダ）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・写真_横長_位置情報あり.jpg     位置情報（架空）が入った写真
・写真_スマホ縦向き.jpg          スマホで縦にして撮った写真と同じ状態（向き情報つき）
・ロゴ_透明あり.png              背景が透明
・商品_縦長.png                  縦長
・小さい画像_400x300.bmp         小さい画像
・正方形.webp / アニメーション.gif / iPhone写真.heic
・画像ではないファイル.txt

確認すること
□ 全部入れると「画像ではないファイル」は外される
□ ロゴに「透明あり」の印が付き、JPEG を選ぶと「透明部分は白になります」の注意が出る
□ 「正方形にする」をオン → 縦長の商品画像が白い余白付きの正方形になる
□ 長辺 1200px → 横長の写真は 1200x750 に縮小、小さい画像は 400x300 のまま（拡大しない）
□ スマホ縦向きの写真が、変換後も正しく縦長になっている
□ 「位置情報を削除」オン → 変換後の写真のプロパティ（詳細）に GPS が無い
□ アニメーション GIF は「1コマ目だけになります」の注意が出る
□ HEIC が読み込めて JPEG に変換できる
□ 「ファイル名を連番にする」→ image_0001.jpg のような名前になる

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
③ CSV 形式変換（「3_CSV形式変換」フォルダ）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・元データ_モールA商品一覧.csv    変換元（Shift_JIS）
・変換先の見本_モールB形式.csv     変換先の見出しだけのファイル

確認すること
□ 元データを入れ、「変換先の見本CSVから列を読み込む」で見本を選ぶ → 同じ名前の「商品名」「発売日」が自動で対応する
□ 「商品コード」←「商品管理番号」、「価格」←「販売価格」（加工：カンマ除去）、「在庫」←「在庫数」、「説明」←「商品説明文」（加工：改行除去）を手で対応させる
□ 「送料区分」は「固定値を入れる」で「送料無料」
□ 「商品名」に「英数を半角」「半角カナを全角」「機種依存文字」→ ＴシャツＬサイズ ﾎﾜｲﾄ → TシャツLサイズ ホワイト
□ 「発売日」に「和暦→西暦」
□ プレビューで確認 →「テンプレートとして保存」→ アプリを開き直してテンプレートを選ぶと同じ設定に戻る
□ 「変換して保存」した CSV を Excel で開いて確認

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
④ PDF 結合・分割（「4_PDF結合・分割」フォルダ）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・請求書_サンプル_4ページ.pdf / 納品書_サンプル_3ページ.pdf / 資料_サンプル_10ページ.pdf
・壊れたPDF.pdf

確認すること
□ 各ページの縮小画像が表示される。壊れたPDFは「読み込めませんでした」と表示される
□ 結合：↑↓で順番を変えて保存 → 指定した順に 7ページ（請求書＋納品書）になる
□ 分割：資料（10ページ）を「3ページごと」→ 4ファイル（3・3・3・1ページ）
□ ページ抜き出し：資料（10ページ）を「対象」にして「1-3, 5」→ 青枠で選ばれたページが表示され、4ページのPDFになる
□ 資料に「12」のような範囲外を入れると、エラーの説明が日本語で出る
"""


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    make_csv()
    make_images()
    make_mapping()
    make_pdfs()
    (OUT / "読んでください.txt").write_bytes(b"\xef\xbb\xbf" + README.replace("\n", "\r\n").encode("utf-8"))
    n = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"samples/ に {n} 個のファイルを作りました")


if __name__ == "__main__":
    main()
