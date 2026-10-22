@echo off
setlocal
title まとめて変換 セットアップ
set "APP=%~dp0"
set "APP=%APP:~0,-1%"
cd /d "%APP%"
echo.
echo  ===============================================
echo   まとめて変換 のセットアップ
echo   初回は数分かかります。このまま待ってください。
echo  ===============================================
echo.

rem ---- Python を探す（無ければ公式版をダウンロードしてインストール）----
echo  [1/4] Python を確認しています...
set "PYEXE="
set "PYFILE=%TEMP%\matomete_python_path.txt"
if exist "%PYFILE%" del "%PYFILE%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%APP%\scripts\find_python.ps1" -OutFile "%PYFILE%"
if exist "%PYFILE%" set /p PYEXE=<"%PYFILE%"
if not defined PYEXE goto :nopython
echo  [1/4] Python: %PYEXE%

rem ---- アプリ専用の環境を作る ----
set "VPY=%APP%\.venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo  [2/4] アプリ専用の環境を作っています...
  "%PYEXE%" -m venv "%APP%\.venv"
)
if not exist "%VPY%" goto :fail
echo  [2/4] 環境 OK

rem ---- 必要な部品を入れる ----
echo  [3/4] 必要な部品をインストールしています（数分かかります）...
"%VPY%" -m pip install --upgrade pip --disable-pip-version-check -q
"%VPY%" -m pip install -r "%APP%\requirements.txt" --disable-pip-version-check -q
if errorlevel 1 goto :fail
"%VPY%" -c "import webview, PIL, pillow_heif, pypdf, pypdfium2, openpyxl" 2>nul
if errorlevel 1 goto :fail
echo  [3/4] 部品 OK

rem ---- 変更履歴（git）を復元する：初回だけ。git が無ければ飛ばす ----
if not exist "%APP%\.git" if exist "%APP%\変更履歴.bundle" (
  where git >nul 2>nul && (
    echo  変更履歴（git）を準備しています...
    git -C "%APP%" init -q -b main
    git -C "%APP%" fetch -q "%APP%\変更履歴.bundle" main
    git -C "%APP%" reset -q --mixed FETCH_HEAD
    git -C "%APP%" checkout -q -- .github
  )
)

rem ---- PC環境を記録する（AI が修正するときの参照用）----
powershell -NoProfile -ExecutionPolicy Bypass -File "%APP%\scripts\collect_pc_info.ps1" -AppDir "%APP%"

rem ---- ショートカットを作る ----
echo  [4/4] デスクトップとスタートメニューにアイコンを作っています...
powershell -NoProfile -ExecutionPolicy Bypass -File "%APP%\scripts\create_shortcut.ps1" -AppDir "%APP%"

echo.
echo  セットアップが終わりました。アプリを起動します。
echo  次からはデスクトップの「まとめて変換」アイコンで起動できます。
echo.
start "" "%APP%\.venv\Scripts\pythonw.exe" "%APP%\app\main.py"
timeout /t 5 >nul
exit /b 0

:nopython
echo.
echo  Python を自動でインストールできませんでした（上のメッセージを確認してください）。
echo  インターネットにつながっているか確認して、もう一度このファイルをダブルクリックしてください。
echo  それでもだめな場合は https://www.python.org/downloads/windows/ から
echo  「Python 3.12」の「Windows installer (64-bit)」を入れてから、もう一度実行してください。
echo.
pause
exit /b 1

:fail
echo.
echo  セットアップに失敗しました。上に表示されたメッセージを確認してください。
echo  （インターネットにつながっているか確認し、もう一度ダブルクリックすると再開します）
echo.
pause
exit /b 1
