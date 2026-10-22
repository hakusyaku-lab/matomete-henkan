"""② 画像一括変換：リサイズ・正方形化・形式変換・位置情報の削除。"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image, ImageOps

try:  # iPhone の HEIC を読めるようにする
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIF_SUPPORTED = True
except Exception:  # pragma: no cover - 環境によっては未インストール
    HEIF_SUPPORTED = False

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".heif"}
OUT_EXT = {"jpeg": ".jpg", "png": ".png", "webp": ".webp"}
GPS_IFD = 0x8825
WHITE = (255, 255, 255)


def has_transparency(img: Image.Image) -> bool:
    """実際に透明な部分があるか（アルファチャンネルがあっても全部不透明なら False）。"""
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        alpha = img.convert("RGBA").getchannel("A")
        return alpha.getextrema()[0] < 255
    return False


def _thumb_data_url(img: Image.Image, size: int = 160) -> str:
    t = img.copy()
    t.thumbnail((size, size))
    if t.mode not in ("RGB", "L"):
        bg = Image.new("RGB", t.size, WHITE)
        bg.paste(t.convert("RGBA"), mask=t.convert("RGBA").getchannel("A"))
        t = bg
    buf = io.BytesIO()
    t.convert("RGB").save(buf, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def inspect_image(path: str | Path) -> dict:
    p = Path(path)
    info = {"path": str(p), "name": p.name}
    try:
        with Image.open(p) as im:
            info["format"] = (im.format or p.suffix.lstrip(".")).upper()
            info["animated"] = bool(getattr(im, "is_animated", False))
            im = ImageOps.exif_transpose(im)
            info["width"], info["height"] = im.size
            info["has_alpha"] = has_transparency(im)
            info["thumb"] = _thumb_data_url(im)
    except Exception as e:  # 壊れたファイル・未対応形式
        info["error"] = f"読み込めませんでした（{type(e).__name__}）"
    return info


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    i = 1
    while True:
        cand = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not cand.exists():
            return cand
        i += 1


def _flatten(img: Image.Image) -> Image.Image:
    """透明部分を白で塗りつぶして RGB にする。"""
    rgba = img.convert("RGBA")
    bg = Image.new("RGB", rgba.size, WHITE)
    bg.paste(rgba, mask=rgba.getchannel("A"))
    return bg


def convert_image(src: str | Path, out_dir: str | Path, opts: dict, index: int = 1) -> dict:
    """1枚を変換して保存する。

    opts:
      fmt: "jpeg" | "png" | "webp"
      max_side: 長辺の最大px（0 なら縮小しない。拡大はしない）
      square: True なら白い余白を足して正方形にする
      quality: 1〜100（JPEG／WebP）
      lossless: True なら WebP を無劣化で保存
      strip_gps: True なら位置情報（GPS）を削除
      sequential: True なら「prefix_0001」の連番名にする
      prefix: 連番名の先頭
    """
    src = Path(src)
    fmt = opts.get("fmt", "jpeg")
    if fmt not in OUT_EXT:
        raise ValueError(f"未対応の出力形式です: {fmt}")
    quality = int(opts.get("quality", 85))
    max_side = int(opts.get("max_side", 0) or 0)
    notes = []

    with Image.open(src) as opened:
        if getattr(opened, "is_animated", False):
            notes.append("アニメーションは1コマ目だけになりました")
        img = ImageOps.exif_transpose(opened)  # スマホ写真の向きを補正
        exif = img.getexif()
        if 0x0112 in exif:
            exif[0x0112] = 1  # 向きは補正済み
        if opts.get("strip_gps", True) and GPS_IFD in exif:
            del exif[GPS_IFD]

        if img.mode == "CMYK":
            img = img.convert("RGB")
        elif img.mode in ("I;16", "I", "F"):
            img = img.convert("RGB")

        if max_side and max(img.size) > max_side:
            img = img.copy()
            img.thumbnail((max_side, max_side), Image.LANCZOS)

        if opts.get("square"):
            side = max(img.size)
            if img.size != (side, side):
                flat = _flatten(img) if img.mode != "RGB" else img
                canvas = Image.new("RGB", (side, side), WHITE)
                canvas.paste(flat, ((side - img.width) // 2, (side - img.height) // 2))
                img = canvas

        if fmt == "jpeg":
            if has_transparency(img):
                notes.append("透明部分を白にしました")
            if img.mode != "RGB":
                img = _flatten(img) if img.mode in ("RGBA", "LA", "PA", "P") else img.convert("RGB")
        elif img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            img = img.convert("RGBA")
        if fmt == "webp" and img.mode in ("P", "LA", "L"):
            img = img.convert("RGBA" if has_transparency(img) else "RGB")

        if opts.get("sequential"):
            prefix = (opts.get("prefix") or "image").strip() or "image"
            stem = f"{prefix}_{index:04d}"
        else:
            stem = src.stem
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = _unique_path(out_dir / f"{stem}{OUT_EXT[fmt]}")

        save_kwargs: dict = {}
        exif_bytes = exif.tobytes() if len(exif) else None
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
        if fmt == "jpeg":
            save_kwargs.update(quality=quality, optimize=True)
            if "icc_profile" in img.info:
                save_kwargs["icc_profile"] = img.info["icc_profile"]
            img.save(dst, "JPEG", **save_kwargs)
        elif fmt == "png":
            img.save(dst, "PNG", **save_kwargs)
        else:
            if opts.get("lossless"):
                save_kwargs.update(lossless=True, quality=100, method=6)
            else:
                save_kwargs.update(quality=quality, method=4)
            img.save(dst, "WEBP", **save_kwargs)

    return {"src": str(src), "output": str(dst), "name": dst.name, "notes": notes}
