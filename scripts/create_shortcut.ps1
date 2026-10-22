# デスクトップとスタートメニューに「まとめて変換」のショートカットを作る
param([Parameter(Mandatory=$true)][string]$AppDir)

$pythonw = Join-Path $AppDir '.venv\Scripts\pythonw.exe'
$main    = Join-Path $AppDir 'app\main.py'
$icon    = Join-Path $AppDir 'icon.ico'
$shell   = New-Object -ComObject WScript.Shell

$places = @(
    [Environment]::GetFolderPath('Desktop'),
    (Join-Path ([Environment]::GetFolderPath('Programs')) '')
)
foreach ($dir in $places) {
    if (-not $dir) { continue }
    $lnk = Join-Path $dir 'まとめて変換.lnk'
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath       = $pythonw
    $s.Arguments        = '"' + $main + '"'
    $s.WorkingDirectory = $AppDir
    $s.IconLocation     = $icon
    $s.Description      = 'CSV・画像・PDF をまとめて変換'
    $s.Save()
    Write-Host "  作成しました: $lnk"
}
