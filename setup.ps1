# AgenticOS: Environment Configuration Script
# This script sets AGENTICOS_HOME and adds the project directory to your PATH.

$ProjectRoot = "C:\AgenticOs"

Write-Host "[INFO] Configuring AgenticOS environment..." -ForegroundColor Cyan

# 1. Check if the directory exists
if (-not (Test-Path $ProjectRoot)) {
    Write-Host "[ERROR] Project directory not found at $ProjectRoot. Please move the project there first." -ForegroundColor Red
    exit 1
}

# 2. Create required directories
Write-Host "[INFO] Initializing project structure..." -ForegroundColor White
$Dirs = @("workspace", "data", "data\logs", "bin")
foreach ($Dir in $Dirs) {
    $Path = Join-Path $ProjectRoot $Dir
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
        Write-Host "[INFO] Created directory: $Dir" -ForegroundColor Gray
    }
}

# 3. Set AGENTICOS_HOME (User Level)
Write-Host "[INFO] Setting AGENTICOS_HOME to $ProjectRoot..." -ForegroundColor White
[Environment]::SetEnvironmentVariable("AGENTICOS_HOME", $ProjectRoot, "User")

# 4. Add to PATH (User Level)
$BinPath = Join-Path $ProjectRoot "bin"
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$BinPath*") {
    Write-Host "[INFO] Adding $BinPath to your PATH..." -ForegroundColor White
    $NewPath = "$CurrentPath;$BinPath"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
} else {
    Write-Host "[INFO] $BinPath is already in your PATH." -ForegroundColor Green
}

Write-Host "[SUCCESS] Environment configured! Please restart your terminal for changes to take effect." -ForegroundColor Green
Write-Host "[TIP] You can now run agent from any directory." -ForegroundColor Yellow
