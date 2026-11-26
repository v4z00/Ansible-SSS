[CmdletBinding()]
param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$serverProcess = $null

function ConvertTo-NativeArgument([string]$Value) {
    # CommandLineToArgvW quoting for Windows PowerShell 5.1 / .NET Framework.
    return '"' + (($Value -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
}

try {
    foreach ($name in @('recover.py', 'notfall_entschluesselung.html', 'install-voraussetzungen.ps1', 'install-voraussetzungen.sh')) {
        if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $name) -PathType Leaf)) {
            throw "Missing file: $name. Extract the complete recovery folder."
        }
    }
    & (Join-Path $PSScriptRoot 'install-voraussetzungen.ps1')
    $wsl = Join-Path $env:WINDIR 'System32\wsl.exe'
    $converted = @(& $wsl --distribution Ubuntu --exec wslpath -a (Join-Path $PSScriptRoot 'recover.py'))
    if ($LASTEXITCODE -ne 0 -or $converted.Count -ne 1) { throw 'WSL cannot access recover.py.' }

    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $wsl
    $start.Arguments = '--distribution Ubuntu --exec python3 ' + (ConvertTo-NativeArgument $converted[0]) + ' --web --stop-on-stdin-close'
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardInput = $true
    $start.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $serverProcess = New-Object System.Diagnostics.Process
    $serverProcess.StartInfo = $start
    if (-not $serverProcess.Start()) { throw 'The local service could not start.' }
    Write-Host 'Offline recovery. The first share identifies the required quorum.'
    Write-Host 'Keep this window open. Press Ctrl+C to stop.'
    $opened = $false
    while ($true) {
        $pendingLine = $serverProcess.StandardOutput.ReadLineAsync()
        while (-not $pendingLine.IsCompleted) { Start-Sleep -Milliseconds 100 }
        $line = $pendingLine.GetAwaiter().GetResult()
        if ($null -eq $line) { break }
        Write-Host $line
        if (-not $opened -and $line -match '^http://127\.0\.0\.1:[0-9]+/[A-Za-z0-9_-]+/$') {
            $opened = $true
            if (-not $NoBrowser) {
                try { Start-Process -FilePath $line }
                catch { Write-Host 'Open the displayed address manually in your browser.' }
            }
        }
    }
    $serverProcess.WaitForExit()
    if ($serverProcess.ExitCode -notin @(0, 130)) { throw "Recovery service exited (code $($serverProcess.ExitCode))." }
}
catch {
    Write-Host ('Error: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
finally {
    if ($null -ne $serverProcess) {
        try {
            # EOF stops this Python service while preserving other WSL sessions.
            if (-not $serverProcess.HasExited) {
                $serverProcess.StandardInput.Close()
                if (-not $serverProcess.WaitForExit(5000)) { $serverProcess.Kill() }
            }
        } catch { }
        $serverProcess.Dispose()
    }
}
