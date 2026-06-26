# AgenticOS Tools Framework

This directory houses the modular library of kernel ops, operating system clidings, and dynamically-loaded plugins that empower the AgenticOS agent with system and web capabilities.

---

## Architecture Overview

AgenticOS uses a unified tool model where capabilities are structured as stateless mixin classes or self-contained function registries. These ops are systematically exposed to the AI model through a strict validation layer and security guardrails.

The tool directory is divided into specialized directories and modules:

```text
ops/
├── filesystem/          # Native and optimized file manipulation utilities
├── terminal/            # Operating system, process, and administrative shells
├── web/                 # Web browsing, scraping, API mixins, and search ops
├── plugins/             # Dynamically loaded third-party custom extension ops
├── desktop_notifications.py  # System tray balloon and standard desktop notification integration
├── ocr_ops.py         # Optical Character Recognition for screenshots and images
├── screen_ops.py      # Screen capture, mouse emulation, and layout analysis
└── system_ops.py      # Core CPU, RAM, and diagnostic resource trackers
```

---

## Component Directories

### 1. Filesystem (`ops/filesystem/`)
Provides atomic, safe, and high-performance operations for traversing and mutating the workspace.
- **Read & Write**: Optimized file-reading with automated chunking to prevent memory issues.
- **Bulk Operations**: Safe directory-wide file edits, deletions, and moves.
- **Fast-Path IO**: Incorporates optimized, stack-based Python DFS `os.scandir` scanning that is up to 170x faster than traditional recursive Python `rglob` lookups.

### 2. Terminal (`ops/terminal/`)
Facilitates native interaction with the host operating system.
- **Subsystem Execution**: Hardened execution of standard CMD, PowerShell, and bash scripts using an AST-like structural parser (`SafetyMixin`) to block shell injections, chaining, obfuscation, and base64 PowerShell commands.
- **Process Orchestration**: Process listing, priority adjustment, and suspension/termination.
- **Audit Tooling**: Active port scanners, firewall rules query managers, and scheduled task creators.

### 3. Web & Browser (`ops/web/`)
Connects the agent to web-based intelligence and interactive environments.
- **Smart Fetch & Scrape**: Downloads raw page content, parses REST APIs, and extracts readable text by stripping HTML boilerplate.
- **Browser Automation**: Playwright-driven browser controller for interactive sessions, screenshots, and visual page verification.
- **Session Management**: Reuses HTTP connection pools with custom headers and user-agents to prevent transport-layer failures.

### 4. Custom Plugins (`ops/addons/`)
A dynamic extension directory that allows AgenticOS to expand its capabilities at runtime.
- **Self-Evolution**: The agent can autonomously generate, register, and execute new `.py` tool plugins inside this directory as needed.
- **Hot-Reloading**: The `ToolRegistry` monitors this directory to register new `@tool`-decorated callables dynamically without requiring a restart.

---

## Advanced Capabilities & Custom Plugins

AgenticOS includes newly added high-performance ops and plugins:

### ◆ System Telemetry & Health Tracker (`ops/system_ops.py`)
- **`getsystemtelemetry`**: Retrieves real-time CPU percentages, physical and logical kernel structures, virtual memory capacities, root disk partition details, and active network bandwidth sent/received bytes.

### ◆ Dynamic Plugin Library (`ops/addons/`)
- **`diff_summarizer`**: Computes text deltas using native diff libraries and compiles a plain-English, line-level modification summary.
- **`urlsafetycheck`**: Establishes peer SSL connections to cryptographically verify certificates, queries root registrars on Port 43 via raw sockets for WHOIS details, and rates domain threat risk.
- **`ossandboxauditor`**: Scans the host PATH to discover installed interpreters and compilers (`Node.js`, `Python`, `Git`, `Go`, `Rust`) and reports active GUI desktop window titles.
- **`sys_package_installer`**: Provides unified cross-platform system package installation, mapping abstract requests to `winget`, `choco`, `brew`, `apt`, `dnf`, or `pacman` autonomously.
- **`codecomplexity`**: Installs `radon` dynamically on-demand, parses target Python files into Abstract Syntax Trees, and generates a ranked cyclomatic complexity report.

---

## Tool Category Summary

| Component / Path | Primary Purpose | Category |
| :--- | :--- | :--- |
| `ops/filesystem/` | Atomic file reads, writes, mutations, and bulk archives | Files |
| `ops/terminal/` | Administrative tasks, process lists, and firewall audits | Terminal |
| `ops/web/` | Web search, Playwright automation, and API fetch Mixins | Web |
| `ops/addons/` | Third-party extension hooks and self-healed dynamic code | Plugins |
| `ocr_ops.py` | Image text extraction and screen OCR analysis | Media |
| `screen_ops.py` | Display tracking, mouse control, and screenshot takers | Media |
| `system_ops.py` | Resource, process handle, hardware telemetry, and systems trackers | System |

---

## Development Guidelines

To contribute a new capability or custom plugin to AgenticOS, follow these architectural rules:

1. **Category Assignment**: Ensure the tool belongs to a structured class mixin or is placed within the `ops/addons/` directory if it is a dynamic extension.
2. **Stateless Operations**: Tools must be stateless. Maintain system and credential state in the central `WebTools` configuration or `.env` rather than within individual tool files.
3. **Guardrail Adherence**: Respect `PathGuard` and HITM (Human-In-The-Middle) settings to ensure high-risk commands fail safely or request permission.
