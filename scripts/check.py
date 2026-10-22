"""修正したら必ず実行する全体チェック。

    python scripts/check.py

すべて合格なら「合格」と表示して終了コード 0、1つでも失敗したら「不合格」と表示して 1 を返します。
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("=== まとめて変換 全体チェック ===")
    code = subprocess.call([sys.executable, "-m", "pytest", "-q", "-rs", str(ROOT / "tests")], cwd=ROOT)
    print()
    if code == 0:
        print("合格：すべてのチェックに通りました。")
        print("（「skipped」がある場合は、その環境では実行できなかった検査です。上の理由を確認してください）")
    else:
        print("不合格：上に表示された失敗を直してから、もう一度実行してください。")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
