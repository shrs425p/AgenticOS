# AgenticOS: High-Performance Autonomous Framework

<div align="center">
  <img src="assets/AgenticOS-Logo.png" alt="AgenticOS Banner" width="85%">
  
  <br>

  <h3>AgenticOS is a secure, high-performance personal AI orchestration framework supporting local and cloud LLMs.</h3>

  <p>
    <a href="https://github.com/shrs425p/AgenticOS/discussions">Discussions</a> | 
    <a href="docs/CATALOG.md">Docs Catalog</a> | 
    <a href="https://github.com/shrs425p/AgenticOS">Follow @shrs425p (Creator)</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/status-production_stable-orange?style=flat-square" alt="Status">
    <img src="https://img.shields.io/badge/latest-v2.1.2-blue?style=flat-square" alt="Latest Version">
    <img src="https://img.shields.io/badge/license-Apache_2.0-red?style=flat-square" alt="License">
    <img src="https://img.shields.io/badge/tools-350+-green?style=flat-square" alt="Tools">
    <img src="https://img.shields.io/badge/tests-445_passed-brightgreen?style=flat-square" alt="Tests">
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

**AgenticOS** is a secure, personal AI orchestration framework designed for deep system automation, workspace safety, and resilient multi-modal research across **Windows, macOS, and Linux**. It integrates high-scale cloud models (NVIDIA NIM, Google Gemini) and local LLMs (Ollama) with a modular ecosystem of over **350 specialized tools** to provide a proactive, self-healing operational experience.

---

## ⚡ Core Pillars & Unique Capabilities

| 🔒 Zero-Trust Guardrails | 🚀 High-Speed Native Engine | 🧠 Orchestrated Autonomy |
| :--- | :--- | :--- |
| **AST Command Validator**<br>Deconstructs command syntax tree-by-tree to intercept obfuscation, chains (`&&`, `;`), and malicious patterns. | **Native DFS Traversal**<br>Scans over 1,000,000 files in under 30 seconds using optimized native Python directory streams. | **Self-Healing Loop**<br>Autonomously detects missing libraries, auto-installs packages (`pip`), and patches runtime exceptions. |
| **PathGuard Security Zones**<br>Restricts filesystem modifications to designated workspaces using strict path boundary checkguards. | **Zero Typewriter Lag**<br>Engineered with block-level terminal rendering to focus 100% CPU on task execution. | **Dynamic Tool Registry**<br>Hot-reloads and validates new capabilities, custom scripts, and plugins on-the-fly. |
| **Zone-Based Sandbox**<br>Adjust safety parameters dynamically at runtime (Green/Yellow/Red/Read-Only) using `/zone`. | **Rate-Limit Shielding**<br>Handles API throttling (HTTP 429) gracefully with custom backoff and retry pacing. | **Cross-Platform Integration**<br>Native system hooks (COM volume controls, AppleScript AX access, bash wrappers). |

---

## 🔒 Advanced Zero-Trust Security

At the heart of AgenticOS is a zero-trust model designed to execute complex operations safely on host systems:

*   **Abstract Syntax Tree (AST) Validation**: Standard command regexes can be bypassed. AgenticOS tokenizes and parses shell commands at a structural level using `shlex`, validating multi-word arguments, quote/tick nested strings, and PowerShell abbreviations.
*   **Encrypted & Obfuscated Command Defense**: Decodes base64-encoded command wrappers (e.g., PowerShell `-EncodedCommand` flags) and checks the payload before execution.
*   **PathGuard Sandbox**: Enforces isolation zones. Any write access attempting to target system folders, user profiles, or Git configuration directories is immediately blocked unless explicit approval is granted.
*   **Structured Auditing**: Keeps a queryable, persistent SQLite audit log recording every thought, command execution, and tool input/output for forensics.

---

## 🚀 Native Performance & System Benchmarks

AgenticOS bypasses slow shell spawning and system overheads to deliver high-performance automation:
*   **Fast-Disk IO**: Replaces generic Python recursive globbing (`rglob`) with an optimized `os.scandir` depth-first search (DFS) traversal, delivering **100x speedups** on standard HDDs/SSDs.
*   **Robust Network Resiliency**: Built-in exponential backoff retries (`retry_call()`) mask all cloud model rate limits to preserve execution state across long runs.
*   **Minimal Footprint**: Operates with less than **150MB of RAM** usage, even during complex, high-iteration loops.

---

## 📖 Interactive Documentation Center

Our comprehensive technical library covers everything you need to configure, run, and scale AgenticOS:

### 🏁 Getting Started
*   [**Setup Guide**](docs/setup_guide.md): Native installer walkthrough for Windows, macOS, and Linux.
*   [**System Requirements**](docs/system_requirements.md): Hardware, operating system, and runtime configurations.
*   [**Runtime Configuration**](docs/runtime_configuration.md): Complete guide to YAML configuration layering and `.env` setups.

### 📐 System Architecture
*   [**Architecture Deep-Dive**](docs/architecture.md): Understand the Thought-Action-Observation orchestrator loop.
*   [**Visual Index & Flowcharts**](docs/visual_index.md): Conceptual diagrams mapping execution pipelines.
*   [**Security Guardrails**](docs/security_guardrails.md): Details on PathGuard, Sandboxing, and AST Command Validators.
*   [**Version History**](docs/version_history.md): Technical evolution of AgenticOS features and performance benchmarks.

### 🛠️ Developer & Extensions
*   [**Contributor Guide**](docs/contributor_guide.md): Branch conventions, coding standards, type hints, and PR processes.
*   [**Tool Development**](docs/tool_development.md): Write your own plugins and register them with the dynamic ToolRegistry.
*   [**API & Tool Reference**](docs/api_reference.md): Functional reference catalog for the 350+ built-in system tools.
*   [**Autonomous Operations**](docs/autonomous_operations.md): Learn how the "Agent Brain" designs and executes actions.

---

## 🏁 Quick Start & Setup
For installation, configuration, project structure, and usage examples, refer to the [Setup Guide](docs/setup_guide.md).

## 🤝 Contributing
For guidelines on coding standards, testing, and pull requests, refer to the [Contributor Guide](docs/contributor_guide.md).

## 📄 License
Distributed under the Apache-2.0 License.

*AgenticOS: Hardened. Autonomous. Ready.*
