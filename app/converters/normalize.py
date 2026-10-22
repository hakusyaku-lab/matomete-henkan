"""データの整形（全角→半角、和暦→西暦、機種依存文字の置き換えなど）。"""
from __future__ import annotations

import re
import unicodedata

# 全角英数字 → 半角
_ZEN_ALNUM = {c: c - 0xFEE0 for c in list(range(0xFF10, 0xFF1A)) + list(range(0xFF21, 0xFF3B)) + list(range(0xFF41, 0xFF5B))}


def to_hankaku_alnum(s: str) -> str:
    """全角の英字・数字だけを半角にする（記号やカナはそのまま）。"""
    return s.translate(_ZEN_ALNUM)


def hankaku_kana_to_zenkaku(s: str) -> str:
    """半角カナ（ｱｲｳ）を全角カナ（アイウ）にする。"""
    if not any("｡" <= ch <= "ﾟ" for ch in s):
        return s
    out = []
    buf = ""
    for ch in s:
        if "｡" <= ch <= "ﾟ":
            buf += ch
        else:
            if buf:
                out.append(unicodedata.normalize("NFKC", buf))
                buf = ""
            out.append(ch)
    if buf:
        out.append(unicodedata.normalize("NFKC", buf))
    return "".join(out)


# 和暦 → 西暦
_ERAS = {"令和": 2018, "平成": 1988, "昭和": 1925, "大正": 1911, "明治": 1867,
         "R": 2018, "H": 1988, "S": 1925, "T": 1911, "M": 1867}
_WAREKI_FULL = re.compile(r"(令和|平成|昭和|大正|明治)\s*(元|\d{1,2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_WAREKI_SHORT = re.compile(r"^\s*([RHSTMrhstm])\s*(\d{1,2})[./\-](\d{1,2})[./\-](\d{1,2})\s*$")


def _fmt_date(era: str, year: str, month: str, day: str) -> str | None:
    y = 1 if year == "元" else int(year)
    m, d = int(month), int(day)
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return None
    return f"{_ERAS[era] + y:04d}/{m:02d}/{d:02d}"


def wareki_to_seireki(s: str) -> str:
    """「令和6年1月2日」「R6.1.2」などを「2024/01/02」にする。

    「R6.1.2」のような略記は、商品コードなどの誤変換を避けるためセル全体が日付のときだけ変換します。
    """
    t = to_hankaku_alnum(s)
    if "年" in t:
        def repl(m: re.Match) -> str:
            return _fmt_date(*m.groups()) or m.group(0)
        new = _WAREKI_FULL.sub(repl, t)
        if new != t:
            return new
    m = _WAREKI_SHORT.match(t)
    if m:
        era, y, mo, d = m.groups()
        out = _fmt_date(era.upper(), y, mo, d)
        if out:
            return out
    return s


# 機種依存文字の置き換え
_CIRCLED = {chr(0x2460 + i): f"({i + 1})" for i in range(20)}  # ①〜⑳
_KISHU_NFKC = set(
    "㈱㈲㈹㍉㌔㌢㍍㌘㌧㌃㌶㍑㍗㌍㌦㌣㌫㍊㌻㎜㎝㎞㎎㎏㏄㎡№℡㊤㊥㊦㊧㊨㍻㍼㍽㍾"
    "ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ"
)


def replace_kishu(s: str) -> str:
    """㈱→(株)、①→(1)、㎏→kg などに置き換える。"""
    if not s:
        return s
    out = []
    for ch in s:
        if ch in _CIRCLED:
            out.append(_CIRCLED[ch])
        elif ch in _KISHU_NFKC:
            out.append(unicodedata.normalize("NFKC", ch))
        else:
            out.append(ch)
    return "".join(out)


def remove_comma(s: str) -> str:
    """「1,280」→「1280」。数字の桁区切りのカンマだけを外す。"""
    t = s.strip()
    if re.fullmatch(r"[-+]?[\d,，]+(\.\d+)?", t):
        return t.replace(",", "").replace("，", "")
    return s


def remove_newline(s: str) -> str:
    return s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


# 列単位の加工（CSV形式変換の「加工」欄で使う）
OPS = {
    "hankaku": to_hankaku_alnum,
    "kana_zenkaku": hankaku_kana_to_zenkaku,
    "wareki": wareki_to_seireki,
    "kishu": replace_kishu,
    "remove_comma": remove_comma,
    "trim": str.strip,
    "remove_newline": remove_newline,
}

OP_LABELS = {
    "hankaku": "英数を半角",
    "kana_zenkaku": "半角カナを全角",
    "wareki": "和暦→西暦",
    "kishu": "機種依存文字",
    "remove_comma": "カンマ除去",
    "trim": "前後の空白除去",
    "remove_newline": "改行除去",
}


def apply_ops(value: str, ops: list[str]) -> str:
    for op in ops:
        fn = OPS.get(op)
        if fn:
            value = fn(value)
    return value


def normalize_rows(rows: list[list[str]], options: dict, has_header: bool = True) -> list[list[str]]:
    """CSV変換・結合画面の整形オプションを表全体に適用する。"""
    ops = [k for k in ("trim", "hankaku", "kana_zenkaku", "kishu", "wareki") if options.get(k)]
    if not ops:
        return rows
    start = 1 if has_header else 0
    out = rows[:start]
    for row in rows[start:]:
        out.append([apply_ops(v, ops) for v in row])
    return out
