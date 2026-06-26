<!-- generated-by: gsd-doc-writer -->
# Setup Guide

This guide walks you through setting up AgenticOS for the first time.

---

## Prerequisites
Before installing AgenticOS, ensure your system meets the following requirements:
- **Python**: version >= 3.10
- **Git**: installed and added to your system PATH
- **Operating System**: Windows 10/11, macOS, or modern Linux (Ubuntu/Debian recommended)

---

## Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/shrs425p/AgenticOS.git
   cd AgenticOS
   ```

2. **Run Installer Script**:
   AgenticOS provides automated setup scripts that create a virtual environment, install package dependencies, and set up base directories.
   - **On Windows (PowerShell):**
     ```powershell
     .\setup.ps1
     ```
   - **On macOS/Linux (Bash):**
     ```bash
     chmod +x setup.sh
     ./setup.sh
     ```

3. **Configure Environment Variables**:
   Copy the example environment template and add your API keys:
   ```bash
   cp .env.example .env
   ```
   Open the `.env` file in your editor and configure the desired LLM API keys (e.g. `NVIDIA_API_KEY`, `GEMINI_API_KEY`). If using Ollama, no API key is necessary.

---

## First Run

1. **Run Health Check Diagnostics**:
   Verify that Python, active configurations, API keys, and local tool imports are in a valid state:
   ```bash
   venv\Scripts\python main.py --health
   ```
   *(On macOS/Linux, run `source venv/bin/activate` followed by `python main.py --health`)*

2. **Launch the Orchestrator**:
   ```bash
   venv\Scripts\python main.py
   ```

---

## Common Setup Issues

### 1. Ollama Connection Error (`urllib.error.URLError`)
- **Symptoms**: Health check reports `✗ Provider Ollama is Unreachable`.
- **Solution**: Ensure the Ollama desktop application is active and listening. Verify by visiting `http://localhost:11434` in your browser. If Ollama is running on a different port, update the `ollama.base_url` key in `config.yaml`.

### 2. Missing Environment Variables
- **Symptoms**: Startup fails with a critical configuration error.
- **Solution**: Check that `.env` is created in the project root and contains valid entries. Keys must not contain quotes unless required by specific variable patterns.

### 3. macOS Accessibility Permissions
- **Symptoms**: Native OS window/UI tools raise permission errors.
- **Solution**: When prompted by macOS, grant Accessibility permissions to your terminal or IDE, then restart the execution loop.

---

## Next Steps
- Read [docs/developer_onboarding.md](file:///c:/Users/pawar/AgenticOS/docs/developer_onboarding.md) to learn how to develop custom plugins.
- Read [docs/testing_guide.md](file:///c:/Users/pawar/AgenticOS/docs/testing_guide.md) to understand the test suite.
