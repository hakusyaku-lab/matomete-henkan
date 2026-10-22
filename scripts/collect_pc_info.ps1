# このPCのスペックと開発環境を調べて「PC環境.md」に書き出す。
# セットアップ（Windows）.bat が毎回実行するので、常に最新の状態になる。
# 手動で更新する場合: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\collect_pc_info.ps1 -AppDir <このフォルダ>
param([Parameter(Mandatory=$true)][string]$AppDir)
$ErrorActionPreference = 'SilentlyContinue'

function Ver($cmd, $arg = '--version') {
    $c = Get-Command $cmd -ErrorAction SilentlyContinue
    if (-not $c) { return '未インストール' }
    $out = & $cmd $arg 2>&1 | Select-Object -First 1
    return "$out".Trim()
}

$os   = Get-CimInstance Win32_OperatingSystem
$cs   = Get-CimInstance Win32_ComputerSystem
$cpu  = Get-CimInstance Win32_Processor | Select-Object -First 1
$gpus = (Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }) -join ' / '
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$disp = (Get-CimInstance Win32_VideoController | Where-Object { $_.CurrentHorizontalResolution } |
         ForEach-Object { "$($_.CurrentHorizontalResolution)x$($_.CurrentVerticalResolution)" }) -join ' / '
$reg  = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$wv2  = (Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}').pv
if (-not $wv2) { $wv2 = (Get-ItemProperty 'HKCU:\Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}').pv }
if (-not $wv2) { $wv2 = '見つからない' }

$venvPy = Join-Path $AppDir '.venv\Scripts\python.exe'
$venvVer = if (Test-Path $venvPy) { (& $venvPy --version 2>&1) } else { '未作成（セットアップ前）' }
$pkgs = if (Test-Path $venvPy) {
    (& $venvPy -m pip list --format=freeze 2>$null | Where-Object { $_ -match '^(pywebview|pillow|pillow.heif|pypdf|pypdfium2|openpyxl|charset.normalizer|pytest|playwright|pyinstaller)==' }) -join ', '
} else { '-' }
$pyLauncher = (& py -0p 2>&1 | ForEach-Object { "$_".Trim() } | Where-Object { $_ }) -join ' / '
if (-not $pyLauncher) { $pyLauncher = '未インストール' }

$now = Get-Date -Format 'yyyy-MM-dd HH:mm'
$ramGB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
$freeGB = [math]::Round($disk.FreeSpace / 1GB, 1)
$sizeGB = [math]::Round($disk.Size / 1GB, 1)

$md = @"
# PC環境（自動作成）

> このファイルは scripts\collect_pc_info.ps1 が自動で作ります。手で書き換えないでください。
> 最終更新: $now ／ 更新するには「セットアップ（Windows）.bat」を実行します。
> AI へ: このアプリを修正・ビルド・動作確認するときは、この PC 環境を前提にしてください。

## ハードウェア・OS

| 項目 | 内容 |
|---|---|
| PC名 | $($cs.Name)（$($cs.Manufacturer) $($cs.Model)） |
| OS | $($os.Caption) $($reg.DisplayVersion)（ビルド $($os.BuildNumber).$($reg.UBR)、$($os.OSArchitecture)） |
| CPU | $($cpu.Name.Trim())（$($cpu.NumberOfCores)コア / $($cpu.NumberOfLogicalProcessors)スレッド） |
| メモリ | $ramGB GB |
| GPU | $gpus |
| 画面 | $disp |
| Cドライブ | 空き $freeGB GB / 全体 $sizeGB GB |
| 表示言語 | $((Get-Culture).Name) |

## このアプリに関係するソフト

| 項目 | 内容 |
|---|---|
| アプリの場所 | $AppDir |
| アプリ専用 Python（.venv） | $venvVer |
| 主な部品 | $pkgs |
| インストール済み Python（py -0p） | $pyLauncher |
| WebView2 ランタイム（画面表示に必要） | $wv2 |
| PowerShell | $($PSVersionTable.PSVersion) |
| Git | $(Ver git) |
| Node.js | $(Ver node) |
| winget | $(Ver winget) |
"@

$out = Join-Path $AppDir 'PC環境.md'
[System.IO.File]::WriteAllText($out, $md, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "  PC環境を書き出しました: $out"
