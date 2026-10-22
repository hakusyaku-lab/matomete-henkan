"""ファイルの文字コード・改行コード・構成の検査。

Windows 用の .bat は「Shift_JIS(cp932) ＋ CRLF」、.ps1 は「BOM付き UTF-8」でないと、
日本語が文字化けして動かなくなります。エディタや AI が保存し直したときに壊れやすいので見張ります。
"""
import sys
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
        "scripts/create_shortcut.ps1", "scripts/find_python.ps1", "scripts/make_samples.py", "samples/読んでください.txt", "scripts/collect_pc_info.ps1", "使い方（Windows）.txt", "セットアップ（Mac）.command",
    ]:
        assert (ROOT / rel).exists(), f"{rel} がありません"


def test_version_in_changelog():
    ns = {}
    exec((ROOT / "app" / "version.py").read_text(encoding="utf-8"), ns)
    v = ns["__version__"]
    assert f"[{v}]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), f"CHANGELOG.md に [{v}] の記録がありません"


def test_bat_references_existing_files():
    """セットアップの .bat が呼び出しているスクリプト・ファイルが実在する。"""
    import re

    for p in ROOT.glob("*.bat"):
        text = p.read_bytes().decode("cp932")
        for rel in re.findall(r'%APP%\\([^"%]+?\.(?:ps1|py|txt))"', text):
            assert (ROOT / rel.replace("\\", "/")).exists(), f"{p.name} が参照している {rel} がありません"
        assert "winget" not in text, "winget はPCに無いことがあるため使わない（scripts/find_python.ps1 を使う）"


def test_ps1_syntax():
    """PowerShell スクリプトに文法エラーが無い（pwsh / powershell がある環境だけ）。"""
    import os
    import shutil
    import subprocess

    import pytest

    exe = shutil.which("pwsh") or shutil.which("powershell") or ("/opt/pwsh/pwsh" if os.path.exists("/opt/pwsh/pwsh") else None)
    if not exe:
        pytest.skip("PowerShell が無い環境")
    for p in ROOT.rglob("*.ps1"):
        cmd = ("$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile("
               f"'{p}', [ref]$null, [ref]$e); if ($e) {{ $e | % {{ $_.Message }}; exit 1 }}")
        r = subprocess.run([exe, "-NoProfile", "-Command", cmd], capture_output=True, text=True)
        assert r.returncode == 0, f"{p.name} に文法エラー: {r.stdout}{r.stderr}"


def test_mac_command():
    """Mac 用セットアップは LF 改行・bash の文法エラーなし。PC 固有のパスを含まない。"""
    import shutil
    import subprocess

    for p in ROOT.glob("*.command"):
        raw = p.read_bytes()
        assert b"\r\n" not in raw, f"{p.name}: 改行は LF にしてください"
        # Windows の bash は WSL（未設定だと動かない）の場合があるので、Mac・Linux でだけ文法を確かめる
        if sys.platform != "win32" and shutil.which("bash"):
            assert subprocess.run(["bash", "-n", str(p)]).returncode == 0, f"{p.name} に文法エラー"


def test_no_machine_specific_paths():
    """公開するファイルに、特定の PC のユーザー名・パスを書いていない。"""
    import re

    bad = re.compile(r"C:\\Users\\(?!<)[A-Za-z0-9_.-]+|/Users/[a-z0-9_.-]+/|/home/[a-z0-9_.-]+/", re.I)
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts or ".venv" in p.parts or "samples" in p.parts or p.name == "PC環境.md":
            continue
        if p.suffix.lower() not in {".md", ".py", ".js", ".html", ".css", ".ps1", ".bat", ".txt", ".yml", ".command"}:
            continue
        raw = p.read_bytes()
        text = raw.decode("cp932" if p.suffix == ".bat" else "utf-8", errors="ignore")
        m = bad.search(text)
        assert not m, f"{p.relative_to(ROOT)} に PC 固有のパスがあります: {m.group(0)}"
