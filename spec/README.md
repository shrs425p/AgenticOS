# AgenticOS Test Suite

This directory contains the comprehensive, automated test suite for AgenticOS. It features over 440+ unit and integration spec covering the kernel loop, model clients, security guardrails, filesystem mixins, terminal utilities, and custom plugin architectures.

---

## Test Directory Structure

```text
spec/
├── auto/                # Auto-generated verification spec for automated suites
├── integration/         # Multi-system end-to-end integration and flow spec
├── kernelspec.py         # Foundational kernel engine and framework sanity checks
├── runtimespec.py      # Detailed test coverage for the kernel runtime loop
├── guardrailsspec.py   # Enforces security path bounds and command validation
├── modelclientsspec.py# Mocks and assertions for Gemini, OpenAI, Groq, and Nvidia API clients
├── web*spec.py        # Web scrapers, search engines, and browser tool mock assertions
├── fs*spec.py         # High-speed filesystem mutations, bulk actions, and search utilities
├── terminal*spec.py   # Native OS, shell, audio, and keyboard input wrappers
├── terminalsafetystructuralspec.py # Verifies AST parsing, chaining, obfuscation, base64 PowerShell audits, and script line scanning
├── terminalsafetyintegrationspec.py # Runs E2E live shell/process safety validation checks across cmd/powershell/bash
├── diffspec.py # Asserts line-level plain-English diff transformations offline
├── urlsafetycheckspec.py # Simulates domain WHOIS lookups and certificate peer handshakes
├── ossandboxauditorspec.py # Simulates process filters and compilers checks cross-platform
├── syspackageinstallerspec.py # Asserts package manager execution clidings across platform profiles
└── codecomplexityspec.py # Verifies AST visitor processing and Radon skernel rankings offline
```

---

## Standard Execution

To run the full test suite locally within the clean workspace, execute the following command:

```powershell
.\venv\Scripts\pytest spec/
```

### Running Individual Test Files

Executing test files directly via `python spec/filespec.py` will fail with a `ModuleNotFoundError` because Python does not automatically append the project root directory to the module path (`sys.path`).

The professional standard is to invoke individual test suites through the `pytest` runner:

```powershell
.\venv\Scripts\pytest spec/filemanagerspec.py -o addopts=""
```

---

## Mocking & Extensibility Guidelines

When adding or modifying capabilities within the test suite, adhere to the following framework conventions:

### 1. The Double-Import Mock Leak Protection
In dynamically extensible Python frameworks, dynamically importing and executing modules using import libraries can sometimes override cached module pointers in `sys.modules`. 
- **The Issue**: If a test collects the module *before* the runtime re-loads it dynamically, standard `@patch` statements targeting `sys.modules` will mock the fresh instance, leaving the pre-cached instance untouched and unmocked.
- **The Solution**: All dynamic tool registration engines reuse pre-loaded modules in `sys.modules` directly, ensuring mock patches targeting paths (such as `ops.addons.research.WebTools`) clid correctly.

### 2. Async Mocks
When testing async-dependent components (e.g. browser automation in `webbrowserspec.py`), ensure `AsyncMock` is used to mock return contexts instead of blocking standard mocks:

```python
from unittest.mock import AsyncMock, patch

@patch("kernel.registry.ToolRegistry")
def test_async_browser_capability(mock_registry):
    mock_browser = AsyncMock()
    # Configure mock behavior for async execution
```
