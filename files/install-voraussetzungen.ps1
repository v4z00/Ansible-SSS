# Windows 10/11 with WSL support. Run as a regular Windows user.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$distribution = 'Ubuntu'
$wsl = Join-Path $env:WINDIR 'System32\wsl.exe'
if (-not (Test-Path -LiteralPath $wsl)) {
    throw 'Install a supported version of WSL for Windows. See START-HERE.md.'
}

$ready = $false
try {
    $listed = @(& $wsl --list --quiet 2>$null)
    $ready = ($LASTEXITCODE -eq 0)
} catch { $listed = @() }
if (-not $ready) {
    Write-Host 'WSL is not ready. Windows will request administrator access (UAC).'
    Write-Host 'Installing WSL components. Restart Windows manually if requested.'
    $process = Start-Process -FilePath $wsl -ArgumentList @('--install', '--no-distribution') -Verb RunAs -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) {
        throw "WSL setup failed (code $($process.ExitCode)). Contact your administrator for assistance."
    }
    throw 'WSL preparation finished. Restart if Windows requests it, then run start-html.bat again.'
}
$names = @($listed | ForEach-Object { ($_ -replace "`0", '').Trim() })
if ($names -notcontains $distribution) {
    Write-Host 'Installing Ubuntu for this Windows user.'
    & $wsl --install --distribution $distribution --no-launch
    if ($LASTEXITCODE -ne 0) {
        throw 'Ubuntu setup needs attention. Follow the WSL instructions and start the launcher again.'
    }
    Write-Host 'Opening Ubuntu for the first time. Create the Linux account if prompted.'
    Write-Host 'When the Ubuntu shell is ready, type exit to continue setup.'
    & $wsl --distribution $distribution
    if ($LASTEXITCODE -ne 0) { throw 'Ubuntu first-run setup is incomplete.' }
}

# Pass paths to wslpath as separate arguments.
$installer = Join-Path $PSScriptRoot 'install-voraussetzungen.sh'
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw 'Missing install-voraussetzungen.sh in the tool directory.' }
$converted = @(& $wsl --distribution $distribution --exec wslpath -a $installer)
if ($LASTEXITCODE -ne 0 -or $converted.Count -ne 1) { throw 'WSL cannot access the directory. Extract the kit onto a local Windows drive.' }
Write-Host 'Checking Linux prerequisites. Ubuntu may request the Linux sudo password.'
& $wsl --distribution $distribution --exec bash $converted[0]
if ($LASTEXITCODE -ne 0) { throw 'Linux prerequisites could not be installed.' }
