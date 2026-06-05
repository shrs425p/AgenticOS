# AgenticOS: Testing and Quality Assurance Guide

AgenticOS uses a robust, high-coverage testing framework built on `pytest`. To maintain the stability and security of the system, all core logic and tool interactions must be validated through automated tests.

---

## Testing Philosophy

Our testing strategy follows the **"Isolated Simulation"** model:
1.  **Safety**: Tests must never modify the real host system. Use temporary directories and mocks.
2.  **Portability**: Tests must run on any OS (Windows/Linux) without external dependencies.
3.  **Speed**: Unit tests should execute in milliseconds.
4.  **Coverage**: Target coverage for `core/` and `tools/` is **60%+**.

---

## The `tests/` Directory Structure

| File | Scope | Key Features |
| :--- | :--- | :--- |
| `test_fs_*.py` | Filesystem Tools | Uses `tmp_path` to simulate disks. |
| `test_web_tools.py` | Web & APIs | Mocks `requests` and `urllib`. |
| `test_guardrails.py`| Security Logic | Validates `PathGuard` and secret redaction. |
| `test_runtime.py`   | Core Engine | Tests the orchestration loop with a mock LLM. |
| `test_plugins.py`   | Dynamic Loading | Verifies plugin registration and hot-reload. |
| `test_diff_summarizer.py`| Plain Diff Summary | Offline mocks line addition/deletion delta checks. |
| `test_url_safety_check.py`| WHOIS/SSL Security | Mock handshakes and WHOIS sockets offline. |
| `test_os_sandbox_auditor.py`| Sandbox Runtimes | Mocks CLI subprocesses and platform system layers. |
| `test_sys_package_installer.py`| Package Managers | Mock cross-platform installer execution sequences. |
| `test_code_complexity.py`| Radon AST Complexity| Mock visitor node traversal and grading offline. |

---

## Running the Test Suite

### Basic Execution
```bash
pytest
```

### Run a single test file
```bash
pytest tests/test_retry.py -q
```

Note: We added `tests/test_retry.py` to validate the centralized `retry_call()` helper behavior.

### Coverage Reporting
To generate a detailed line-by-line coverage report:
```bash
pytest --cov=core --cov=tools --cov-report=term-missing
```

---

## Mocking Strategies

### 1. Filesystem Mocking (`tmp_path`)
Always use the built-in `tmp_path` fixture to avoid touching the real disk.
```python
def test_write_file(tmp_path):
    manager = FileManager(base_dir=str(tmp_path))
    manager.write_file("test.txt", "Hello World")
    assert (tmp_path / "test.txt").read_text() == "Hello World"
```

### 2. Network Mocking (`unittest.mock`)
Never make real HTTP requests during tests.
```python
@patch("requests.get")
def test_fetch_url(mock_get):
    mock_get.return_value.text = "Mocked Response"
    res = tool.fetch_url("https://example.com")
    assert res == "Mocked Response"
```

---

## CI/CD Integration

The test suite is automatically executed on every push to GitHub via `.github/workflows/ci.yml`.
- **Enforcement**: Pull Requests will be blocked if any test fails or if coverage drops significantly.
- **Environment**: CI runs on `windows-latest` to ensure compatibility with Windows-specific tools (using mocks).

---

## Contributing New Tests

When adding a new tool:
1. Create a corresponding file in `tests/`.
2. Mock any OS-specific calls (e.g., `subprocess.run`).
3. Assert both the **Success Path** and the **Error Path** (e.g., what happens when a file is missing).

---

*Last Updated: 2026-05-18*
*Status: Engineering Standard (Verified Cross-Platform)*

## Test Framework and Setup
Please see [Testing Philosophy](#testing-philosophy) and [Running the Test Suite](#running-the-test-suite) above.

## Running Tests
Please see [Running the Test Suite](#running-the-test-suite) above.

## Writing New Tests
Please see [Contributing New Tests](#contributing-new-tests) above.

## Coverage Requirements
Please see [Testing Philosophy](#testing-philosophy) (Target coverage is 60%+) and [Coverage Reporting](#coverage-reporting) above.

## CI Integration
Please see [CI/CD Integration](#cicd-integration) above.
