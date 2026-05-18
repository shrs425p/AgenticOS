# AgenticOS: Comprehensive Setup Guide

Welcome to AgenticOS! This guide will walk you through the end-to-end setup process, from installing dependencies to running your first autonomous task.

---

## Step 1: System Prerequisites

Before you begin, ensure your machine meets the [System Requirements](system_requirements.md).

1.  **Python 3.12+**: Download from [python.org](https://www.python.org/downloads/).
2.  **Git**: For cloning the repository.
3.  **Terminal**: Windows Terminal, PowerShell, or CMD (Windows); Bash, Zsh, or equivalent (macOS/Linux).
4.  **Environment Sync**: Run the configuration script for your platform—`.\setup.ps1` on Windows or `./setup.sh` on macOS/Linux—once to sync the environment and add `bin/` to your system PATH. This permanently registers the `agent` command so you can launch AgenticOS from any terminal without specifying the full path.


---

## Step 2: Running the Automated Setup Script

For maximum stability and performance, we recommend cloning the project into a root-level or simple home directory path without spaces (e.g., `<REPO_ROOT>` on Windows, or `~/AgenticOs` on macOS/Linux). This ensures that path utilities, Fast-Path optimizations, and terminal commands execute with 100% reliability.

Once cloned and in the project directory, run the setup script. You can execute this natively via your code editor (e.g., VS Code) or the terminal:

#### Windows:
1. Clone the repository and navigate into it:
```powershell
git clone https://github.com/shrs425p/AgenticOS.git <REPO_ROOT>
cd <REPO_ROOT>
```

### Method A: Via VS Code Task (Recommended)
1. Open the project folder in VS Code.
2. Press `Ctrl+Shift+B` (or select **Terminal** -> **Run Build Task** from the Command Palette).
3. The editor will automatically run the correct setup script for your platform, bypassing all Windows execution policy restrictions!

### Method B: Via Terminal

#### Windows (PowerShell or CMD):
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

#### macOS / Linux Setup:
1. Clone the repository and navigate into it:
```bash
git clone https://github.com/shrs425p/AgenticOS.git ~/AgenticOs
cd ~/AgenticOs
```
2. Run the automated setup script:

```bash
./setup.sh
```

### What the Setup Script Automates:
* **Python Auto-Install Option**: If Python 3.12+ is missing or outdated, the script prompts you and handles downloading and installing it automatically via `winget` or direct installer (Windows), Homebrew (macOS), or `apt` (Linux).
* **Hot-Reload Environment PATH**: Instantly refreshes PATH variables in the active PowerShell session, allowing the script to proceed seamlessly to `venv` and package setup without requiring a restart mid-run.
* **Playwright Browsers**: Downloads and registers the Playwright Chromium browser binary automatically.
* **Environment Credentials**: Creates your `.env` template from [.env.example](../.env.example) and prompts/opens it for keys configuration.
* **System Diagnostics & Health Check**: Runs automated checks on network connectivity, `.env` file credentials (to flag empty or placeholder keys), and environment executables before completing the setup.
* **PATH Registration**: Registers the global `agent` command to launch the system from any directory.

---

## Step 3: Configure Credentials (.env)

The setup script automatically copied [.env.example](../.env.example) to `.env` and opened it in your text editor. Add your keys in the following format:

```env
NVIDIA_API_KEY=your_nvidia_nim_key
GOOGLE_API_KEY=your_google_gemini_key
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
```

*Note: Your `.env` file is automatically ignored by Git to prevent accidental leakage.*

Important: AgenticOS loads the `.env` file early at startup via `main.py`. The `.env` file in the repository root is the canonical source of API keys for the running agent and is applied to the process environment before provider clients and plugins initialize.

---

## Step 4: Runtime Configuration (`config/`)

AgenticOS uses a layered configuration system located in the `config/` directory.

### 1. Choose Your Provider (`providers.yaml`)
Open `config/providers.yaml` to define your AI models:
```yaml
agent:
  provider: nvidia # Options: ollama, nvidia, gemini, groq
```

### 2. Set Up Your Environment (`runtime.yaml`)
Open `config/runtime.yaml` to set your workspace path and system heuristics.

### 3. Verify Security Policy (`policy.yaml`)
Review `config/policy.yaml` to ensure the **Secret Redaction Engine** and **PathGuard** are configured correctly.

---

## Step 5: Launching AgenticOS

Once everything is configured, start the agent from any terminal:

#### Windows:
```powershell
agent
```
> **Prerequisite:** You must restart your active terminal once after running `.\setup.ps1` so the newly registered `agent` PATH changes take effect.

#### macOS / Linux:
```bash
agent
```
> **Prerequisite:** Ensure you have added the `bin/` directory to your shell configuration (`.zshrc` / `.bashrc`) as prompted at the end of `./setup.sh`.

### The Startup Sequence:
1.  **Banner**: You will see the AgenticOS ASCII art banner.
2.  **Initialization**: The system loads the Tool Registry and checks for plugins.
3.  **Environment**: `main.py` reads the `.env` file and sets environment variables before provider clients and plugins initialize.
4.  **Hot-Reload**: The system monitors `config/` for changes.

---

## Step 6: Your First Task

Try giving the agent a simple system-level task to verify it has the correct permissions:

> *"Check my system health and tell me the top 3 processes using the most RAM."*

The agent should:
1.  Draft a plan.
2.  Call the `process_list` tool.
3.  Analyze the results.
4.  Provide a specific answer in the terminal.

---

## Step 7: Safety Guide

By default, AgenticOS is in **Secure Mode**.
-   **Security**: It will ask for permission before writing to any folder outside `workspace/`.
-   **Autonomy**: If you want it to be more "hands-off," set `autonomy: autopilot: true` in `config.yaml`.

---

## Project Structure
- `core/`: The Runtime Engine, Tool Registry, Memory, and Security Guardrails.
- `tools/`: Modular library of core tools and dynamic `plugins/`.
- `config/`: Layered YAML configuration system.
- `tests/`: Automated test suite.
- `bin/`: CLI commands (e.g., `agent.bat`). This folder is added to your PATH.
- `workspace/`: Designated environment for task artifacts and reports.
- `data/`: Persistent session memory (SQLite) and audit logs.

---

## Troubleshooting the Setup

-   **ModuleNotFoundError**: Ensure you are running inside the activated environment or using the global `agent` wrapper which activates it automatically.
-   **API Key Error**: Double-check that your `.env` variables are correctly named and have no extra spaces.
-   **Browser Error**: If Playwright fails, run `playwright install --with-deps chromium`.

---

## Step 8: Running the Test Suite (Optional)

To verify your installation is 100% stable:

```powershell
pytest tests/
```

This will run the automated suite to ensure core components, filesystem tools, and security guardrails are functioning correctly.

---

## Next Steps
-   Read the [Architecture Deep-Dive](architecture.md).
-   Learn how to write [Custom Plugins](tool_development.md).
-   Explore the [Testing Guide](testing_guide.md).
-   Explore the [API Reference](api_reference.md) for a list of all 180+ tools.

---

*Last Updated: 2026-05-18*
*Status: Verified on Windows, macOS, and Linux*

