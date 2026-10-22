"""① CSV 変換・結合：複数ファイルの結合と、Excel／CSV／JSON への書き出し。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .text_io import write_csv

SOURCE_COL = "元ファイル"


def uniquify(header: list[str]) -> list[str]:
    """重複や空の見出しに番号を付けて一意にする（例：金額, 金額(2)）。"""
    seen: dict[str, int] = {}
    out = []
    for i, h in enumerate(header):
        name = h.strip() or f"列{i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}({seen[name]})"
        else:
            seen[name] = 1
        out.append(name)
    return out


def merge_tables(tables: list[dict], add_source: bool = False) -> list[list[str]]:
    """見出し名をそろえて縦に結合する。

    列の並びが違うファイルや、片方にしかない列があっても、見出し名で対応させます。
    """
    columns: list[str] = []
    prepared = []
    for t in tables:
        rows = t["rows"]
        if not rows:
            continue
        header = uniquify(rows[0])
        for h in header:
            if h not in columns:
                columns.append(h)
        prepared.append((t, header, rows[1:]))

    out_header = ([SOURCE_COL] if add_source else []) + columns
    out = [out_header]
    for t, header, body in prepared:
        pos = {h: i for i, h in enumerate(header)}
        for row in body:
            values = [row[pos[c]] if c in pos and pos[c] < len(row) else "" for c in columns]
            out.append(([t["name"]] if add_source else []) + values)
    return out


_NUMBER = re.compile(r"^-?(0|[1-9]\d{0,14})(\.\d+)?$")


def _to_number(v: str):
    """先頭が0でない普通の数字だけを数値にする（電話番号・郵便番号・長いコードは文字列のまま）。"""
    if _NUMBER.match(v):
        return float(v) if "." in v else int(v)
    return v


def write_xlsx(path: str | Path, rows: list[list[str]], protect_zero: bool = True, sheet_name: str = "Sheet1") -> None:
    """Excel 形式で書き出す。

    protect_zero=True のときは全セルを「文字列」として保存し、先頭の0や長い数字の指数表記化を防ぎます。
    False のときは、普通の数字だけを数値にして集計できるようにします。
    """
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(sheet_name[:31])
    for r_i, row in enumerate(rows):
        cells = []
        for v in row:
            value = v if (protect_zero or r_i == 0) else _to_number(v)
            cell = WriteOnlyCell(ws, value=value)
            if isinstance(value, str):
                cell.data_type = "s"  # 「=」で始まる値を数式として扱わない
                if protect_zero:
                    cell.number_format = "@"
            cells.append(cell)
        ws.append(cells)
    wb.save(path)


def write_json(path: str | Path, rows: list[list[str]]) -> None:
    """見出し行をキーにした JSON 配列で書き出す（値はすべて文字列）。"""
    if not rows:
        data = []
    else:
        header = uniquify(rows[0])
        data = [{h: (row[i] if i < len(row) else "") for i, h in enumerate(header)} for row in rows[1:]]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


FORMATS = {
    "xlsx": (".xlsx", "Excel ファイル"),
    "csv_utf8": (".csv", "CSV（UTF-8 BOM付き）"),
    "csv_sjis": (".csv", "CSV（Shift_JIS）"),
    "json": (".json", "JSON"),
}


def export_rows(path: str | Path, rows: list[list[str]], fmt: str, protect_zero: bool = True) -> None:
    if fmt == "xlsx":
        write_xlsx(path, rows, protect_zero=protect_zero)
    elif fmt == "csv_utf8":
        write_csv(path, rows, "utf-8-sig")
    elif fmt == "csv_sjis":
        write_csv(path, rows, "cp932")
    elif fmt == "json":
        write_json(path, rows)
    else:
        raise ValueError(f"未対応の出力形式です: {fmt}")
