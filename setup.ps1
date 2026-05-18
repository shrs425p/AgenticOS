# AgenticOS: Environment Configuration Script
# This script sets AGENTICOS_HOME and adds the project directory to your PATH.

$ProjectRoot = $PSScriptRoot

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

# 2b. Auto-generate workspace README.md if missing
$WorkspaceReadme = Join-Path $ProjectRoot "workspace\README.md"
$ReadmeTemplate = Join-Path $ProjectRoot "config\workspace_readme_template.md"
if (-not (Test-Path $WorkspaceReadme) -and (Test-Path $ReadmeTemplate)) {
    Copy-Item -Path $ReadmeTemplate -Destination $WorkspaceReadme -Force
    Write-Host "[INFO] Automatically generated workspace README.md from template." -ForegroundColor Gray
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

# 5. Verify Python Installation
Write-Host "[INFO] Verifying Python installation..." -ForegroundColor White
try {
    $PythonVer = & python --version 2>&1
    Write-Host "[INFO] Detected Python: $PythonVer" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Python was not found on your system. Please install Python 3.12+ first." -ForegroundColor Red
    exit 1
}

# 6. Initialize Virtual Environment
$VenvPath = Join-Path $ProjectRoot "venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "[INFO] Creating Python virtual environment (venv)..." -ForegroundColor White
    & python -m venv venv
    if (-not (Test-Path $VenvPath)) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
    Write-Host "[SUCCESS] Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "[INFO] Virtual environment already exists." -ForegroundColor Gray
}

# 7. Install Python Dependencies
$PipPath = Join-Path $VenvPath "Scripts\pip.exe"
$PythonExePath = Join-Path $VenvPath "Scripts\python.exe"
$PlaywrightPath = Join-Path $VenvPath "Scripts\playwright.exe"

if (-not (Test-Path $PipPath) -or -not (Test-Path $PythonExePath)) {
    Write-Host "[ERROR] Virtual environment executables not found. Please delete 'venv' folder and run setup again." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Upgrading pip inside virtual environment..." -ForegroundColor White
& $PythonExePath -m pip install --upgrade pip

$ReqFile = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path $ReqFile) {
    Write-Host "[INFO] Installing Python dependencies from requirements.txt..." -ForegroundColor White
    & $PipPath install -r $ReqFile
}

$ReqDevFile = Join-Path $ProjectRoot "requirements-dev.txt"
if (Test-Path $ReqDevFile) {
    Write-Host "[INFO] Installing development dependencies from requirements-dev.txt..." -ForegroundColor White
    & $PipPath install -r $ReqDevFile
}

# 8. Install Playwright Chromium Browser
if (Test-Path $PlaywrightPath) {
    Write-Host "[INFO] Installing Playwright Chromium browser..." -ForegroundColor White
    & $PlaywrightPath install chromium
} else {
    Write-Host "[WARNING] Playwright executable not found. Skipping Playwright installation." -ForegroundColor Yellow
}

# 9. Configure Credentials (.env)
$EnvFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $EnvFile)) {
    $EnvExample = Join-Path $ProjectRoot ".env.example"
    if (Test-Path $EnvExample) {
        Copy-Item -Path $EnvExample -Destination $EnvFile -Force
        Write-Host "[SUCCESS] Automatically generated .env file from template." -ForegroundColor Green
        
        if (Get-Process -Name "explorer" -ErrorAction SilentlyContinue) {
            Write-Host "[INFO] Opening .env file in Notepad. Please edit it to configure your API keys." -ForegroundColor Cyan
            Start-Process notepad.exe -ArgumentList $EnvFile
        } else {
            Write-Host "[INFO] Please edit the newly created .env file to configure your API keys." -ForegroundColor Cyan
        }
    }
} else {
    Write-Host "[INFO] .env file is already configured." -ForegroundColor Gray
}

Write-Host "[SUCCESS] Environment configured successfully! Please restart your terminal for changes to take effect." -ForegroundColor Green
Write-Host "[TIP] You can now run 'agent' from any directory." -ForegroundColor Yellow

