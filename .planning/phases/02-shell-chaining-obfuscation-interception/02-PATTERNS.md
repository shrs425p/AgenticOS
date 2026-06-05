# Phase 2: Shell Chaining & Obfuscation Interception - Patterns

**Mapped:** 2026-06-05
**Padded Phase:** 02

## Component Map

We will modify components in the terminal subsystem:

| File Path | Role | Data Flow | Closest Analog |
|-----------|------|-----------|----------------|
| [tools/terminal/safety.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/safety.py) | Security boundary / Policy enforcement | Intercepts chaining, escapes, and variable expansions | Existing structural command safety checks |
| [tests/test_terminal_safety_structural.py](file:///c:/Users/shrs/AgenticOS/tests/test_terminal_safety_structural.py) | Unit test suite | Asserts that chaining and obfuscation checks correctly block/allow commands | Existing safety tests in `test_terminal_safety_structural.py` |

---

## Target Patterns

### 1. Quote-Aware Chaining Scanner
```python
def _has_chaining_operators(self, command: str) -> bool:
    in_single = False
    in_double = False
    i = 0
    while i < len(command):
        char = command[i]
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if char in {";", "|", "&", "`"}:
                return True
            if char == "$" and i + 1 < len(command) and command[i+1] == "(":
                return True
        i += 1
    return False
```

### 2. Variable Expansion Recognition Pattern
Using regular expressions to check for unquoted parameters:
```python
import re

VAR_PATTERNS = [
    re.compile(r"%[a-zA-Z0-9_-]+%"),                  # CMD (%VAR%)
    re.compile(r"\$[a-zA-Z0-9_-]+"),                  # Bash/PowerShell ($VAR)
    re.compile(r"\$\{[a-zA-Z0-9_-]+\}"),               # Bash/PowerShell (${VAR})
    re.compile(r"\$env:[a-zA-Z0-9_-]+", re.IGNORECASE) # PowerShell ($env:VAR)
]
```

### 3. Caret, Backslash, and Backtick Escape Cleansing
Sanitizing escape characters inside words:
```python
def _clean_token(self, token: str) -> tuple[str, bool]:
    # ... strips quotes ...
    # Also strip caret (^), backslash (\), and backtick (`) escapes if they occur inside the identifier
    # ...
```
