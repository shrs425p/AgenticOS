# AgenticOS lightweight launcher registration.
# Updates user-level PATH so the global `agent` command resolves to this checkout.

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$CliPath = Join-Path $ProjectRoot "cli"

if (-not (Test-Path $CliPath)) {
    Write-Host "[ERROR] cli directory not found at $CliPath" -ForegroundColor Red
    exit 1
}

[Environment]::SetEnvironmentVariable("AGENTICOS_HOME", $ProjectRoot, "User")

$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathParts = @()
if ($CurrentPath) {
    $PathParts = $CurrentPath -split ';' | Where-Object {
        $_ -and ($_ -ne $CliPath)
    }
}

$NewPath = (@($CliPath) + $PathParts) -join ';'
[Environment]::SetEnvironmentVariable("Path", $NewPath, "User")

$MachinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$env:Path = if ($MachinePath) { "$NewPath;$MachinePath" } else { $NewPath }
$env:AGENTICOS_HOME = $ProjectRoot

$Signature = @"
using System;
using System.Runtime.InteropServices;
public static class EnvNotify {
    [DllImport("user32.dll", SetLastError=true, CharSet=CharSet.Auto)]
    public static extern IntPtr SendMessageTimeout(
        IntPtr hWnd,
        uint Msg,
        UIntPtr wParam,
        string lParam,
        uint fuFlags,
        uint uTimeout,
        out UIntPtr lpdwResult);
}
"@
try {
    Add-Type -TypeDefinition $Signature -ErrorAction Stop
    $Result = [UIntPtr]::Zero
    [EnvNotify]::SendMessageTimeout([IntPtr]0xffff, 0x1A, [UIntPtr]::Zero, "Environment", 0x0002, 5000, [ref]$Result) | Out-Null
} catch {
    Write-Host "[WARN] Could not broadcast environment refresh. Restarting the terminal will still work." -ForegroundColor Yellow
}

Write-Host "[OK] Registered AgenticOS launcher:" -ForegroundColor Green
Write-Host "     $CliPath" -ForegroundColor Gray
Write-Host "[OK] Restart your terminal, then run: agent" -ForegroundColor Green
Write-Host ""
Write-Host "For this CMD window only, run:" -ForegroundColor Yellow
Write-Host 'for /f "tokens=2*" %A in (''reg query HKCU\Environment /v Path'') do set "PATH=%B;%PATH%"' -ForegroundColor Gray
Write-Host ""
Write-Host "For this PowerShell window only, run:" -ForegroundColor Yellow
Write-Host '$env:Path = [Environment]::GetEnvironmentVariable("Path","User") + ";" + [Environment]::GetEnvironmentVariable("Path","Machine")' -ForegroundColor Gray
