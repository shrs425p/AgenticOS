@echo off
:: AgenticOS Advanced Launcher
:: This script manages caches, environment activation, and UTF-8 encoding.
setlocal

:: Resolve the project root (one level up from the cli folder)
set "BIN_DIR=%~dp0"
set "AGENT_BASE_DIR=%BIN_DIR%.."

:: Route common caches into one folder (keeps repo root clean).
set "CACHE_ROOT=%AGENT_BASE_DIR%\data\cache"
if not exist "%CACHE_ROOT%" mkdir "%CACHE_ROOT%" >nul 2>&1
if not exist "%CACHE_ROOT%\pycache" mkdir "%CACHE_ROOT%\pycache" >nul 2>&1
if not exist "%CACHE_ROOT%\ruff" mkdir "%CACHE_ROOT%\ruff" >nul 2>&1
if not exist "%CACHE_ROOT%\pip" mkdir "%CACHE_ROOT%\pip" >nul 2>&1
if not exist "%CACHE_ROOT%\pytest" mkdir "%CACHE_ROOT%\pytest" >nul 2>&1

set "PYTHONPYCACHEPREFIX=%CACHE_ROOT%\pycache"
set "RUFF_CACHE_DIR=%CACHE_ROOT%\ruff"
set "PIP_CACHE_DIR=%CACHE_ROOT%\pip"
if "%PYTEST_ADDOPTS%"=="" (
  set "PYTEST_ADDOPTS=--cache-dir=%CACHE_ROOT%\pytest"
) else (
  echo %PYTEST_ADDOPTS% | findstr /C:"--cache-dir" >nul 2>&1
  if errorlevel 1 set "PYTEST_ADDOPTS=%PYTEST_ADDOPTS% --cache-dir=%CACHE_ROOT%\pytest"
)

:: Activate the virtual environment if it exists
if exist "%AGENT_BASE_DIR%\venv\Scripts\activate" (
    call "%AGENT_BASE_DIR%\venv\Scripts\activate"
)

:: Force UTF-8 for emoji and special character support
set "PYTHONIOENCODING=utf-8"

:: Launch the kernel engine
python "%AGENT_BASE_DIR%\main.py" %*

endlocal
