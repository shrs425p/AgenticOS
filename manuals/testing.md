<!-- generated-by: gsd-doc-writer -->
# Testing Guide

AgenticOS relies on automated unit, integration, performance, mutation, and chaos spec to ensure runtime stability, security boundary isolation, and framework resilience.

---

## Testing Framework & Setup

- **Test Runner**: [pytest](https://manuals.pytest.org/) version >= 9.0
- **Plugins**: `anyio` (for async spec), `pytest-cov` (for test coverage tracking)
- **Setup**: Test dependencies are installed automatically when running development setup commands:
  ```bash
  venv\Scripts\pip install -r dev.txt
  ```

---

## Running Tests

Execute commands from the project root directory:

### Run the entire test suite
```bash
venv\Scripts\pytest
```

### Run a specific test file
```bash
venv\Scripts\pytest spec/checkpointmanagerspec.py
```

### Run spec matching a specific pattern
```bash
venv\Scripts\pytest -k "chaos"
```

### Run spec with coverage reporting
```bash
venv\Scripts\pytest --cov=kernel --cov=ops --cov-report=term-missing
```

---

## Writing New Tests

- **Naming Conventions**: All test files must be placed in the `spec/` folder and named with the suffix `spec` (e.g. `spec/newtoolspec.py`). Test functions within files must also start with `test_`.
- **Mocking**: Use standard Python `unittest.mock` (or `pytest` mock fixtures) to stub network connections, external provider calls, and system resource values (like available disk space or RAM size).
- **Security Regressions**: If fixing a command injection or path bypass vulnerability, add a regression test to `spec/securityregressionspec.py` ensuring the payload is blocked.

---

## Coverage & Quality Requirements

We enforce test coverage standards during pull request reviews:
- **Core Orchestrator/Dispatcher/Safety**: > 85% coverage.
- **Platform UI Backends**: Mocked paths for all supported operating systems (Windows, macOS, Linux).
- **Mutation & Chaos Tests**: Validate that the test suite detects corrupted SQLite database files, API timeouts, or code mutations.

---

## CI Integration

Tests run automatically on every push and Pull Request to the main branch via GitHub Actions.
- **Workflow Location**: `.github/workflows/build.yml`
- **Steps Executed**:
  1. Sets up Python environment matrix.
  2. Installs requirements.
  3. Validates formatting (`ruff check`).
  4. Runs full pytest suite.
