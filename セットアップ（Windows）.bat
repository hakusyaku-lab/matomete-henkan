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

rem ---- Python を探す（3.12 を優先）----
set "PYEXE="
for %%V in (3.12 3.13 3.11 3.10) do (
  if not defined PYEXE (
    for /f "delims=" %%P in ('py -%%V -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%P"
  )
)
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if not defined PYEXE (
  echo  [1/4] Python が見つからないので、インストールします...
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
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
echo  Python を自動でインストールできませんでした。
echo  https://www.python.org/downloads/ から Python 3.12 をインストールし、
echo  もう一度このファイルをダブルクリックしてください。
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
