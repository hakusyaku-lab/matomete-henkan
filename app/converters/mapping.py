"""③ CSV 形式変換：列の対応付けと、テンプレートの保存。"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from .csv_tools import uniquify
from .normalize import apply_ops

APP_DIR_NAME = "MatometeHenkan"


def config_dir() -> Path:
    """設定の保存場所（OSごとの標準の場所）。環境変数 MATOMETE_CONFIG_DIR で変更可。"""
    override = os.environ.get("MATOMETE_CONFIG_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_DIR_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def templates_dir() -> Path:
    d = config_dir() / "templates"
    d.mkdir(parents=True, exist_ok=True)
    return d


_BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _template_path(name: str) -> Path:
    clean = _BAD.sub("_", name).strip().strip(".")
    if not clean:
        raise ValueError("テンプレート名を入力してください")
    return templates_dir() / f"{clean[:80]}.json"


def list_templates() -> list[str]:
    return sorted(p.stem for p in templates_dir().glob("*.json"))


def save_template(name: str, data: dict) -> str:
    p = _template_path(name)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p.stem


def load_template(name: str) -> dict:
    p = _template_path(name)
    if not p.exists():
        raise FileNotFoundError(f"テンプレート「{name}」が見つかりません")
    return json.loads(p.read_text(encoding="utf-8"))


def delete_template(name: str) -> None:
    p = _template_path(name)
    if p.exists():
        p.unlink()


def apply_mapping(rows: list[list[str]], mapping: list[dict]) -> list[list[str]]:
    """元の表（1行目が見出し）を、対応表に従って新しい表に作り替える。

    mapping の各要素:
      target: 変換先の列名
      source: 元の列名（"" なら空欄、"__fixed__" なら固定値）
      fixed:  固定値（source が "__fixed__" のとき）
      ops:    加工のリスト（normalize.OPS のキー）
    """
    if not rows:
        return [[m.get("target", "") for m in mapping]]
    header = uniquify(rows[0])
    pos = {h: i for i, h in enumerate(header)}
    out = [[m.get("target", "") for m in mapping]]
    for row in rows[1:]:
        new_row = []
        for m in mapping:
            src = m.get("source", "")
            if src == "__fixed__":
                value = m.get("fixed", "")
            elif src in pos and pos[src] < len(row):
                value = row[pos[src]]
            else:
                value = ""
            new_row.append(apply_ops(value, m.get("ops", [])))
        out.append(new_row)
    return out


def auto_mapping(source_header: list[str], target_header: list[str]) -> list[dict]:
    """変換先の列名と同じ名前の元の列があれば、自動で対応させる。"""
    src = set(uniquify(source_header))
    return [{"target": t, "source": t if t in src else "", "fixed": "", "ops": []} for t in target_header]
