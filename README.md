# AgenticOS: High-Performance Autonomous Framework

<div align="center">
  <img src="assets/AgenticOS-Logo.png" alt="AgenticOS Banner" width="85%">
  
  <br>

  <h3>AgenticOS is a personal artificial superintelligence framework: private, secure, and extremely powerful.</h3>

  <p>
    <a href="https://github.com/shrs425p/AgenticOS/discussions">Discussions</a> | 
    <a href="docs/CATALOG.md">Docs Catalog</a> | 
    <a href="https://github.com/shrs425p/AgenticOS">Follow @shrs425p (Creator)</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/status-production_stable-orange?style=flat-square" alt="Status">
    <img src="https://img.shields.io/badge/latest-v2.1.1-blue?style=flat-square" alt="Latest Version">
    <img src="https://img.shields.io/badge/license-Apache_2.0-red?style=flat-square" alt="License">
    <img src="https://img.shields.io/badge/tools-180-green?style=flat-square" alt="Tools">
    <img src="https://img.shields.io/badge/tests-347_passed-brightgreen?style=flat-square" alt="Tests">
    <a href="https://codecov.io/gh/shrs425p/AgenticOS"><img src="https://codecov.io/gh/shrs425p/AgenticOS/branch/main/graph/badge.svg" alt="Coverage"></a>
  </p>
  
  <p>
    <img src="https://img.shields.io/badge/python-3.10%2B-yellow?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/platform-Windows_|_macOS_|_Linux-blue?style=flat-square" alt="Platform">
    <img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs Welcome">
    <img src="https://img.shields.io/badge/security-verified-brightgreen?style=flat-square" alt="Security">
    <img src="https://github.com/shrs425p/AgenticOS/actions/workflows/ci.yml/badge.svg" alt="CI Build Status">
  </p>

  <br>

  <p>
    <b>Built With:</b><br>
    <img src="https://img.shields.io/badge/Ollama-Local_LLM-white?style=for-the-badge&logo=ollama&logoColor=black" alt="Ollama">
    <img src="https://img.shields.io/badge/NVIDIA-NIM_Cloud-76B900?style=for-the-badge&logo=nvidia&logoColor=white" alt="NVIDIA">
    <img src="https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Playwright-Browser_Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright">
  </p>
</div>

---

**AgenticOS** is a secure autonomous framework designed for extreme performance, deep system orchestration, and resilient multi-modal research across **Windows, macOS, and Linux**. It integrates high-scale cloud models (NVIDIA NIM, Google Gemini) and local LLMs (Ollama) with a modular ecosystem of over **180 specialized tools** to provide a proactive, self-healing operational experience.

---

## Proven in the "Crucible" Stress Test
AgenticOS recently completed a **96-task autonomous audit** of a live Windows system.
-   **Disk Hygiene**: Scanned 1M+ files on C:\ in < 3 minutes using native PowerShell optimization.
-   **Security Audit**: Successfully identified 12+ suspicious scheduled tasks and non-standard firewall ports.
-   **API Resilience**: Handled over 50+ "429 Rate Limit" errors flawlessly without a single agent crash.
-   **Resource Efficiency**: Maintained < 150MB RAM usage during complex 60-iteration tasks.

---

## System Harmony and Operator Sovereignty
AgenticOS is a high-performance autonomous tool. Its best results are achieved through clear, precise guidance from the user.
-   **Sovereignty**: The user maintains ultimate control over the system, providing the vision for the agent to execute.
-   **Collaboration**: Best practices involve starting with "Autopilot: False" to fine-tune your collaborative style with the agent.
-   **Guidance**: All operations are performed under the user's direction and oversight. See [Operator Guidance](docs/safety_guide.md) for best practices.

---

## The "Crucible" Hardened Architecture
Following a massive 96-item stress test, AgenticOS v2.1.1 has been hardened for real-world production environments. It solves the core bottlenecks of traditional agents:
-   **No-Lag Terminal UI**: Block-level rendering removes the character-by-character "typewriter lag."
-   **Rate-Limit Shield**: Built-in exponential backoff masks all `429 Too Many Requests` errors (implemented in `core/retry.py` as `retry_call()`).
-   **Centralized Logging**: Consistent, structured stream formatting and persistent storage (`workspace/logs/agenticos.log` or `data/logs/agenticos.log`) with a unified logger factory.
-   **Early Schema Validation**: Real-time boot diagnostics verify `config.yaml` layers and halt early if critical sections are missing.
-   **Native Windows COM Audio**: C# code dynamically compiled via PowerShell provides native, dependency-free volume controls.
-   **Fast-Path IO & Checkguards**: Native PowerShell scanning is 20x faster than Python's `rglob`, wrapped in strict tool checkguards (e.g. `shutil.which` warnings) on Linux.
-   **OS-Level Desktop Accessibility**: AppleScript accessibility control (AXMinimized / AXZoomed) and recursive window queries for scriptable Cocoa & non-scriptable macOS applications.
-   **Zone-Based Security**: Hardware-level path guardrails protect critical system folders.
-   **Environment Portability**: 100% configuration-driven logic with zero hardcoded paths or URLs.
-   **Resilient Testing**: Comprehensive `pytest` suite with 347 passed tests ensuring 100% deterministic tool behavior.

---

## Documentation Center

