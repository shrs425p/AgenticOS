# AgenticOS: High-Performance Autonomous Framework

<div align="center">
  <img src="media/logo.png" alt="AgenticOS Banner" width="85%">
  
  <br>

  <h3>AgenticOS is a secure, high-performance personal AI orchestration framework supporting local and cloud LLMs.</h3>

  <p>
    <a href="https://github.com/shrs425p/AgenticOS/discussions">Discussions</a> | 
    <a href="manuals/CATALOG.md">Docs Catalog</a> | 
    <a href="https://github.com/shrs425p/AgenticOS">Follow @shrs425p (Creator)</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/status-production_stable-orange?style=flat-square" alt="Status">
    <img src="https://img.shields.io/github/v/release/shrs425p/AgenticOS?style=flat-square&label=latest" alt="Latest Version">
    <img src="https://img.shields.io/badge/license-Apache_2.0-red?style=flat-square" alt="License">
    <img src="https://img.shields.io/badge/ops-179-green?style=flat-square" alt="Ops">
    <img src="https://img.shields.io/badge/tests-556_passed-brightgreen?style=flat-square" alt="Tests">
    <a href="https://codecov.io/gh/shrs425p/AgenticOS"><img src="https://codecov.io/gh/shrs425p/AgenticOS/branch/main/graph/badge.svg" alt="Coverage"></a>
  </p>
  
  <p>
    <img src="https://img.shields.io/badge/python-3.10%2B-yellow?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/platform-Windows_|_macOS_|_Linux-blue?style=flat-square" alt="Platform">
    <img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs Welcome">
    <img src="https://img.shields.io/badge/security-verified-brightgreen?style=flat-square" alt="Security">
    <img src="https://github.com/shrs425p/AgenticOS/actions/workflows/build.yml/badge.svg" alt="CI Build Status">
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

**AgenticOS** is a secure, personal AI orchestration framework designed for deep system automation, workspace safety, and resilient multi-modal research across **Windows, macOS, and Linux**. It integrates high-scale cloud models (NVIDIA NIM, Google Gemini) and local LLMs (Ollama) with a modular ecosystem of over **179 specialized ops** to provide a proactive, self-healing operational experience.

---

## â—† Core Pillars & Unique Capabilities

| â—† Zero-Trust Guardrails | â—† High-Speed Native Engine | â—† Orchestrated Autonomy |
| :--- | :--- | :--- |
| **AST Command Validator**<br>Deconstructs command syntax tree-by-tree to intercept obfuscation, chains (`&&`, `;`), and malicious patterns. | **Native DFS Traversal**<br>Scans over 1,000,000 files in under 30 seconds using optimized native Python directory streams. | **Self-Healing Loop**<br>Autonomously detects missing libraries, auto-installs packages (`pip`), and patches runtime exceptions. |
| **PathGuard Security Zones**<br>Restricts filesystem modifications to designated workspaces using strict path boundary checkguards. | **Zero Typewriter Lag**<br>Engineered with block-level terminal rendering to focus 100% CPU on task execution. | **Dynamic Tool Registry**<br>Hot-reloads and validates new capabilities, custom scripts, and plugins on-the-fly. |
| **Zone-Based Sandbox**<br>Adjust safety parameters dynamically at runtime (Green/Yellow/Red/Blue/Black) using `/zone`. | **Rate-Limit Shielding**<br>Handles API throttling (HTTP 429) gracefully with custom backoff and retry pacing. | **Cross-Platform Integration**<br>Native system hooks (COM volume controls, AppleScript AX access, bash wrappers). |

---

## â—† Autonomous Self-Evolution & Dynamic Tool Creation

Unlike static orchestrators limited to pre-configured integrations, AgenticOS can expand its own capabilities at runtime:
*   **Dynamic Code Generation**: When faced with a task requiring missing dependencies or Ops (e.g., parsing a new file format, computing specific metrics), the agent autonomously writes a Python plugin conforming to the system's plugin decorators.
*   **Automated Validation & Testing**: Before reloading, the agent runs linting checks and builds temporary unit tests to verify that the newly generated plugin behaves deterministically.
*   **Hot-Reload Registry**: Registers and loads the verified plugin dynamically into the running execution loop without requiring a restart or interrupting active workflows.
*   **Self-Healing Loop**: If execution fails, the agent parses the stack trace, adjusts the code, re-runs tests, and heals the plugin programmatically.

---

## â—† Deep OS Automation & Low-Level Host Control

