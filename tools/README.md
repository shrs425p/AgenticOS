# AgenticOS Tools Framework

This directory houses the modular library of core tools, operating system bindings, and dynamically-loaded plugins that empower the AgenticOS agent with system and web capabilities.

---

## Architecture Overview

AgenticOS uses a unified tool model where capabilities are structured as stateless mixin classes or self-contained function registries. These tools are systematically exposed to the AI model through a strict validation layer and security guardrails.

The tool directory is divided into specialized directories and modules:

```text
tools/
├── filesystem/          # Native and optimized file manipulation utilities
├── terminal/            # Operating system, process, and administrative shells
├── web/                 # Web browsing, scraping, API mixins, and search tools
├── plugins/             # Dynamically loaded third-party custom extension tools
├── desktop_notifications.py  # System tray balloon and standard desktop notification integration
├── ocr_tools.py         # Optical Character Recognition for screenshots and images
├── screen_tools.py      # Screen capture, mouse emulation, and layout analysis
└── system_tools.py      # Core CPU, RAM, and diagnostic resource trackers
```

---

## Component Directories

### 1. Filesystem (`tools/filesystem/`)
Provides atomic, safe, and high-performance operations for traversing and mutating the workspace.
- **Read & Write**: Optimized file-reading with automated chunking to prevent memory issues.
- **Bulk Operations**: Safe directory-wide file edits, deletions, and moves.
- **Fast-Path IO**: Incorporates optimized PowerShell scanning that is up to 20x faster than traditional recursive Python lookups.

### 2. Terminal (`tools/terminal/`)
Facilitates native interaction with the host operating system.
- **Subsystem Execution**: Safe execution of standard CMD and PowerShell scripts.
- **Process Orchestration**: Process listing, priority adjustment, and suspension/termination.
- **Audit Tooling**: Active port scanners, firewall rules query managers, and scheduled task creators.

### 3. Web & Browser (`tools/web/`)
Connects the agent to web-based intelligence and interactive environments.
- **Smart Fetch & Scrape**: Downloads raw page content, parses REST APIs, and extracts readable text by stripping HTML boilerplate.
- **Browser Automation**: Playwright-driven browser controller for interactive sessions, screenshots, and visual page verification.
- **Session Management**: Reuses HTTP connection pools with custom headers and user-agents to prevent transport-layer failures.

### 4. Custom Plugins (`tools/plugins/`)
A dynamic extension directory that allows AgenticOS to expand its capabilities at runtime.
- **Self-Evolution**: The agent can autonomously generate, register, and execute new `.py` tool plugins inside this directory as needed.
- **Hot-Reloading**: The `ToolRegistry` monitors this directory to register new `@tool`-decorated callables dynamically without requiring a restart.

---

## Advanced Capabilities & Custom Plugins

AgenticOS includes newly added high-performance tools and plugins:

### ◆ System Telemetry & Health Tracker (`tools/system_tools.py`)
- **`get_system_telemetry`**: Retrieves real-time CPU percentages, physical and logical core structures, virtual memory capacities, root disk partition details, and active network bandwidth sent/received bytes.

### ◆ Dynamic Plugin Library (`tools/plugins/`)
- **`diff_summarizer`**: Computes text deltas using native diff libraries and compiles a plain-English, line-level modification summary.
- **`url_safety_check`**: Establishes peer SSL connections to cryptographically verify certificates, queries root registrars on Port 43 via raw sockets for WHOIS details, and rates domain threat risk.
- **`os_sandbox_auditor`**: Scans the host PATH to discover installed interpreters and compilers (`Node.js`, `Python`, `Git`, `Go`, `Rust`) and reports active GUI desktop window titles.
- **`sys_package_installer`**: Provides unified cross-platform system package installation, mapping abstract requests to `winget`, `choco`, `brew`, `apt`, `dnf`, or `pacman` autonomously.
- **`code_complexity`**: Installs `radon` dynamically on-demand, parses target Python files into Abstract Syntax Trees, and generates a ranked cyclomatic complexity report.

---

## Tool Category Summary

| Component / Path | Primary Purpose | Category |
| :--- | :--- | :--- |
| `tools/filesystem/` | Atomic file reads, writes, mutations, and bulk archives | Files |
| `tools/terminal/` | Administrative tasks, process lists, and firewall audits | Terminal |
| `tools/web/` | Web search, Playwright automation, and API fetch Mixins | Web |
| `tools/plugins/` | Third-party extension hooks and self-healed dynamic code | Plugins |
| `ocr_tools.py` | Image text extraction and screen OCR analysis | Media |
| `screen_tools.py` | Display tracking, mouse control, and screenshot takers | Media |
| `system_tools.py` | Resource, process handle, hardware telemetry, and systems trackers | System |

---

## Development Guidelines

To contribute a new capability or custom plugin to AgenticOS, follow these architectural rules:

1. **Category Assignment**: Ensure the tool belongs to a structured class mixin or is placed within the `tools/plugins/` directory if it is a dynamic extension.
2. **Stateless Operations**: Tools must be stateless. Maintain system and credential state in the central `WebTools` configuration or `.env` rather than within individual tool files.
3. **Guardrail Adherence**: Respect `PathGuard` and HITM (Human-In-The-Middle) settings to ensure high-risk commands fail safely or request permission.
