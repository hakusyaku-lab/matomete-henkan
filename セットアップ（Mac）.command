#!/bin/bash
# まとめて変換 ― Mac 用セットアップ
# Finder でダブルクリックすると実行されます（初回は「右クリック →開く」）。
# 1) Python 3.10 以上を探す  2) アプリ専用の環境(.venv)を作って部品を入れる
# 3) 起動用の「まとめて変換.command」を作り、デスクトップにも置く  4) アプリを起動する
set -u
APP="$(cd "$(dirname "$0")" && pwd)"
cd "$APP" || exit 1
echo ""
echo " ==============================================="
echo "  まとめて変換 のセットアップ（Mac）"
echo "  初回は数分かかります。このまま待ってください。"
echo " ==============================================="
echo ""

fail() {
  echo ""
  echo " セットアップに失敗しました：$1"
  echo " 上に表示されたメッセージを確認してください。"
  echo ""
  read -r -p " Enter キーで閉じます..." _
  exit 1
}

# ---- 1. Python を探す（3.10 以上。新しい順に試す）----
echo " [1/4] Python を確認しています..."
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3 \
            /Library/Frameworks/Python.framework/Versions/3.1[0-3]/bin/python3 \
            /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  exe="$(command -v "$cand" 2>/dev/null || true)"
  [ -z "$exe" ] && [ -x "$cand" ] && exe="$cand"
  [ -z "$exe" ] && continue
  if "$exe" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$exe"; break
  fi
done
if [ -z "$PY" ]; then
  echo ""
  echo " Python 3.10 以上が見つかりませんでした。"
  echo " https://www.python.org/downloads/macos/ から「Python 3.12」の macOS 64-bit universal2 installer を"
  echo " インストールしてから、もう一度このファイルを開いてください。"
  read -r -p " Enter キーで閉じます..." _
  exit 1
fi
echo " [1/4] Python: $PY ($("$PY" --version 2>&1))"

# ---- 2. アプリ専用の環境と部品 ----
VPY="$APP/.venv/bin/python"
if [ ! -x "$VPY" ]; then
  echo " [2/4] アプリ専用の環境を作っています..."
  "$PY" -m venv "$APP/.venv" || fail "環境を作れませんでした"
fi
echo " [3/4] 必要な部品をインストールしています（数分かかります）..."
"$VPY" -m pip install --upgrade pip --disable-pip-version-check -q || fail "pip の更新"
"$VPY" -m pip install -r "$APP/requirements.txt" --disable-pip-version-check -q || fail "部品のインストール"
"$VPY" -c "import webview, PIL, pillow_heif, pypdf, pypdfium2, openpyxl" || fail "部品の確認"

# ---- 3. 起動用ファイル ----
echo " [4/4] 起動用のファイルを作っています..."
LAUNCHER="$APP/まとめて変換.command"
cat > "$LAUNCHER" <<LAUNCH
#!/bin/bash
# まとめて変換を起動する（セットアップ（Mac）.command が作成）
cd "$APP" && exec "$VPY" "$APP/app/main.py"
LAUNCH
chmod +x "$LAUNCHER"
if [ -d "$HOME/Desktop" ]; then
  ln -sf "$LAUNCHER" "$HOME/Desktop/まとめて変換.command" && echo "  デスクトップに「まとめて変換」を置きました"
fi

echo ""
echo " セットアップが終わりました。アプリを起動します。"
echo " 次からはデスクトップの「まとめて変換」をダブルクリックすると起動できます。"
echo ""
"$VPY" "$APP/app/main.py" &
sleep 3
