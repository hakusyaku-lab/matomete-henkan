"""ファイルの文字コード・改行コード・構成の検査。

Windows 用の .bat は「Shift_JIS(cp932) ＋ CRLF」、.ps1 は「BOM付き UTF-8」でないと、
日本語が文字化けして動かなくなります。エディタや AI が保存し直したときに壊れやすいので見張ります。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bat_is_cp932_crlf():
    bats = list(ROOT.glob("*.bat"))
    assert bats, ".bat が見つかりません"
    for p in bats:
        raw = p.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{p.name}: BOM 付き UTF-8 になっています。cp932 で保存してください"
        try:
            raw.decode("cp932")
        except UnicodeDecodeError:
            raise AssertionError(f"{p.name}: Shift_JIS(cp932) で保存されていません")
        assert b"\n" not in raw.replace(b"\r\n", b""), f"{p.name}: 改行が CRLF ではありません"


def test_ps1_is_utf8_bom():
    for p in ROOT.rglob("*.ps1"):
        raw = p.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf"), f"{p.name}: BOM 付き UTF-8 で保存してください（PowerShell 5 の文字化け対策）"


def test_text_sources_are_utf8():
    for pattern in ("app/**/*.py", "app/ui/*", "tests/*.py", "*.md", "docs/*.md", "scripts/*.py"):
        for p in ROOT.glob(pattern):
            if p.is_file():
                p.read_bytes().decode("utf-8")


def test_required_files_exist():
    for rel in [
        "AGENTS.md", "CLAUDE.md", "CHANGELOG.md", "README.md", "docs/ARCHITECTURE.md", "docs/EXTENDING.md",
        "app/main.py", "app/version.py", "app/ui/index.html", "app/ui/app.js", "app/ui/style.css",
        "requirements.txt", "requirements-dev.txt", "icon.ico", "build.py", "scripts/check.py",
        "scripts/create_shortcut.ps1", "使い方（Windows）.txt",
    ]:
        assert (ROOT / rel).exists(), f"{rel} がありません"


def test_version_in_changelog():
    ns = {}
    exec((ROOT / "app" / "version.py").read_text(encoding="utf-8"), ns)
    v = ns["__version__"]
    assert f"[{v}]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), f"CHANGELOG.md に [{v}] の記録がありません"
