# AgenticOS: Version History and Evolution

This document tracks the technical evolution of AgenticOS from its initial prototype to the current secure framework. Each major version represents a significant leap in safety, performance, and autonomous reasoning.

---

---

## v2.1.1 - The "Bulletproof Cross-Platform Hardened" Edition (Current)
*Release Date: 2026-05-18*

The v2.1.1 release establishes seamless, robust, low-level OS integrations across Windows 11, macOS Darwin, and modern Linux GNOME environments.

### Key Innovations:
1.  **C# Native Audio Endpoint COM Interoperability (Windows)**: Replaced external nircmd helpers inside `volume_set` with direct C# COM interfaces (`IAudioEndpointVolume`, `IMMDevice`, `IMMDeviceEnumerator`) dynamically compiled via PowerShell.
2.  **CIM-Based Systems Telemetry (Windows)**: Modernized `system.py` diagnostics by replacing deprecated `wmic` utilities with modern, universal PowerShell Common Information Model (`Get-CimInstance`) queries mapping `Win32_Processor` and `Win32_OperatingSystem`.
3.  **Linux Tool Checkguards**: Integrated `shutil.which` dependency checks inside `take_screenshot` (scrot, gnome-screenshot, import) and keyboard routines, providing clean installation advice instead of raw subprocess failures.
4.  **OS-Level macOS Window Control (AXMinimized / AXZoomed)**: Upgraded `minimize_app` and `maximize_app` to query System Events and manipulate standard macOS accessibility attributes, ensuring compatibility with scriptable Cocoa and non-scriptable web/Electron applications (Chrome, VS Code, Spotify).
5.  **Recursive macOS Window title query in `list_windows`**: Upgraded macOS Darwin window listings to dynamically crawl active desktop processes via AppleScript and extract their true visible window names.
6.  **Dual GNOME picture-uri Wallpapers (Linux)**: Upgraded wallpaper configurations to simultaneously write org.gnome.desktop.background `picture-uri` and `picture-uri-dark` keys, preventing silent theme mismatches.
7.  **Keystroke AppleScript Fallback**: Hardened mac keyboard emulation with a safe keystroke fallback pathway instead of uncompilable reflection syntax.
8.  **Centralized Logger Factory**: Formulated `core/logger.py` to route all output to standardized console formatters and persistent file stores (`data/logs/agenticos.log`).
9.  **Early Configuration Schema Validator**: Integrated startup schema validation on the fully-merged configuration dictionary, outputting early warnings and halting startup on critical missing keys.

---

## v2.0.0 - The "Portable and Resilient" Edition
*Release Date: 2026-05-15*

### Key Innovations:
1.  **Layered Configuration System**: Migrated from a single `config.yaml` to a multi-file configuration directory (`config/`). This enables clean separation of security policy, service endpoints, and system heuristics.
2.  **Comprehensive Testing Suite**: Launched a `pytest`-based framework with 40+ unit tests covering core logic, filesystem tools, and security guardrails.
3.  **Zero-Hardcoding Policy**: Fully refactored the codebase to eliminate absolute paths and hardcoded URLs, ensuring 100% environment portability.
4.  **Secret Redaction Engine**: Implemented an automated regex-based masking system that protects API keys and PII in all logs and persistent memory.
5.  **CI/CD Automation**: Integrated GitHub Actions to enforce testing and coverage standards on every code submission.

---

## v2.0 - The "Hardened" Edition
*Release Date: 2026-05-14*

The v2.0 release focuses on transforming AgenticOS into a resilient system capable of handling enterprise-scale tasks with minimal resource impact and maximum security.

### Key Innovations:
1.  **Fast-Path PowerShell Tooling**: Replaced inefficient Python-based recursive crawlers with native PowerShell pipelines. This reduced drive-audit times from 30+ minutes to <3 minutes.
2.  **Zone-Based PathGuard**: Implemented a non-bypassable security layer that restricts the agent to specific filesystem zones (Green, Yellow, Red).
3.  **Exponential Backoff Shield**: Integrated a resilient API client that autonomously handles `429 Too Many Requests` errors using an exponential retry logic.
4.  **No-Lag UI**: Optimized the terminal rendering engine to use block-level output, eliminating the CPU thrashing caused by the character-by-character "typewriter" effect.
5.  **Persistent SQLite Memory**: Migrated session memory to a structured SQLite database for faster querying and long-term task persistence.

### Stress Test Results:
-   Successfully completed the **96-task Crucible Suite** with a 100% success rate on system-level diagnostics.
-   Maintained stable RAM usage (<150MB) during high-intensity 60-iteration tasks.

---

## v1.5 - The Modular Refactor
*Release Date: 2026-04-20*

This version moved the system away from a single-file script toward a modular, scalable architecture.

### Key Innovations:
1.  **Modular Tool Registry**: Isolated tool logic into separate mixin classes, allowing for easier extension and testing.
2.  **Playwright Integration**: Added the first version of the browser automation suite, enabling the agent to interact with Single-Page Applications (SPAs).
3.  **YAML Configuration**: Moved all agent settings from hardcoded constants to a centralized `config.yaml`.
4.  **Type-Hinted Tooling**: Implemented strict Python type hinting for all tools, enabling the model to understand argument schemas automatically.

---

## v1.0 - The Autonomous Prototype
*Release Date: 2026-03-05*

The initial proof-of-concept for an agent that could interact directly with the Windows Operating System.

### Key Innovations:
1.  **Cortex Reasoning Loop**: The first implementation of the "Think-Action-Observation" cycle.
2.  **Basic Filesystem Tools**: Standard read/write/delete capabilities using Python's `os` and `pathlib` libraries.
3.  **Terminal Executor**: A simple bridge that allowed the agent to run CMD commands.
4.  **Local Memory**: A simple JSON file used to track the agent's short-term history.

### Lessons Learned:
-   Python-based recursive walkers were identified as a major bottleneck for large drives.
-   Direct model access to the root directory was deemed too high-risk for autonomous use.

---

## The Future Roadmap (v3.0 and Beyond)

The next phase of AgenticOS development will focus on multi-agent collaboration and advanced visual reasoning.

-   **Multi-Agent Orchestration**: Allowing multiple agents to share a single "Blackboard" and work on sub-tasks in parallel.
-   **Native Visual Input**: Integrating OCR and Computer Vision directly into the terminal so the agent can "see" active application windows.
-   **Kernel-Level Guardrails**: Exploring lower-level system hooks to provide even more granular control over process execution.

---

*Last Updated: 2026-05-14*
*Status: v2.0 Hardened*