Explore the full AgenticOS manual for deep technical insights:

*   [**Documentation Catalog**](docs/CATALOG.md): Canonical index of all Markdown docs in this repository.

### Getting Started and Architecture
*   [**Setup Guide**](docs/setup_guide.md): Step-by-step instructions for new users.
*   [**System Architecture**](docs/architecture.md): Deep dive into the Orchestrator and Memory loops.
*   [**Visual Index & Flowcharts**](docs/visual_index.md): Central hub for all architectural diagrams.
*   [**Case Studies & Results**](docs/case_studies.md): Real-world proof from the 96-task "Crucible" test.
*   [**Autonomous Test Suite**](docs/testing_guide.md): Guide to our high-coverage testing framework and tasks.
*   [**Evaluation Harness**](docs/evaluation_harness.md): How to run stress tests and read session logs.
*   [**System Requirements**](docs/system_requirements.md): Hardware and software prerequisites.
*   [**Deployment Scenarios**](docs/deployment_scenarios.md): Specific "Recipes" for different use cases.
*   [**Version History**](docs/version_history.md): Technical evolution from v1.0 to v2.0.0.
*   [**Runtime Configuration**](docs/runtime_configuration.md): Exhaustive guide to `config.yaml`.

### Developer and Tooling
*   [**Developer Onboarding**](docs/developer_onboarding.md): Guide for contributing to the core engine.
*   [**Contributor Guide**](docs/contributor_guide.md): Comprehensive guide on setting up, coding standards, and testing.
*   [**Tool Development Guide**](docs/tool_development.md): Write your own plugins and optimize performance.
*   [**API & Tool Reference**](docs/api_reference.md): Overview of the 180 tools in the registry.
*   [**Autonomous Operations**](docs/autonomous_operations.md): How the "Agent Brain" plans and self-heals.
*   [**Prompt Engineering Guide**](docs/prompt_engineering_guide.md): Best practices for task optimization.

### Security and Performance
*   [**Security Guardrails**](docs/security_guardrails.md): PathGuard, HITM, and System Protection.
*   [**Privacy & Data Policy**](docs/privacy_data_policy.md): Data residency and "Zero-Cloud" configuration.
*   [**Performance Optimization**](docs/performance_optimization.md): Typewriter fixes and Fast-Disk strategies.
*   [**Troubleshooting Guide**](docs/troubleshooting.md): Common errors, 429s, and fixes.

### Special Capabilities
*   [**Web Automation & Browser**](docs/web_automation.md): Playwright, Scrapers, and Smart Downloads.
*   [**Model Integration**](docs/model_integration.md): Configuring Ollama, Nvidia, and Cloud providers.
*   [**User Interface (UX)**](docs/user_interface.md): Terminal aesthetics, colors, and notifications.

---

## Core Security Features

-   **Zone-Based Guardrails**: Four security zones (Green, Yellow, Red, Blue/Read-Only) that can be switched dynamically at runtime using the `/zone` command to balance safety and autonomy.
-   **Command Validation**: Advanced regex blocking for dangerous patterns like `rm -rf`, `format`, or `net user`.
-   **Audit Traceability**: Every thought, action, and tool output is mirrored in `evaluation_output.txt` and recorded in a persistent SQLite audit log.

---

## High-Speed Capabilities

-   **Self-Evolution**: The agent can autonomously identify missing capabilities, `pip install` libraries, and generate new tool plugins at runtime.
-   **Typewriter Optimization**: Optimized rendering engine ensures 100% CPU focus on the task, not the terminal.
-   **Native Dispatch**: High-load tasks (Disk Audits, Registry Scans) are delegated to high-speed PowerShell pipelines.

---

## Quick Start

### 1. Installation
Run the environment setup script (this automatically initializes the virtual environment, installs dependencies, downloads Playwright chromium, registers the `agent` command globally, and sets up your credentials template).

You can run this using your code editor (e.g., VS Code) or the terminal:

#### Method A: Via VS Code Task (Recommended)
1. Open the project folder in VS Code.
2. Press `Ctrl+Shift+B` (or select **Terminal** -> **Run Build Task** / **Tasks: Run Build Task** from the Command Palette).
3. The editor will automatically run the correct setup script for your platform, bypassing all Windows execution policy restrictions!

#### Method B: Via Terminal

##### Windows (PowerShell or CMD):
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

##### macOS / Linux:
```bash
./setup.sh
```

### 2. Configuration
Open the newly created `.env` file in the project root and configure your API keys (e.g., `NVIDIA_API_KEY`, `GOOGLE_API_KEY`).

### 3. Execution
Restart your terminal and start the agent from any directory:
```powershell
agent
```

---

## Project Structure
- `core/`: The Runtime Engine, Tool Registry, Memory, and Security Guardrails.
- `tools/`: Modular library of core tools and dynamic `plugins/`.
- `config/`: Layered YAML configuration system (Endpoints, Policy, Runtime).
- `tests/`: Automated test suite for core logic and filesystem tools.
- `docs/`: Comprehensive technical documentation (20+ detailed guides).
- `workspace/`: Designated environment for task artifacts and reports.
- `data/`: Configured location for SQLite databases and JSONL audit logs. (Can also be stored in `workspace/`).

---

## License
Distributed under the Apache-2.0 License.

*AgenticOS: Hardened. Autonomous. Ready.*