AgenticOS interfaces directly with the host system using native APIs and low-level script automation:
*   **OS Accessibility Integration**: Controls AppleScript accessibility (AXMinimized, AXZoomed, AXFrame) to query UI element titles and layouts in macOS scriptable/non-scriptable Cocoa applications.
*   **Native Windows COM Control**: Compiles and executes C# code on-the-fly via PowerShell to interface with the Win32 COM APIs for native, dependency-free hardware control (e.g., volume management, network interfaces).
*   **System Telemetry and Diagnostics**: Inspects active registry keys, queries local firewall configurations (flagging rules permitting inbound traffic on non-standard ports), audits scheduled system tasks, and parses local user account metrics.

---

## â—† Headless Browser Scraping & Dynamic Web Intelligence

AgenticOS drives a dynamic browser engine to parse modern JavaScript-rendered web apps:
*   **Playwright Automation**: Launches sandboxed Chromium browsers to scrape content, fill interactive forms, capture element screenshots, download files, and bypass basic scraper blocklists.
*   **DNS & Security Audits**: Resolves network hosts, validates SSL certificate signatures/expiration, checks WHOIS domains registration logs, and queries security blacklist databases to evaluate URL safety.
*   **Recursive Research Loops**: Executes multi-phase search-and-synthesize cycles, using query results to refine subsequent research prompts for deep intelligence gathering.

---

## â—† Advanced Zero-Trust Security & AST-Level Sandboxing

Security is the primary constraint. The framework enforces strict boundary controls to protect the host:
*   **Abstract Syntax Tree (AST) Parsing**: Traditional regex validators are bypassed by simple quote or string variations. AgenticOS uses `shlex` to deconstruct command arguments, verifying nested quotes, variable expansions, and escaped strings.
*   **PowerShell Abbreviation & Encoded Command Defense**: Detects parameter prefix matching (e.g., `-e`, `-enc`, `-en` flags for execution) and decodes base64-encoded PowerShell commands to audit the underlying script payload before launching the subprocess.
*   **Line-by-Line Script Validation**: When running shell scripts (`.sh`, `.bash`, `.ps1`, `.bat`, `.cmd`), the agent reads the file content, filters syntax-specific comments, handles line continuation characters, and validates every single instruction block against safety rules.
*   **PathGuard Boundary Isolation**: Restricts system writes, preventing access to critical OS folders, active system configurations, or local Git repositories.

---

## â—† Under-the-Hood Resilience & Memory Architecture

*   **SQLite-Backed Context Memory**: Persists short-term plans, model thought patterns, actions, and observations in a structured SQLite database to ensure the agent remembers its progress even across session restarts.
*   **Rate-Limit Shielding**: Jittered exponential backoff retries (`retry_call()`) mask all cloud model API limit (HTTP 429) spikes, maintaining task stability under high network volumes.
*   **Optimized Native Dispatch**: Scans directories and counts millions of files in seconds using native DFS traversals, bypassing the CPU overhead of spawning subprocess commands.

---

## â—† Interactive Documentation Center

Our comprehensive technical library covers configurations, architecture, and extension guides:

### â—† Getting Started
*   [**Setup Guide**](manuals/setup.md): Native installer walkthrough for Windows, macOS, and Linux.
*   [**System Requirements**](manuals/requirements.md): Hardware, operating system, and runtime configurations.
*   [**Runtime Configuration**](manuals/runtime.md): Complete guide to YAML configuration layering and `.env` setups.

### â—† System Architecture
*   [**Architecture Deep-Dive**](manuals/architecture.md): Understand the Thought-Action-Observation orchestrator loop.
*   [**Visual Index & Flowcharts**](manuals/visual.md): Conceptual diagrams mapping execution pipelines.
*   [**Security Guardrails**](manuals/guard.md): Details on PathGuard, Sandboxing, and AST Command Validators.
*   [**Version History**](manuals/history.md): Technical evolution of AgenticOS features and performance benchmarks.

### â—† Developer & Extensions
*   [**Contributor Guide**](manuals/contribute.md): Branch conventions, coding standards, type hints, and PR processes.
*   [**Tool Development**](manuals/tools.md): Write your own plugins and register them with the dynamic ToolRegistry.
*   [**API & Tool Reference**](manuals/api.md): Functional reference catalog for the 179 registered ops.
*   [**Autonomous Operations**](manuals/autonomy.md): Learn how the "Agent Brain" designs and executes actions.

---

## â—† Quick Start & Setup
For installation, configuration, project structure, and usage examples, refer to the [Setup Guide](manuals/setup.md).

## â—† Contributing
For guidelines on coding standards, testing, and pull requests, refer to the [Contributor Guide](manuals/contribute.md).

## â—† License
Distributed under the Apache-2.0 License.

*AgenticOS: Hardened. Autonomous. Ready.*