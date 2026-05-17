# AgenticOS Test Suite

This directory contains the comprehensive, automated test suite for AgenticOS. It features over 550+ unit and integration tests covering the core loop, model clients, security guardrails, filesystem mixins, terminal utilities, and custom plugin architectures.

---

## Test Directory Structure

```text
tests/
├── auto/                # Auto-generated verification tests for automated suites
├── integration/         # Multi-system end-to-end integration and flow tests
├── test_core.py         # Foundational core engine and framework sanity checks
├── test_runtime.py      # Detailed test coverage for the core runtime loop
├── test_guardrails.py   # Enforces security path bounds and command validation
├── test_model_clients.py# Mocks and assertions for Gemini, OpenAI, Groq, and Nvidia API clients
├── test_web_*.py        # Web scrapers, search engines, and browser tool mock assertions
├── test_fs_*.py         # High-speed filesystem mutations, bulk actions, and search utilities
└── test_terminal_*.py   # Native OS, shell, audio, and keyboard input wrappers
```

---

## Standard Execution

To run the full test suite locally within the clean workspace, execute the following command:

```powershell
.\venv\Scripts\pytest tests/
```

### Running Individual Test Files

Executing test files directly via `python tests/test_file.py` will fail with a `ModuleNotFoundError` because Python does not automatically append the project root directory to the module path (`sys.path`).

The professional standard is to invoke individual test suites through the `pytest` runner:

```powershell
.\venv\Scripts\pytest tests/test_file_manager.py -o addopts=""
```

---

## Mocking & Extensibility Guidelines

When adding or modifying capabilities within the test suite, adhere to the following framework conventions:

### 1. The Double-Import Mock Leak Protection
In dynamically extensible Python frameworks, dynamically importing and executing modules using import libraries can sometimes override cached module pointers in `sys.modules`. 
- **The Issue**: If a test collects the module *before* the runtime re-loads it dynamically, standard `@patch` statements targeting `sys.modules` will mock the fresh instance, leaving the pre-cached instance untouched and unmocked.
- **The Solution**: All dynamic tool registration engines reuse pre-loaded modules in `sys.modules` directly, ensuring mock patches targeting paths (such as `tools.plugins.research_loop.WebTools`) bind correctly.

### 2. Async Mocks
When testing async-dependent components (e.g. browser automation in `test_web_browser.py`), ensure `AsyncMock` is used to mock return contexts instead of blocking standard mocks:

```python
from unittest.mock import AsyncMock, patch

@patch("core.tool_registry.ToolRegistry")
def test_async_browser_capability(mock_registry):
    mock_browser = AsyncMock()
    # Configure mock behavior for async execution
```
