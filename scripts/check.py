"""修正したら必ず実行する全体チェック。

    python scripts/check.py

すべて合格なら「合格」と表示して終了コード 0、1つでも失敗したら「不合格」と表示して 1 を返します。
GitHub Actions 上では、失敗した検査の名前と理由を「注記（annotation）」としても出すので、
ログを開けない環境からでも原因を確認できます。
"""
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Windows の英語環境などで日本語を表示してもエラーにならないようにする
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _annotate_failures(junit: Path) -> None:
    """GitHub Actions に失敗内容を注記として出す。"""
    try:
        tree = ET.parse(junit)
    except Exception:
        return
    for case in tree.iter("testcase"):
        for kind in ("failure", "error"):
            el = case.find(kind)
            if el is None:
                continue
            name = f"{case.get('classname')}.{case.get('name')}"
            msg = (el.get("message") or el.text or "").strip().replace("\r", "")
            msg = msg.replace("%", "%25").replace("\n", "%0A")[:1500]
            print(f"::error title={name}::{msg}")


def main() -> int:
    print("=== まとめて変換 全体チェック ===")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")  # 表示だけ UTF-8（処理は実際の PC と同じ条件）
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "result.xml"
        code = subprocess.call(
            [sys.executable, "-m", "pytest", "-q", "-rs", f"--junitxml={junit}", str(ROOT / "tests")],
            cwd=ROOT, env=env,
        )
        if code != 0 and os.environ.get("GITHUB_ACTIONS"):
            _annotate_failures(junit)
    print()
    if code == 0:
        print("合格：すべてのチェックに通りました。")
        print("（「skipped」がある場合は、その環境では実行できなかった検査です。上の理由を確認してください）")
    else:
        print("不合格：上に表示された失敗を直してから、もう一度実行してください。")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
