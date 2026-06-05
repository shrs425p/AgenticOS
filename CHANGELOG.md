## [2.2.0] - 2026-06-05

### Security Hardening
- **Zero-Trust AST Command Validator**: Implemented a robust, AST-like structural command validation engine using `shlex` lexical parsing. It deconstructs command strings into distinct arguments to block chaining operators (`&&`, `;`, `||`, `|`, `&`) and quote-escaped/backslash-obfuscated bypasses.
- **PowerShell Encoded Command Audit**: Extracted and audited base64-encoded PowerShell payloads recursively before execution, matching abbreviation parameters (e.g., `-e`, `-enc`, `-encodedcommand`) using prefix scanning.
- **Line-by-Line Script Validation**: Hardened shell script runner executions (`.ps1`, `.bat`, `.cmd`, `.sh`, `.bash`) by parsing script files line-by-line, stripping comments/whitespace, resolving continuation lines, and auditing each statement against the security rules.
- **Security Audits Tracking**: Integrated security warning telemetry, logging audit events with `where="security_validation"` directly inside the persistent SQLite database for forensic visibility.

### Documentation & Onboarding
- **Command Validation Reference**: Added `docs/command_validation.md` documenting the zero-trust validator, script parser, and PowerShell audits.
- **Self-Improvement Guide**: Added `docs/self_improvement.md` detailing the dreaming reflections engine, logs audits, and offline heuristics.
- **Developer Quick Start**: Added `docs/quick_start.md` containing a fast 2-minute setup, CLI run command, and standard agent workflows.
- **Core and Package Docs Update**: Synchronized `docs/security_guardrails.md`, `docs/architecture.md`, `docs/testing_guide.md`, `docs/CATALOG.md`, `core/README.md`, `tools/README.md`, and `tests/README.md`.

## [2.1.2] - 2026-06-03

### Performance Improvements
- **High-Performance Filesystem Walker**: Replaced slow `Path.rglob` traversals and native PowerShell pipelines with highly-optimized native Python DFS stack-based directory traversal (`os.scandir`). This yields a **~170x** speed improvement on drive scans (from 35.4s to 0.20s) and prevents recursion loops by automatically bypassing symlinks and NTFS junction points.
- **Optimized Hot-Reload Checks**: Refactored `_get_mtimes` inside `core/runtime.py` to exclude dependency/data directories (`venv`, `node_modules`, `workspace`, `data`, and `mock_workspace`) from the file scanning traversal. This reduces idle CPU usage and disk I/O significantly.
- **Optimized Workspace Context Scan**: Updated `_scan_workspace` inside `core/context_engine.py` to skip scanning and child-counting for heavy or system-generated directories (`.git`, `venv`, `node_modules`, `__pycache__`, caches, and data directories) during prompt assembly.

### Documentation & Verification
- **Unified Tool Count & Metrics**: Updated `docs/index.html` and other documentation files to reflect the actual registry size of **352** specialized tools (previously reported as 180+) and accurate performance benchmarks.
- **Visual Diagram Corrections**: Replaced the outdated PowerShell pipeline diagram and description in `docs/visual_index.md` with the new optimized DFS stack walker flowchart, and resolved a code fence formatting syntax error.
- **Comprehensive Unit Testing**: Verified all changes using `pytest` to ensure 100% stable, cross-platform behavior.

## [2.1.1] - 2026-05-18

### CI/CD and Workflow Hardening
- **Deleted Duplicate Workflows**: Removed [.github/workflows/auto-merge.yml](.github/workflows/auto-merge.yml) to eliminate double runner execution and optimize GitHub billing/minutes.
- **Concurrency Controls**: Added concurrency groups across all active GitHub Workflows (`ci.yml`, `bandit.yml`, `codeql.yml`, `dependency-review.yml`) to automatically cancel redundant builds on subsequent pushes.
- **Fixed Hallucinated Action Versions**:
  - Corrected broken `actions/upload-artifact@v7` (non-existent) references to `@v4` in `ci.yml` and `dependency-review.yml`.
  - Corrected broken `actions/checkout@v6` (non-existent) references to `@v4` across `bandit.yml`, `codeql.yml`, `dependency-review.yml`, and `summary.yml`.
- **Protected Security Auditing Rules**: Safeguarded essential Bandit scan command skips (`B101,B603,B602,B605,B607,B404`) and folder exclusions (`tools/terminal`) to prevent false-positive command execution alerts on agent terminal tools.
- **AI Summary Formatting**: Updated Issue/PR summarization headers from a robot prefix (representing a robot icon) to `⫸ AI Summary` in `summary.yml`.
- **CodeQL Alert Mitigation**: Resolved CodeQL Medium CWE-829 (unpinned-tag) alert by pinning `codecov/codecov-action` inside `ci.yml` to its immutable full-length commit SHA (`57e3a136b779b570ffcdbf80b3bdc90e7fab3de2`).

