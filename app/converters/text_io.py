"""テキスト（CSV・TXT）の読み書きと文字コード判定。"""
from __future__ import annotations

import codecs
import csv
import io
from pathlib import Path

ENCODING_LABELS = {
    "utf-8-sig": "UTF-8（BOM付き）",
    "utf-8": "UTF-8",
    "cp932": "Shift_JIS",
    "utf-16": "UTF-16",
    "euc_jp": "EUC-JP",
}

# 出力で選べる文字コード
OUTPUT_ENCODINGS = ("utf-8-sig", "utf-8", "cp932")


def encoding_label(enc: str) -> str:
    return ENCODING_LABELS.get(enc, enc)


def decode_bytes(raw: bytes) -> tuple[str, str]:
    """バイト列を文字列にする。戻り値は (文字列, 判定した文字コード)。

    判定の順番:
      1. BOM（ファイル先頭の目印）があればそれに従う
      2. UTF-8 として矛盾なく読めれば UTF-8
      3. Shift_JIS（Windows拡張を含む cp932）として読めれば Shift_JIS
      4. それでも駄目なら charset-normalizer に推定させる
    """
    if raw.startswith(codecs.BOM_UTF8):
        return raw[len(codecs.BOM_UTF8):].decode("utf-8", errors="replace"), "utf-8-sig"
    if raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE):
        return raw.decode("utf-16", errors="replace"), "utf-16"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("cp932"), "cp932"
    except UnicodeDecodeError:
        pass
    try:
        from charset_normalizer import from_bytes

        best = from_bytes(raw).best()
        if best is not None:
            return str(best), best.encoding
    except ImportError:
        pass
    return raw.decode("cp932", errors="replace"), "cp932"


def detect_delimiter(text: str) -> str:
    """区切り文字（カンマ／タブ／セミコロン）を先頭数行から推定する。"""
    head = "\n".join(text.splitlines()[:5])
    counts = {d: head.count(d) for d in (",", "\t", ";")}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def read_table(path: str | Path) -> dict:
    """CSV/TXT を読み込み、行のリストと判定結果を返す。"""
    p = Path(path)
    text, enc = decode_bytes(p.read_bytes())
    delim = detect_delimiter(text)
    rows = [list(r) for r in csv.reader(io.StringIO(text, newline=""), delimiter=delim)]
    while rows and not any(c.strip() for c in rows[-1]):
        rows.pop()
    width = max((len(r) for r in rows), default=0)
    return {
        "path": str(p),
        "name": p.name,
        "encoding": enc,
        "encoding_label": ENCODING_LABELS.get(enc, enc),
        "delimiter": delim,
        "rows": rows,
        "row_count": max(len(rows) - 1, 0),  # 見出し行を除いたデータ行数
        "col_count": width,
    }


def find_unencodable(rows: list[list[str]], encoding: str = "cp932", limit: int = 200) -> list[dict]:
    """指定の文字コードで表せない文字を探す（Shift_JIS 出力前のチェック用）。"""
    found: list[dict] = []
    for r_i, row in enumerate(rows):
        for c_i, value in enumerate(row):
            for ch in value:
                try:
                    ch.encode(encoding)
                except UnicodeEncodeError:
                    found.append({"row": r_i + 1, "col": c_i + 1, "char": ch, "value": value[:40]})
                    if len(found) >= limit:
                        return found
                    break
    return found


def write_csv(path: str | Path, rows: list[list[str]], encoding: str = "utf-8-sig", delimiter: str = ",") -> None:
    """CSV を書き出す。Shift_JIS で表せない文字は「?」に置き換える。"""
    if encoding not in OUTPUT_ENCODINGS:
        raise ValueError(f"未対応の文字コードです: {encoding}")
    errors = "replace" if encoding == "cp932" else "strict"
    with open(path, "w", encoding=encoding, errors=errors, newline="") as f:
        writer = csv.writer(f, delimiter=delimiter, lineterminator="\r\n")
        writer.writerows(rows)
