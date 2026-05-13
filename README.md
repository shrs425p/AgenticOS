# AgenticOS — High-Performance Autonomous Framework [SECURE][LAUNCH]
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AgenticOS** is a secure autonomous operating system designed for extreme performance, deep system orchestration, and resilient multi-modal research. It integrates high-scale cloud models (NVIDIA NIM, Google Gemini) and local LLMs (Ollama) with a modular ecosystem of over **350+ specialized tools** to provide a proactive, self-healing operational experience.

---

## [PROVEN] Proven in the "Crucible" Stress Test
AgenticOS recently completed a **96-task autonomous audit** of a live Windows system.
-   **Disk Hygiene**: Scanned 1M+ files on C:\ in < 3 minutes using native PowerShell optimization.
-   **Security Audit**: Successfully identified 12+ suspicious scheduled tasks and non-standard firewall ports.
-   **API Resilience**: Handled over 50+ "429 Rate Limit" errors flawlessly without a single agent crash.
-   **Resource Efficiency**: Maintained < 150MB RAM usage during complex 60-iteration tasks.

---

## [SECURE] System Harmony & Operator Sovereignty
AgenticOS is a high-performance autonomous tool. Its best results are achieved through clear, precise guidance from the user.
-   **Sovereignty**: The user maintains ultimate control over the system, providing the vision for the agent to execute.
-   **Collaboration**: Best practices involve starting with "Autopilot: False" to fine-tune your collaborative style with the agent.
-   **Guidance**: All operations are performed under the user's direction and oversight. See [Operator Guidance](docs/safety_guide.md) for best practices.

---

## [ARCH] The "Crucible" Hardened Architecture
Following a massive 96-item stress test, AgenticOS v2.0 has been hardened for real-world production environments. It solves the core bottlenecks of traditional agents:
-   **No-Lag Terminal UI**: Block-level rendering removes the character-by-character "typewriter lag."
-   **Rate-Limit Shield**: Built-in exponential backoff masks all `429 Too Many Requests` errors.
-   **Fast-Path IO**: Native PowerShell-optimized scanning is 20x faster than Python's `rglob`.
-   **Zone-Based Security**: Hardware-level path guardrails protect critical system folders.

---

## 📚 Documentation Center

Explore the full AgenticOS manual for deep technical insights:

### [LAUNCH] Getting Started & Architecture
*   [**Setup Guide**](docs/setup_guide.md): Step-by-step instructions for new users.
*   [**System Architecture**](docs/architecture.md): Deep dive into the Orchestrator and Memory loops.
*   [**Visual Index & Flowcharts**](docs/visual_index.md): Central hub for all architectural diagrams.
*   [**Case Studies & Results**](docs/case_studies.md): Real-world proof from the 96-task "Crucible" test.
*   [**Autonomous Test Suite**](docs/test_suite.md): Full index of nearly 100 tasks you can run.
*   [**Evaluation Harness**](docs/evaluation_harness.md): How to run stress tests and read session logs.
*   [**System Requirements**](docs/system_requirements.md): Hardware and software prerequisites.
*   [**Deployment Scenarios**](docs/deployment_scenarios.md): Specific "Recipes" for different use cases.
*   [**Version History**](docs/version_history.md): Technical evolution from v1.0 to v2.0.
*   [**Runtime Configuration**](docs/runtime_configuration.md): Exhaustive guide to `config.yaml`.

### [TOOL] Developer & Tooling
*   [**Developer Onboarding**](docs/developer_onboarding.md): Guide for contributing to the core engine.
*   [**Tool Development Guide**](docs/tool_development.md): Write your own plugins and optimize performance.
*   [**API & Tool Reference**](docs/api_reference.md): Overview of the 300+ tools in the registry.
*   [**Autonomous Operations**](docs/autonomous_operations.md): How the "Agent Brain" plans and self-heals.
*   [**Prompt Engineering Guide**](docs/prompt_engineering_guide.md): Best practices for task optimization.

### [SECURE] Security & Performance
*   [**Security Guardrails**](docs/security_guardrails.md): PathGuard, HITM, and System Protection.
*   [**Privacy & Data Policy**](docs/privacy_data_policy.md): Data residency and "Zero-Cloud" configuration.
*   [**Performance Optimization**](docs/performance_optimization.md): Typewriter fixes and Fast-Disk strategies.
*   [**Troubleshooting Guide**](docs/troubleshooting.md): Common errors, 429s, and fixes.

### [WEB] Special Capabilities
*   [**Web Automation & Browser**](docs/web_automation.md): Playwright, Scrapers, and Smart Downloads.
*   [**Model Integration**](docs/model_integration.md): Configuring Ollama, Nvidia, and Cloud providers.
*   [**User Interface (UX)**](docs/user_interface.md): Terminal aesthetics, colors, and notifications.

---

## [SECURE] Core Security Features

-   **Zone-Based Guardrails**: Restrict the agent to `workspace/` (Green Zone) while enforcing Human-in-the-Middle (HITM) for user folders (Yellow Zone) and blocking system paths (Red Zone).
-   **Command Validation**: Advanced regex blocking for dangerous patterns like `rm -rf`, `format`, or `net user`.
-   **Audit Traceability**: Every thought, action, and tool output is mirrored in `evaluation_output.txt` and recorded in a persistent SQLite audit log.

---

## [FAST] High-Speed Capabilities

-   **Self-Evolution**: The agent can autonomously identify missing capabilities, `pip install` libraries, and generate new tool plugins at runtime.
-   **Typewriter Optimization**: Optimized rendering engine ensures 100% CPU focus on the task, not the terminal.
-   **Native Dispatch**: High-load tasks (Disk Audits, Registry Scans) are delegated to high-speed PowerShell pipelines.

---

## [TOOL] Quick Start

### 1. Installation
```powershell
pip install -r requirements.txt
playwright install chromium
```

### 2. Configuration
Edit `config.yaml` to set your default provider (Ollama or Nvidia). Add your API keys to a `.env` file.

### 3. Execution
```powershell
python main.py
```

---

## [FILE] Project Structure
- `core/`: The Runtime Engine, Tool Registry, Memory, and Security Guardrails.
- `tools/`: Modular library of core tools and dynamic `plugins/`.
- `docs/`: Comprehensive technical documentation (10+ detailed guides).
- `workspace/`: Designated environment for task artifacts and reports.
- `data/`: Persistent session memory (SQLite) and audit logs.

---

## [DOC] License
Distributed under the MIT License.

*AgenticOS: Hardened. Autonomous. Ready.*