### Bug Fixes
- **Resilient Cache Loader**: Fixed `UnboundLocalError` in `main.py` cache root resolver where a missing `PyYAML` package in clean/isolated Python environments crashed the startup loader instead of gracefully falling back to defaults.

### Documentation and QA
- **Upgraded PR Template**: Re-engineered [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) to integrate customized checks for AgenticOS tool registry, shadow testing (`test_all_tools_shadow.py`), command execution safety, and dynamic path portability checks.

## [2.1.0] - 2026-05-17

### New Features
- Daily maintenance plugins framework for scheduled automated tasks and monitoring.

### Dependencies and Updates
- Updated `lxml` from >=4.9.0 to >=6.1.0 for improved XML/HTML parsing performance.
- Updated `numpy` from >=1.24.0 to >=2.4.5 for enhanced numerical computing capabilities.
- Updated `playwright` from >=1.43.0 to >=1.59.0 for latest browser automation features.
- Updated `ruff` from >=0.1.0 to >=0.15.13 for improved code linting and formatting.
- Updated `python-dateutil` from >=2.8.0 to >=2.9.0.post0 for better date/time handling.
- Updated `requests` from >=2.31.0 to >=2.34.2 for enhanced HTTP client stability.
- Updated `pyyaml` from >=6.0 to >=6.0.3 for improved YAML parsing security.
- Updated `groq` from >=0.4.0 to >=1.2.0 for latest Groq API client features.

### Bug Fixes
- Fix platform-specific `winreg` import crashing on Unix/Linux/macOS CI environments (resolved with dynamic `ImportError` exception handling).
- Resolve false-positive CodeQL CWE-20 Incomplete URL substring sanitization warnings in unit test assertions (`test_web_search.py`, `test_web_tools.py`, `test_web_fetch.py`).
- Automatically verify and create the tasks directory inside `workspace` if missing in `core/task_tracker.py` to prevent initialization errors.
- Silently suppress duplicate tool registration console logs in `core/tool_registry.py` to keep boot output clean.
- Fix async mock behaviors in `tests/test_web_browser.py` to properly handle `AsyncMock` context engines.

### Infrastructure and Operations
- Increase Dependabot's open pull request limit to 15 in `.github/dependabot.yml` to permit concurrent security and version updates.
- Fully align all developer guides and user manuals (`docs/user_interface.md`, `docs/tool_development.md`) to run the standard `agent` launcher globally instead of the legacy `python main.py` command.

### Maintenance and Refactors
- Add `core/retry.py` and migrate provider clients to use a centralized `retry_call()` helper for exponential backoff and jittered retries.
- Centralize `.env` loading in `main.py` (the `.env` file in the repo root is now the canonical credentials source); modules include a fallback for direct runs.
- Namespaced plugin imports under `tools.plugins.<module>` and updated `ToolRegistry` to register top-level `@tool` callables, improving hot-reload and test patchability.
- Add `core/config_types.py` types and annotate `core/runtime_config.py` for clearer config typing.
- Add `tests/test_retry.py` to cover retry behaviour.

## [2.0.1] - 2026-05-16

### New Features
- Daily maintenance plugins framework: `feat: add daily maintenance plugins and tests (#15)` (Shreyas Pawar)
  - Introduced automated maintenance task scheduler for periodic health checks and cleanup operations
  - Added comprehensive test coverage for new plugin architecture
  - Enables users to define custom maintenance routines and lifecycle hooks

## [2.0.0] - 2026-05-14

### New Features
- Fast-Path PowerShell Tooling: Replaced inefficient Python-based recursive crawlers with native PowerShell pipelines.
- Persistent SQLite Memory: Migrated session memory to a structured SQLite database.
- No-Lag UI: Optimized the terminal rendering engine to use block-level output.

### Performance Improvements
- Crucible Stress Test: Successfully completed the 96-task autonomous audit of a live Windows system.
- Disk Hygiene: Scanned 1M+ files on the system drive in < 3 minutes using native PowerShell optimization.
- Resource Efficiency: Maintained stable RAM usage (<150MB) during high-intensity 60-iteration tasks.

### Security Hardening
- Zone-Based PathGuard: Implemented a non-bypassable security layer that restricts the agent to specific filesystem zones (Green, Yellow, Red).
- Security Audit: Successfully identified 12+ suspicious scheduled tasks and non-standard firewall ports.

### Bug Fixes
- API Resilience / Exponential Backoff Shield: Handled over 50+ "429 Rate Limit" errors flawlessly without a single agent crash.
