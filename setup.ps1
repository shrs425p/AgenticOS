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
$PythonInstalled = $false
try {
    $PythonVer = & python --version 2>&1
    if ($PythonVer -is [System.Management.Automation.ErrorRecord]) {
        throw "Python not found"
    }
    
    # Check if Python version is 3.12+
    $Null = & python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARNING] Detected Python version is older than 3.12. Detected version: $PythonVer" -ForegroundColor Yellow
    } else {
        $PythonInstalled = $true
        Write-Host "[INFO] Detected Python: $PythonVer" -ForegroundColor Gray
        Write-Host "[SUCCESS] Python version requirement (3.12+) met." -ForegroundColor Green
    }
} catch {
    # Python is not installed or not in PATH
}

if (-not $PythonInstalled) {
    Write-Host "[WARNING] Python 3.12+ was not found on your system." -ForegroundColor Yellow
    $Choice = Read-Host "Do you want to download and install Python 3.12 automatically? (Y/N)"
    if ($Choice -eq 'Y' -or $Choice -eq 'y') {
        Write-Host "[INFO] Attempting to install Python 3.12 via winget..." -ForegroundColor Cyan
        $InstallSuccess = $false
        try {
            winget install --id Python.Python.3.12 --exact --silent --accept-package-agreements --accept-source-agreements --scope user
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[SUCCESS] Python 3.12 installed successfully via winget." -ForegroundColor Green
                $InstallSuccess = $true
            } else {
                throw "winget returned non-zero exit code"
            }
        } catch {
            Write-Host "[INFO] winget installation failed or is unavailable. Downloading installer directly..." -ForegroundColor Cyan
            try {
                $InstallerUrl = "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe"
                $InstallerPath = Join-Path $env:TEMP "python-installer.exe"
                Write-Host "[INFO] Downloading Python installer from $InstallerUrl ..." -ForegroundColor Gray
                Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath
                Write-Host "[INFO] Running Python installer silently (Adding Python to PATH)..." -ForegroundColor Gray
                $InstallProcess = Start-Process -FilePath $InstallerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -PassThru -Wait
                if ($InstallProcess.ExitCode -eq 0) {
                    Write-Host "[SUCCESS] Python 3.12 installed successfully." -ForegroundColor Green
                    $InstallSuccess = $true
                } else {
                    Write-Host "[ERROR] Python installation failed with exit code $($InstallProcess.ExitCode). Please install Python 3.12+ manually." -ForegroundColor Red
                    exit 1
                }
            } catch {
                Write-Host "[ERROR] Failed to download or execute Python installer: $_. Please install Python 3.12+ manually." -ForegroundColor Red
                exit 1
            }
        }

        if ($InstallSuccess) {
            # Hot-reload environment variables in the active session
            Write-Host "[INFO] Refreshing environment PATH for the current session..." -ForegroundColor Cyan
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
            
            # Re-verify Python in active session
            try {
                $PythonVer = & python --version 2>&1
                if ($PythonVer -isnot [System.Management.Automation.ErrorRecord]) {
                    Write-Host "[SUCCESS] Python is now active in this session. Continuing setup..." -ForegroundColor Green
                } else {
                    throw "Python still not found in active session PATH"
                }
            } catch {
                Write-Host "[IMPORTANT] Python was installed, but we could not hot-reload it into the active terminal process." -ForegroundColor Yellow
                Write-Host "[IMPORTANT] Please restart your terminal/IDE and run the setup script again to complete the configuration." -ForegroundColor Cyan
                exit 0
            }
        }
    } else {
        Write-Host "[INFO] Installation cancelled. Please install Python 3.12+ manually to continue." -ForegroundColor Yellow
        exit 1
    }
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

# 10. Perform System Diagnostic & Health Summary
Write-Host "`n[INFO] Running System Diagnostics & Health Checks..." -ForegroundColor Cyan

$DiagnosticPassed = $true

# check Internet
try {
    $Ping = Test-Connection -ComputerName google.com -Count 1 -ErrorAction SilentlyContinue
    if ($Ping) {
        Write-Host "[SUCCESS] Network Connection: Online" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Network Connection: Offline or slow" -ForegroundColor Yellow
        $DiagnosticPassed = $false
    }
} catch {
    Write-Host "[WARNING] Network Connection: Offline or slow" -ForegroundColor Yellow
    $DiagnosticPassed = $false
}

# check .env API keys
$PlaceholdersFound = @()
if (Test-Path $EnvFile) {
    $EnvContent = Get-Content $EnvFile
    foreach ($Line in $EnvContent) {
        if ($Line -match "^\s*([A-Za-z0-9_]+)\s*=\s*(.*)$") {
            $Key = $Matches[1]
            $Val = $Matches[2].Trim()
            if ($Val -eq "" -or $Val -like "your_*") {
                $PlaceholdersFound += $Key
            }
        }
    }
}
if ($PlaceholdersFound.Count -gt 0) {
    Write-Host "[WARNING] Credentials Config: Missing / Placeholder keys found ($($PlaceholdersFound -join ', '))" -ForegroundColor Yellow
    $DiagnosticPassed = $false
} else {
    Write-Host "[SUCCESS] Credentials Config: Configured" -ForegroundColor Green
}

# check Python & venv executables
if ((Test-Path $PythonExePath) -and (Test-Path $PipPath)) {
    Write-Host "[SUCCESS] Virtual Environment: Configured and healthy" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Virtual Environment: Missing or corrupted executables" -ForegroundColor Red
    $DiagnosticPassed = $false
}

Write-Host ""
if ($DiagnosticPassed) {
    Write-Host "[SUCCESS] System Health: Perfect! AgenticOS is ready for launch." -ForegroundColor Green
} else {
    Write-Host "[WARNING] System Health: Configuration is incomplete. Please see warnings above." -ForegroundColor Yellow
}

Write-Host "`n[SUCCESS] Environment configured successfully! Please restart your terminal for changes to take effect." -ForegroundColor Green
Write-Host "[TIP] You can now run 'agent' from any directory." -ForegroundColor Yellow

