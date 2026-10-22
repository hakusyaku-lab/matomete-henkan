# このアプリで使う Python（3.10〜3.13）を探し、無ければ python.org の公式版 3.12 をこのユーザー用にインストールする。
# 見つかった python.exe のパスを -OutFile に書き出す（見つからなければファイルを作らない）。
# winget が無い PC でも動くように、インストーラーを直接ダウンロードする。
param([Parameter(Mandatory=$true)][string]$OutFile)
$ErrorActionPreference = 'Continue'

$PreferOrder  = @('3.12', '3.13', '3.11', '3.10')   # 画面部品（pywebview / pythonnet）が対応している版
$InstallVer   = '3.12.10'                           # 自動インストールする版（Windows 用インストーラーがある最後の 3.12）
$InstallerUrl = "https://www.python.org/ftp/python/$InstallVer/python-$InstallVer-amd64.exe"
$InstalledExe = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'

function Get-PyVersion([string]$exe) {
    if (-not $exe -or -not (Test-Path $exe)) { return $null }
    if ($exe -like '*\WindowsApps\*') { return $null }   # Microsoft Store の案内用ダミーは除外
    try {
        $v = & $exe -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0) { return "$v".Trim() }
    } catch {}
    return $null
}

function Find-Python {
    $cands = New-Object System.Collections.Generic.List[string]
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -0p 2>$null | ForEach-Object { if ("$_" -match '([A-Za-z]:\\.+?python\.exe)') { $cands.Add($Matches[1]) } }
    }
    foreach ($pat in @("$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
                       "$env:LOCALAPPDATA\Python\pythoncore-3.*\python.exe",   # Python インストールマネージャー（py install）で入れた版
                       "$env:ProgramFiles\Python3*\python.exe",
                       "${env:ProgramFiles(x86)}\Python3*\python.exe",
                       "C:\Python3*\python.exe")) {
        Get-ChildItem $pat -ErrorAction SilentlyContinue | ForEach-Object { $cands.Add($_.FullName) }
    }
    Get-Command python.exe -All -ErrorAction SilentlyContinue | ForEach-Object { $cands.Add($_.Source) }

    $found = @{}
    foreach ($c in ($cands | Select-Object -Unique)) {
        $v = Get-PyVersion $c
        if ($v -and -not $found.ContainsKey($v)) { $found[$v] = $c }
    }
    if ($found.Count) { Write-Host ("  見つかった Python: " + (($found.Keys | Sort-Object) -join ', ')) }
    foreach ($v in $PreferOrder) { if ($found.ContainsKey($v)) { return $found[$v] } }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host "  使える Python（3.10〜3.13）が無いので、公式の Python $InstallVer をダウンロードします..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $tmp = Join-Path $env:TEMP "python-$InstallVer-amd64.exe"
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $InstallerUrl -OutFile $tmp -UseBasicParsing
    } catch {
        Write-Host "  ダウンロードに失敗しました: $($_.Exception.Message)"
        exit 1
    }
    $sig = Get-AuthenticodeSignature $tmp
    if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
        Write-Host "  ダウンロードしたファイルの署名を確認できなかったため、中止しました（$($sig.Status)）。"
        Remove-Item $tmp -ErrorAction SilentlyContinue
        exit 1
    }
    Write-Host "  インストールしています（1〜3分）..."
    $p = Start-Process -FilePath $tmp -Wait -PassThru -ArgumentList @(
        '/quiet', 'InstallAllUsers=0', 'PrependPath=0', 'Include_launcher=0',
        'Include_test=0', 'Include_doc=0', 'Shortcuts=0', 'AssociateFiles=0')
    Remove-Item $tmp -ErrorAction SilentlyContinue
    if ($p.ExitCode -ne 0) { Write-Host "  インストーラーがエラーで終了しました（コード $($p.ExitCode)）。"; exit 1 }
    if (Get-PyVersion $InstalledExe) { $py = $InstalledExe }
}

if ($py) {
    # cmd の set /p で読むため、Windows の既定の文字コード（日本語環境では Shift_JIS）で書く。日本語のユーザー名でも化けない
    [System.IO.File]::WriteAllText($OutFile, $py, [System.Text.Encoding]::Default)
    exit 0
}
exit 1
