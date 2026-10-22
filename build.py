"""配布用アプリを作るスクリプト（Windows では .exe、Mac では .app）。

使い方:  python build.py
できあがり: dist/MatometeHenkan/MatometeHenkan.exe（Windows）
            dist/MatometeHenkan.app（Mac）
"""
import sys

import PyInstaller.__main__

NAME = "MatometeHenkan"

args = [
    "app/main.py",
    "--name", NAME,
    "--windowed",          # 黒いコンソール画面を出さない
    "--noconfirm",
    "--clean",
    "--add-data", "app/ui:ui",
    "--paths", "app",
    "--collect-all", "pillow_heif",
    "--collect-all", "pypdfium2",
    "--collect-all", "pypdfium2_raw",
    "--collect-submodules", "webview",
]

if sys.platform == "darwin":
    args += ["--osx-bundle-identifier", "io.github.matomete-henkan"]

PyInstaller.__main__.run(args)
