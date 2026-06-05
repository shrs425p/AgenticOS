# Coding Conventions

**Analysis Date:** 2026-06-05

## Naming Patterns

**Files:**
- snake_case.py for all Python modules (e.g. `model_clients.py`).
- test_*.py prefix for test files (e.g. `test_runtime.py`).
- UPPERCASE.md for documentation (e.g. `README.md`).

**Functions & Methods:**
- snake_case for all function and method names (e.g. `get_logger`, `list_models`).
- `_` prefix for private helper functions/methods (e.g. `_load_api_key`).

**Variables:**
- snake_case for variable names (e.g. `api_key`, `logger`).
- UPPER_SNAKE_CASE for constants (e.g. `_CACHED_LOG_LEVEL`, `BASE_DIR`).

**Classes:**
- PascalCase for class names (e.g. `OllamaClient`, `NvidiaClient`).

## Code Style

**Formatting:**
- `black` code formatter (26.5.1) - strict Python styling enforcement.
- `ruff` (0.15.15) - code linting and style checking.
- Line length: Standard PEP 8 (88-100 characters max).
- Double quotes preferred for string literals (enforced by `black`).
- Indentation: Strict 4 spaces (no tabs).

**Linting:**
- Checked via `ruff check` and static analysis via `mypy`.
- No unused imports, no undeclared variables.
- Run: `ruff check` / `mypy .`

## Import Organization

**Order:**
1. Standard library imports (e.g. `os`, `sys`, `time`, `logging`).
2. Third-party package imports (e.g. `requests`, `openai`, `google.genai`).
3. Local module imports (e.g. `from core.runtime_config import BASE_DIR`).

**Grouping:**
- Blank lines must separate the three major import categories.
- Alphabetical sorting within each category.

## Error Handling

**Patterns:**
- Core business logic errors throw specific custom exceptions defined in `core/exceptions.py`.
- Try/except blocks capture expected failures, log warning/error diagnostics, and propagate or return a default placeholder.
- HTTP transient rate limit errors (HTTP 429) are pacing-shielded via `core/retry.py` and converted to `RateLimitExhausted` if the retry limit is breached.

**Logging:**
- Failures must be logged using the standard logger before returning or raising.
- Use `logger.exception` to log the full stack trace on unexpected system exceptions.

## Logging

**Framework:**
- Centralized logger factory `core.logger.get_logger(__name__)`.
- Levels: debug, info, warning, error, critical.

**Patterns:**
- Console outputs use simple formatting for readability.
- File logs are fully structured, timestamped, and written to `data/logs/agenticos.log`.
- No raw `print` statements in production core modules.

## Comments

**When to Comment:**
- Comments must explain "why" a design choice was made, especially when integrating with complex API behaviors or platform workarounds (e.g. reconfiguring sys.stdout for Windows Unicode compatibility).
- Document complex logic blocks or optimization pathways.

**Docstrings:**
- Google-style triple-quoted string docstrings are required for all public classes, methods, and functions.
- Specify `Args`, `Returns`, and `Raises` fields explicitly.

```python
def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger with standard formatting.

    Args:
        name: The name of the logger to construct or retrieve.

    Returns:
        logging.Logger: A configured, standard-compliant logger.
    """
```

**TODO Comments:**
- Formatted as `# TODO: description` to track tasks or cleanup targets.

## Function Design

**Size:**
- Keep functions modular and focused. Break large routines into sub-functions.
- Guard clauses at the beginning of functions (return early) to avoid deep nested indentation.

**Parameters:**
- Limit parameter counts (typically under 4). Use dictionary configurations or configuration objects for complex parameters.

---

*Convention analysis: 2026-06-05*
*Update when patterns change*
