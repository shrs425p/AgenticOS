# Technology Stack

**Analysis Date:** 2026-06-05

## Languages

**Primary:**
- Python 3.10+ - All application runtime, core orchestration, tools, and testing code.

**Secondary:**
- PowerShell 5.1+ - Environment setup and configuration scripts for Windows (`setup.ps1`).
- Bash 3.2+ - Environment setup and configuration scripts for macOS/Linux (`setup.sh`).

## Runtime

**Environment:**
- Python 3.10+ virtual environment (`venv`).
- Windows Command Prompt/PowerShell, macOS Terminal, or Linux Bash.

**Package Manager:**
- pip (included in virtual environment)
- Lockfile/dependencies: `requirements.txt` and `requirements-dev.txt` are present.

## Frameworks

**Core:**
- Custom AgenticOS Framework - Private, secure, high-performance personal AI orchestration framework.

**Testing:**
- pytest 9.0.3 - Unit and integration testing framework.
- pytest-cov 7.1.0 - Code coverage measurement.

**Build/Dev:**
- ruff 0.15.15 - Fast Python linter and formatter.
- black 26.5.1 - Deterministic Python code formatter.
- mypy 2.1.0 - Static type checker for Python.
- radon 6.0.1 - Cyclomatic complexity code analyzer.
- pdoc 16.0.0 - API documentation generator.
- bandit 1.9.4 - Security linter/auditor.

## Key Dependencies

**Critical:**
- `google-genai` 2.8.0 - Official client SDK for Google Gemini models.
- `openai` 2.41.0 - Client SDK for OpenAI-compatible APIs (e.g. Nvidia NIM cloud endpoints).
- `groq` 1.4.0 - Client SDK for Groq API endpoint acceleration.
- `playwright` 1.60.0 - Browser automation engine for E2E crawling and page scraping.

**Infrastructure:**
- `requests` 2.34.2 & `httpx` 0.28.1 - Synchronous and asynchronous HTTP networking libraries.
- `pyyaml` 6.0.3 - Config parser for YAML configuration files.
- `python-dotenv` 1.2.2 - Parses environment variables from `.env` file.
- `pyautogui` 0.9.54 - Cross-platform GUI control library.
- `psutil` 5.9.8 - Retrieves hardware/process system metrics.
- `Pillow` 12.2.0 - Image processing support.
- `pandas` 2.2.2 & `numpy` 1.26.4 - Data analysis and structural manipulation.
- `matplotlib` 3.10.9 - Data visualization/plotting library.

## Configuration

**Environment:**
- Configured via `.env` file (stores secret keys like `NVIDIA_API_KEY`, `GOOGLE_API_KEY`).
- Base environment variables loaded dynamically via `python-dotenv`.

**Build:**
- `pytest.ini` - Pytest runtime configuration.
- `pydoc-markdown.yml` - Configuration for API documentation generator.
- `config.yaml` - Main user settings file overriding core defaults.
- `config/*.yaml` - Layered system configuration directories.

## Platform Requirements

**Development:**
- Cross-platform: Windows 10/11, macOS, or modern Linux.
- Requires Python 3.10+ installed globally.

**Production:**
- Runs locally on developer/operator machines.
- Persistent local SQLite database for session memory.

---

*Stack analysis: 2026-06-05*
*Update after major dependency changes*
