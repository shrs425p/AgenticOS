# AgenticOS: 2-Minute Quick Start Guide

This guide gets AgenticOS running on your system in under two minutes.

---

## Prerequisites

Before starting, ensure you have:
*   Python 3.12+ installed on your system.
*   Git command line client.

---

## 1. Quick Setup

Run the following commands in your terminal to clone the project, sync the environment, and register the global command wrapper.

### Windows (PowerShell)
```powershell
git clone https://github.com/shrs425p/AgenticOS.git AgenticOS
```
```powershell
cd AgenticOS
```
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

### macOS / Linux (Bash/Zsh)
```bash
git clone https://github.com/shrs425p/AgenticOS.git AgenticOS
```
```bash
cd AgenticOS
```
```bash
./setup.sh
```

---

## 2. Configure API Keys

Open the newly created `.env` file in your project root and add your API keys:

```env
NVIDIA_API_KEY=your_nvidia_nim_key
GOOGLE_API_KEY=your_google_gemini_key
```

*Note: You only need to configure one provider key (e.g. Nvidia or Gemini) to begin running tasks.*

---

## 3. Run Your First Task

Launch the autonomous runtime agent:

```bash
agent
```

Once the AgenticOS execution loop boots, type your task in the prompt. For example:

```text
Check my system health and tell me the top 3 processes using the most RAM.
```

The agent will design an execution plan, run the necessary system telemetry tools, analyze the output, and display the formatted results in your terminal.

---

## Common Use Cases

Here are three common automation workflows you can execute with AgenticOS:

### ◆ A. System Diagnostics and Resource Audit
Ask the agent:
> *"Run a system diagnostics scan and list the top 3 processes consuming the most RAM."*

Heuristics:
*   Calls the `process_list` tool.
*   Sorts active system processes by physical memory footprint.
*   Returns a clean markdown table of CPU and RAM usage.

### ◆ B. Autonomous Web Research
Ask the agent:
> *"Search the web for the latest developments in local LLMs and save a summary to research.md."*

Heuristics:
*   Executes `web_search` to query technical search engines.
*   Fetches content from relevant web pages using sandboxed HTTP clients.
*   Synthesizes the findings and writes a formatted markdown report to the workspace.

### ◆ C. Filesystem Cleanup
Ask the agent:
> *"Find all temporary log files in my workspace directory and clean them up."*

Heuristics:
*   Uses optimized filesystem tools to scan the active workspace.
*   Filters files by matching extensions or patterns.
*   Safely removes the temporary files, respecting all PathGuard workspace boundary zones.

---

## Next Steps

*   **Custom Configurations**: See the [Runtime Configuration Guide](runtime_configuration.md) to tweak YAML profiles.
*   **Security Policy**: Review the [Security and Guardrails Manual](security_guardrails.md) to understand PathGuard zones.
*   **API reference**: Look at the [API Reference Catalog](api_reference.md) to explore the 350+ built-in system tools.
