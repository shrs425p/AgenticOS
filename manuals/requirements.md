# AgenticOS: System Requirements and Prerequisites

To ensure stable, high-performance autonomous operations, your host machine must meet certain hardware and software requirements. This document outlines the minimum and recommended specifications for running AgenticOS in both local-only and cloud-hybrid modes.

---

##  Hardware Requirements

### 1. Minimal Specifications (Cloud-Hybrid Mode)
If you are offloading the "thinking" to cloud providers like Nvidia or Google, AgenticOS is relatively lightweight.
-   **CPU**: 4-Core Processor (Intel i5 / AMD Ryzen 5 or equivalent).
-   **RAM**: 8GB DDR4.
-   **Disk**: 2GB free space for logs and workspace.
-   **OS**: Windows 10/11, macOS 12+ (Monterey or later), or Linux (Ubuntu 20.04+, Debian 11+, Fedora 36+, or equivalent).

### 2. Recommended Specifications (Local-Only Mode / Ollama)
Running high-quality local models like `qwen2.5-coder:7b` or `llama-3.1:8b` requires significant local resources.
-   **CPU**: 8-Core Processor (Intel i7 / AMD Ryzen 7 / Apple Silicon M1 or equivalent).
-   **RAM**: 16GB - 32GB (Essential for handling large context windows).
-   **GPU (VRAM)**: 
    -   **NVIDIA RTX 3060+ (8GB VRAM)**: Ideal for 7B-8B parameter models.
    -   **Apple Silicon (Unified Memory)**: M1/M2/M3 with 16GB+ unified memory.
    -   **NVIDIA RTX 4080+ (16GB VRAM)**: Required for 14B+ parameter models.
-   **Disk**: 50GB free space on an **NVMe SSD** (Necessary for fast model loading and the "Fast-Path" disk audits).

---

## Software Prerequisites

### 1. Python Environment
-   **Version**: Python 3.12 or later is strictly required.
-   **PIP**: Latest version for installing dependencies.
-   **Virtual Environment**: We strongly recommend using `venv` to avoid dependency conflicts.

### 2. Native Tools (Multi-Platform)
AgenticOS leverages native operating system utilities to perform system tasks and integrations:
-   **Windows**:
    -   **PowerShell 5.1+**: Standard on Windows 10/11.
    -   **WMI (Windows Management Instrumentation)**: For system resource diagnostics.
-   **macOS (Darwin)**:
    -   **AppleScript & System Events**: Requires Accessibility permissions for window and desktop actions.
    -   **Screencapture & Say**: Native system utilities for screenshots and Speech.
-   **Linux**:
    -   **Xdotool / Ydotool**: For keyboard and mouse simulation.
    -   **Zenity / Xmessage / Notify-send**: GUI wrappers for alerts and popup dialogs.
    -   **Scrot / Gnome-screenshot / Import**: Standard utilities for screenshot capabilities.
-   **Playwright Dependencies**: Requires the Chromium/Firefox browser cliaries (installed via `playwright install`).

### 3. Ollama (Optional but Recommended)
For local-first privacy, you must install and run the Ollama service.
-   **Download**: [ollama.com/download](https://ollama.com/download)
-   **Verification**: Run `ollama list` in your terminal to ensure the service is active.

---

## Network Requirements

### Connectivity
-   **Cloud Mode**: Stable internet connection is required for Nvidia/Google/OpenAI APIs.
-   **Local Mode**: Can run entirely offline once the models are downloaded.

### Ports and Firewall
AgenticOS typically communicates over the following ports:
-   **Port 11434**: Default port for the local Ollama API.
-   **Port 443**: Standard HTTPS port for cloud API communication.

---

## OS-Level Permissions

AgenticOS is designed to run in a standard user context. 
-   **Standard User**: Sufficient for 95% of tasks (File editing, Web research, Process monitoring).
-   **Administrator**: Required only if the agent needs to modify system-level registry keys or start/stop critical Windows services.
-   **Security Note**: We recommend running the agent in a dedicated "Agent" user account if you plan to enable `autopilot: true` for system-level changes.

---

## Scaling Guidelines

| Workload | Recommended Specs | Key Bottleneck |
| :--- | :--- | :--- |
| **Simple File Edits** | 8GB RAM / Any CPU | Network Latency |
| **Full Drive Audits** | NVMe SSD | Disk I/O Speed |
| **Browser Automation**| 16GB RAM | CPU / Thread Count |
| **Large Codebases** | 32GB RAM / 12GB VRAM| Context Window Size |

---

## System Health Check

You can verify if your current machine meets the requirements by asking the agent:
> *"Run a system health check and tell me if my hardware is ready for local Ollama models."*

The agent will call `systemhealth` and compare your RAM, CPU, and VRAM against the targets listed in this document.

---

##  Updating Dependencies

To keep the system at peak performance, ensure your Python packages are up to date:
```powershell
pip install --upgrade -r requirements.txt
```

---

*Last Updated: 2026-05-18*
*Status: Verified on Win11, macOS Darwin, and Ubuntu GNOME*
