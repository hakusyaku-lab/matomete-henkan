"""④ PDF 結合・分割・ページ抜き出し。ページをそのまま移すので画質は変わりません。"""
from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .normalize import to_hankaku_alnum


def open_reader(path: str | Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            ok = reader.decrypt("")
        except Exception:
            ok = 0
        if not ok:
            raise ValueError(f"{Path(path).name} はパスワード付きのため扱えません")
    return reader


def render_thumbs(path: str | Path, max_pages: int = 30, width: int = 120) -> list[str]:
    """ページの縮小画像（data URL）。pypdfium2 がなければ空のリスト。"""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return []
    thumbs = []
    try:
        pdf = pdfium.PdfDocument(str(path))
        try:
            for i in range(min(len(pdf), max_pages)):
                page = pdf[i]
                scale = width / max(page.get_width(), 1)
                pil = page.render(scale=scale).to_pil().convert("RGB")
                buf = io.BytesIO()
                pil.save(buf, "JPEG", quality=70)
                thumbs.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())
                page.close()
        finally:
            pdf.close()
    except Exception:
        return []
    return thumbs


def inspect_pdf(path: str | Path, with_thumbs: bool = True) -> dict:
    p = Path(path)
    info = {"path": str(p), "name": p.name}
    try:
        info["pages"] = len(open_reader(p).pages)
        info["thumbs"] = render_thumbs(p) if with_thumbs else []
    except Exception as e:
        info["error"] = str(e) if isinstance(e, ValueError) else f"読み込めませんでした（{type(e).__name__}）"
    return info


def parse_ranges(text: str, total: int) -> list[int]:
    """「1-3, 5, 8-」を 0 始まりのページ番号のリストにする。全角や読点も受け付けます。"""
    t = to_hankaku_alnum(text).replace("、", ",").replace("，", ",").replace("－", "-").replace("〜", "-").replace("~", "-")
    t = re.sub(r"\s+", "", t)
    if not t:
        raise ValueError("ページを入力してください（例：1-3, 5）")
    pages: list[int] = []
    for part in t.split(","):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)?-(\d+)?|(\d+)", part)
        if not m:
            raise ValueError(f"「{part}」はページ指定として読めません（例：1-3, 5）")
        if m.group(3):
            start = end = int(m.group(3))
        else:
            start = int(m.group(1) or 1)
            end = int(m.group(2) or total)
        if start < 1 or end > total or start > end:
            raise ValueError(f"「{part}」は範囲外です（1〜{total}ページ）")
        pages.extend(range(start - 1, end))
    return pages


def merge_pdfs(paths: list[str], out_path: str | Path) -> int:
    writer = PdfWriter()
    total = 0
    for p in paths:
        reader = open_reader(p)
        for page in reader.pages:
            writer.add_page(page)
            total += 1
    with open(out_path, "wb") as f:
        writer.write(f)
    return total


def split_pdf(path: str | Path, out_dir: str | Path, every: int = 1) -> list[str]:
    every = max(int(every), 1)
    reader = open_reader(path)
    n = len(reader.pages)
    stem = Path(path).stem
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    width = max(len(str(n)), 3)
    outputs = []
    for start in range(0, n, every):
        end = min(start + every, n)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        label = f"p{start + 1:0{width}d}" if end - start == 1 else f"p{start + 1:0{width}d}-{end:0{width}d}"
        dst = out_dir / f"{stem}_{label}.pdf"
        with open(dst, "wb") as f:
            writer.write(f)
        outputs.append(str(dst))
    return outputs


def extract_pages(path: str | Path, ranges: str, out_path: str | Path) -> int:
    reader = open_reader(path)
    pages = parse_ranges(ranges, len(reader.pages))
    writer = PdfWriter()
    for i in pages:
        writer.add_page(reader.pages[i])
    with open(out_path, "wb") as f:
        writer.write(f)
    return len(pages)
