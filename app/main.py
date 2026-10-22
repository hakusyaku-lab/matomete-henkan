"""まとめて変換 - デスクトップアプリの入口。

画面は ui/ フォルダの HTML、変換処理は converters/ の Python。
pywebview が両者をつなぎ、Windows では Edge(WebView2)、Mac では Safari(WebKit) の部品で画面を表示します。
"""
from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

import webview

from converters import csv_tools, image_tools, mapping, normalize, pdf_tools, text_io
from version import __version__

APP_NAME = "まとめて変換"
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
UI_INDEX = BASE_DIR / "ui" / "index.html"

# pywebview 5 と 6 のどちらでも動くように、ダイアログ種別を取り出す
try:
    OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG = webview.FileDialog.OPEN, webview.FileDialog.FOLDER, webview.FileDialog.SAVE
except AttributeError:  # pywebview 5
    OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG = webview.OPEN_DIALOG, webview.FOLDER_DIALOG, webview.SAVE_DIALOG

FILE_TYPES = {
    "csv": ("CSV テキスト (*.csv;*.txt;*.tsv)", "すべてのファイル (*.*)"),
    "image": ("画像 (*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.gif;*.tif;*.tiff;*.heic;*.heif)", "すべてのファイル (*.*)"),
    "pdf": ("PDF (*.pdf)",),
}


def safe(fn):
    """例外を画面に表示できる形 {ok: False, error: ...} に変換する。"""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            if isinstance(result, dict):
                result.setdefault("ok", True)
                return result
            return {"ok": True, "data": result}
        except (ValueError, FileNotFoundError) as e:
            return {"ok": False, "error": str(e)}
        except PermissionError:
            return {"ok": False, "error": "保存できませんでした。ファイルが他のアプリで開かれていないか確認してください。"}
        except Exception as e:  # 想定外のエラー
            traceback.print_exc()
            return {"ok": False, "error": f"エラーが発生しました：{type(e).__name__}: {e}"}

    return wrapper


def _first(result):
    """ダイアログの戻り値（文字列・タプル・None）を1つのパスにそろえる。"""
    if not result:
        return None
    if isinstance(result, (list, tuple)):
        return result[0] if result else None
    return result


