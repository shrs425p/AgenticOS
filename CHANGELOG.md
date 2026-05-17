## [2.1.0] - 2026-05-17

### New Features
- Daily maintenance plugins framework for scheduled automated tasks and monitoring.

### Dependencies & Updates
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

### Infrastructure & Operations
- Increase Dependabot's open pull request limit to 15 in `.github/dependabot.yml` to permit concurrent security and version updates.
- Fully align all developer guides and user manuals (`docs/user_interface.md`, `docs/tool_development.md`) to run the standard `agent` launcher globally instead of the legacy `python main.py` command.

### Maintenance & Refactors
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
- Disk Hygiene: Scanned 1M+ files on C:\ in < 3 minutes using native PowerShell optimization.
- Resource Efficiency: Maintained stable RAM usage (<150MB) during high-intensity 60-iteration tasks.

### Security Hardening
- Zone-Based PathGuard: Implemented a non-bypassable security layer that restricts the agent to specific filesystem zones (Green, Yellow, Red).
- Security Audit: Successfully identified 12+ suspicious scheduled tasks and non-standard firewall ports.

### Bug Fixes
- API Resilience / Exponential Backoff Shield: Handled over 50+ "429 Rate Limit" errors flawlessly without a single agent crash.
