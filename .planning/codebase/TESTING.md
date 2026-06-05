# Testing Patterns

**Analysis Date:** 2026-06-05

## Test Framework

**Runner:**
- pytest 9.0.3
- Config: `pytest.ini` in project root.

**Assertion Library:**
- pytest built-in standard Python assertions (`assert` keyword).
- Matchers: `==`, `!=`, `in`, `is`, `pytest.raises` for exception checks.

**Run Commands:**
```bash
pytest                                                # Run all tests
pytest tests/test_retry.py                            # Run single test file
pytest -k "test_retry_call_success"                   # Run specific test by name match
pytest --cov=core --cov=tools --cov-report=html       # Generate HTML coverage report
```

## Test File Organization

**Location:**
- Dedicated `tests/` folder in the project root.
- No source-colocated test files (i.e. tests are kept strictly separate from `core/` and `tools/`).

**Naming:**
- `test_*.py` for all test modules matching the code they verify.

**Structure:**
```
tests/
├── test_ast_parser.py
├── test_audit_logger.py
├── test_config.py
├── test_event_bus.py
├── test_retry.py
├── test_runtime.py
└── integration/
    ├── (integration test files)
```

## Test Structure

**Suite Organization:**
```python
import pytest
from core.retry import retry_call

def test_retry_call_success():
    # Arrange / Setup
    calls = []
    def fn():
        calls.append(1)
        return "ok"

    # Act
    res = retry_call(fn, max_retries=3, base_delay=0.001)

    # Assert
    assert res == "ok"
    assert len(calls) == 1
```

**Patterns:**
- Assertions focus on inputs, outputs, and side effects (like lists tracking function invocations).
- Direct function calls inside `pytest.raises` contexts for verifying exception triggers.

## Mocking

**Framework:**
- Pytest standard `monkeypatch` fixture.
- Custom mock classes or dictionaries inline for testing clients.

**Patterns:**
```python
def test_retry_then_success(monkeypatch):
    # Mock time.sleep to run instantly without waiting
    monkeypatch.setattr("time.sleep", lambda s: None)
    
    attempts = {"count": 0}
    # rest of test code...
```

**What to Mock:**
- IO/networking time constraints (such as `time.sleep`).
- External model API endpoints (such as `requests.post`).
- Shell scripts or subprocess executions (`subprocess.run`).

**What NOT to Mock:**
- Core business logic, configuration schema structures, event routing.

## Fixtures and Factories

**Test Data:**
- Factory dictionaries/fixtures created dynamically inside tests to configure mock runtimes.

**Location:**
- Configured directly inside specific test files or standard pytest `conftest.py` if shared.

## Coverage

**Requirements:**
- Broad coverage targeting core modules (`core/`) and capabilities (`tools/`).
- Coverage monitored via `pytest-cov` and reported on terminal stdout.

**Configuration:**
- Defined inside `pytest.ini` using `addopts = --cov=core --cov=tools --cov-report=term-missing`.

## Test Types

**Unit Tests:**
- Fast, synchronous tests isolating specific functionalities (like retries, configurations, memory operations).
- Execute in milliseconds.

**Integration Tests:**
- Multi-component integration tests verifying actual capabilities execution (like loading tools registry and invoking mock tool commands).
- Located in `tests/integration/` (or general test files matching complex systems).

---

*Testing analysis: 2026-06-05*
*Update when test patterns change*