class Api:
    """画面の JavaScript から window.pywebview.api.xxx() で呼び出す処理。"""

    def __init__(self):
        self._window = None
        self._tables: dict[str, dict] = {}

    # ---------- 共通 ----------
    def _progress(self, done: int, total: int, label: str = "") -> None:
        if self._window:
            self._window.evaluate_js(f"window.__progress && window.__progress({done},{total},{json.dumps(label)})")

    def _save_dialog(self, filename: str, file_type: str | None = None):
        kwargs = {"save_filename": filename}
        if file_type:
            kwargs["file_types"] = (file_type,)
        return _first(self._window.create_file_dialog(SAVE_DIALOG, **kwargs))

    @safe
    def app_info(self):
        return {"name": APP_NAME, "version": __version__, "platform": sys.platform,
                "heif": image_tools.HEIF_SUPPORTED, "op_labels": normalize.OP_LABELS}

    @safe
    def pick_files(self, kind: str):
        paths = self._window.create_file_dialog(OPEN_DIALOG, allow_multiple=True, file_types=FILE_TYPES.get(kind, ()))
        return {"paths": list(paths or [])}

    @safe
    def pick_file(self, kind: str):
        paths = self._window.create_file_dialog(OPEN_DIALOG, allow_multiple=False, file_types=FILE_TYPES.get(kind, ()))
        return {"path": _first(paths)}

    @safe
    def reveal(self, path: str):
        """保存先をエクスプローラー／Finder で開く。"""
        p = Path(path)
        if sys.platform == "win32":
            if p.is_file():
                subprocess.run(["explorer", "/select,", str(p)])
            else:
                os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(p)] if p.is_file() else ["open", str(p)])
        else:
            subprocess.run(["xdg-open", str(p if p.is_dir() else p.parent)])
        return {}

    # ---------- ① CSV 変換・結合 ----------
    def _table(self, path: str) -> dict:
        if path not in self._tables:
            self._tables[path] = text_io.read_table(path)
        return self._tables[path]

    @safe
    def csv_load(self, paths: list[str]):
        files = []
        for p in paths:
            try:
                self._tables.pop(p, None)
                t = self._table(p)
                files.append({k: t[k] for k in ("path", "name", "encoding", "encoding_label", "row_count", "col_count")})
            except Exception as e:
                files.append({"path": p, "name": Path(p).name, "error": f"読み込めませんでした（{type(e).__name__}）"})
        return {"files": files}

    def _build_csv(self, paths: list[str], options: dict) -> list[list[str]]:
        tables = [self._table(p) for p in paths]
        if len(tables) == 1 and not options.get("add_source"):
            rows = tables[0]["rows"]
        else:
            rows = csv_tools.merge_tables(tables, add_source=bool(options.get("add_source")))
        return normalize.normalize_rows(rows, options)

    @safe
    def csv_check(self, paths: list[str], options: dict):
        """Shift_JIS で表せない文字の一覧（出力前のチェック）。"""
        if not paths:
            return {"unencodable": []}
        rows = self._build_csv(paths, options)
        return {"unencodable": text_io.find_unencodable(rows, "cp932", limit=50)}

    @safe
    def csv_export(self, paths: list[str], options: dict, fmt: str):
        if not paths:
            raise ValueError("ファイルを追加してください")
        ext, _label = csv_tools.FORMATS[fmt]
        stem = Path(paths[0]).stem + ("_結合" if len(paths) > 1 else "_変換")
        dst = self._save_dialog(stem + ext, f"{ext.lstrip('.').upper()} (*{ext})")
        if not dst:
            return {"cancelled": True}
        if not dst.lower().endswith(ext):
            dst += ext
        rows = self._build_csv(paths, options)
        replaced = len(text_io.find_unencodable(rows, "cp932", limit=100000)) if fmt == "csv_sjis" else 0
        csv_tools.export_rows(dst, rows, fmt, protect_zero=bool(options.get("protect_zero", True)))
        return {"path": dst, "rows": max(len(rows) - 1, 0), "replaced": replaced}

    # ---------- ② 画像一括変換 ----------
    @safe
    def image_inspect(self, paths: list[str]):
        out = []
        targets = [p for p in paths if Path(p).suffix.lower() in image_tools.IMAGE_EXTS]
        for i, p in enumerate(targets):
            self._progress(i, len(targets), "読み込み中")
            out.append(image_tools.inspect_image(p))
        self._progress(len(targets), len(targets))
        return {"images": out, "skipped": len(paths) - len(targets)}

    @safe
    def image_convert(self, paths: list[str], opts: dict):
        if not paths:
            raise ValueError("画像を追加してください")
        out_dir = _first(self._window.create_file_dialog(FOLDER_DIALOG))
        if not out_dir:
            return {"cancelled": True}
        results, errors = [], []
        for i, p in enumerate(paths):
            self._progress(i, len(paths), Path(p).name)
            try:
                results.append(image_tools.convert_image(p, out_dir, opts, index=i + 1))
            except Exception as e:
                errors.append({"name": Path(p).name, "error": f"{type(e).__name__}: {e}"})
        self._progress(len(paths), len(paths))
        return {"folder": out_dir, "count": len(results), "errors": errors}

    # ---------- ③ CSV 形式変換 ----------
    @safe
    def map_load_source(self, path: str):
        self._tables.pop(path, None)
        t = self._table(path)
        header = csv_tools.uniquify(t["rows"][0]) if t["rows"] else []
        return {"path": path, "name": t["name"], "encoding_label": t["encoding_label"],
                "row_count": t["row_count"], "header": header}

    @safe
    def map_load_target(self, path: str):
        t = text_io.read_table(path)
        if not t["rows"]:
            raise ValueError("見本ファイルに見出し行がありません")
        return {"header": csv_tools.uniquify(t["rows"][0])}

    @safe
    def map_preview(self, src_path: str, mapping_rows: list[dict], limit: int = 3):
        t = self._table(src_path)
        rows = mapping.apply_mapping(t["rows"][: limit + 1], mapping_rows)
        return {"rows": rows}

    @safe
    def map_export(self, src_path: str, mapping_rows: list[dict], encoding: str):
        if not mapping_rows:
            raise ValueError("変換先の列を追加してください")
        if encoding not in text_io.OUTPUT_ENCODINGS:
            raise ValueError("出力の文字コードを選んでください")
        t = self._table(src_path)
        dst = self._save_dialog(Path(src_path).stem + "_変換.csv", "CSV (*.csv)")
        if not dst:
            return {"cancelled": True}
        if not dst.lower().endswith(".csv"):
            dst += ".csv"
        rows = mapping.apply_mapping(t["rows"], mapping_rows)
        replaced = len(text_io.find_unencodable(rows, "cp932", limit=100000)) if encoding == "cp932" else 0
        text_io.write_csv(dst, rows, encoding)
        return {"path": dst, "rows": max(len(rows) - 1, 0), "replaced": replaced}

    @safe
    def tpl_list(self):
        return {"names": mapping.list_templates()}

    @safe
    def tpl_save(self, name: str, data: dict):
        return {"name": mapping.save_template(name, data), "names": mapping.list_templates()}

    @safe
    def tpl_load(self, name: str):
        return {"data": mapping.load_template(name)}

    @safe
    def tpl_delete(self, name: str):
        mapping.delete_template(name)
        return {"names": mapping.list_templates()}

    # ---------- ④ PDF ----------
    @safe
    def pdf_inspect(self, paths: list[str]):
        targets = [p for p in paths if Path(p).suffix.lower() == ".pdf"]
        out = []
        for i, p in enumerate(targets):
            self._progress(i, len(targets), "読み込み中")
            out.append(pdf_tools.inspect_pdf(p))
        self._progress(len(targets), len(targets))
        return {"files": out, "skipped": len(paths) - len(targets)}

    @safe
    def pdf_merge(self, paths: list[str]):
        if len(paths) < 2:
            raise ValueError("結合するPDFを2つ以上追加してください")
        dst = self._save_dialog(Path(paths[0]).stem + "_結合.pdf", "PDF (*.pdf)")
        if not dst:
            return {"cancelled": True}
        if not dst.lower().endswith(".pdf"):
            dst += ".pdf"
        pages = pdf_tools.merge_pdfs(paths, dst)
        return {"path": dst, "pages": pages}

    @safe
    def pdf_split(self, path: str, every: int):
        out_dir = _first(self._window.create_file_dialog(FOLDER_DIALOG))
        if not out_dir:
            return {"cancelled": True}
        outs = pdf_tools.split_pdf(path, out_dir, every)
        return {"folder": out_dir, "count": len(outs)}

    @safe
    def pdf_extract(self, path: str, ranges: str):
        total = len(pdf_tools.open_reader(path).pages)
        pdf_tools.parse_ranges(ranges, total)  # 先に入力を確認
        dst = self._save_dialog(Path(path).stem + "_抜き出し.pdf", "PDF (*.pdf)")
        if not dst:
            return {"cancelled": True}
        if not dst.lower().endswith(".pdf"):
            dst += ".pdf"
        pages = pdf_tools.extract_pages(path, ranges, dst)
        return {"path": dst, "pages": pages}


def bind_drop(window) -> None:
    """ファイルのドラッグ＆ドロップで、本当のファイルパスを画面に渡す。"""
    try:
        from webview.dom import DOMEventHandler
    except ImportError:
        return

    def on_drop(e):
        files = (e.get("dataTransfer") or {}).get("files") or []
        paths = [f.get("pywebviewFullPath") for f in files if f.get("pywebviewFullPath")]
        if paths:
            window.evaluate_js(f"window.onFilesDropped && window.onFilesDropped({json.dumps(paths)})")

    try:
        window.dom.document.events.dragover += DOMEventHandler(lambda e: None, True, True)
        window.dom.document.events.drop += DOMEventHandler(on_drop, True, True)
    except Exception:
        traceback.print_exc()


def main() -> None:
    api = Api()
    window = webview.create_window(
        APP_NAME, url=str(UI_INDEX), js_api=api,
        width=1280, height=840, min_size=(900, 640), background_color="#EEF1F5",
    )
    api._window = window
    webview.start(bind_drop, window, debug=bool(os.environ.get("MATOMETE_DEBUG")))


if __name__ == "__main__":
    main()
