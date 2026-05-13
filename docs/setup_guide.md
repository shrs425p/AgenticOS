# AgenticOS: Comprehensive Setup Guide

Welcome to AgenticOS! This guide will walk you through the end-to-end setup process, from installing dependencies to running your first autonomous task.

---

## [TOOL] Step 1: System Prerequisites

Before you begin, ensure your machine meets the [System Requirements](system_requirements.md).

1.  **Python 3.12+**: Download from [python.org](https://www.python.org/downloads/).
2.  **Git**: For cloning the repository.
3.  **Terminal**: Windows Terminal, PowerShell, or CMD.
4.  **Environment Sync**: (Optional) Run `powershell .\setup.ps1` to set the project root in your system PATH and enable the `agent` command.

---

## [FILE] Step 2: Clone & Environment Setup

### Recommended Path: C:\AgenticOs
For maximum stability and performance, we strongly recommend cloning the project into a root-level directory without spaces (e.g., `C:\AgenticOs`). This ensures that the **Fast-Path** PowerShell optimizations and terminal commands function with 100% reliability.

Clone the repository and move into the project directory:

```powershell
git clone https://github.com/your-repo/AgenticOs.git C:\AgenticOs
cd C:\AgenticOs
```

Create and activate a virtual environment to keep your dependencies isolated:

```powershell
python -m venv venv
.\venv\Scripts\activate
```

---

## 📦 Step 3: Install Dependencies

Install the core Python packages and the Playwright browser engine:

```powershell
pip install -r requirements.txt
playwright install chromium
```

---

## 🔐 Step 4: Configure Credentials (.env)

AgenticOS needs API keys to talk to cloud providers. Create a file named `.env` in the root directory:

```powershell
notepad .env
```

Add your keys in the following format:

```env
NVIDIA_API_KEY=your_nvidia_nim_key
GOOGLE_API_KEY=your_google_gemini_key
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
```

*Note: Your `.env` file is automatically ignored by Git to prevent accidental leakage.*

---

## [CONFIG] Step 5: Runtime Configuration (config.yaml)

Open `config.yaml` to define your agent's behavior.

### 1. Choose Your Provider
Set the default model provider (local or cloud):
```yaml
agent:
  provider: nvidia # Options: ollama, nvidia, gemini, groq
```

### 2. Configure Local AI (Optional)
If you want to use **Ollama**, download it from [ollama.com](https://ollama.com/) and pull a model:
```powershell
ollama pull qwen2.5-coder:7b
```
Then verify the `ollama:` section in `config.yaml` matches your model name.

---

## [LAUNCH] Step 6: Launching AgenticOS

Once everything is configured, start the agent:

```powershell
python main.py
```

### The Startup Sequence:
1.  **Banner**: You will see the AgenticOS ASCII art banner.
2.  **Initialization**: The system loads the Tool Registry and checks for plugins.
3.  **Hot-Reload**: The system monitors `config.yaml` for changes.

---

## [TEST] Step 7: Your First Task

Try giving the agent a simple system-level task to verify it has the correct permissions:

> *"Check my system health and tell me the top 3 processes using the most RAM."*

The agent should:
1.  Draft a plan.
2.  Call the `process_list` tool.
3.  Analyze the results.
4.  Provide a specific answer in the terminal.

---

## [FILE] Step 8: Safety Guide

By default, AgenticOS is in **Secure Mode**.
-   **Security**: It will ask for permission before writing to any folder outside `workspace/`.
-   **Autonomy**: If you want it to be more "hands-off," set `autonomy: autopilot: true` in `config.yaml`.

---

## [FILE] Project Structure
- `core/`: The Runtime Engine, Tool Registry, Memory, and Security Guardrails.
- `tools/`: Modular library of core tools and dynamic `plugins/`.
- `docs/`: Comprehensive technical documentation (19 detailed guides).
- `bin/`: CLI commands (e.g., `agent.bat`). This folder is added to your PATH.
- `workspace/`: Designated environment for task artifacts and reports.
- `data/`: Persistent session memory (SQLite) and audit logs.

---

## [FILE] Troubleshooting the Setup

-   **ModuleNotFoundError**: Ensure you are inside the `venv` (`.\venv\Scripts\activate`).
-   **API Key Error**: Double-check that your `.env` variables are correctly named and have no extra spaces.
-   **Browser Error**: If Playwright fails, run `playwright install --with-deps chromium`.

---

## [END] Next Steps
-   Read the [Architecture Deep-Dive](architecture.md).
-   Learn how to write [Custom Plugins](tool_development.md).
-   Explore the [API Reference](api_reference.md) for a list of all 300+ tools.

---

*Last Updated: 2026-05-14*
*Status: Secure & Verified*
