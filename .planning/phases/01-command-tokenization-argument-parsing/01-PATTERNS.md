# Phase 1: Command Tokenization & Argument Parsing - Patterns

**Mapped:** 2026-06-05
**Padded Phase:** 01

## Component Map

We will modify/create components in the terminal subsystem:

| File Path | Role | Data Flow | Closest Analog |
|-----------|------|-----------|----------------|
| [tools/terminal/safety.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/safety.py) | Security boundary / Policy enforcement | Intercepts commands prior to subprocess launch, return validation diagnostics | Existing substring safety checks in `tools/terminal/safety.py` |
| [tests/test_terminal_safety_structural.py](file:///c:/Users/shrs/AgenticOS/tests/test_terminal_safety_structural.py) | Unit test suite | Invokes safety validator with test cases, assert block results | [tests/test_validators.py](file:///c:/Users/shrs/AgenticOS/tests/test_validators.py) |

---

## Existing Patterns

### Substring-based Safety Checks
The current implementation in [safety.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/safety.py#L5-L31):
```python
class SafetyMixin:
    def _blocked_command_reason(self, command: str) -> str:
        if not self.rules.get("allow_shell_exec", True):
            return "shell execution is disabled"

        if not self.rules.get("validate_commands", False):
            return ""

        lowered = (command or "").lower().strip()
        blocked_groups = []
        # ... groups lookup ...
        for token in blocked_groups:
            if lowered.startswith(token) or f" {token}" in lowered:
                return f"Command blocked by safety rules: {token.strip()}"
        return ""
```

### Pytest Unit Test Pattern
From [test_validators.py](file:///c:/Users/shrs/AgenticOS/tests/test_validators.py#L1-L24):
```python
import pytest
from pathlib import Path
from core.validators import validate_tool

def test_validate_tool_write_file(tmp_path):
    # Setup and assertions ...
    pass
```

---

## Target Patterns

### 1. Structural Tokenization and Sanitization
```python
import shlex
import os
import re

def _clean_token(token: str) -> tuple[str, bool]:
    cleaned = token
    while len(cleaned) >= 2:
        if cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1]
        elif cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        else:
            break
    has_internal = "'" in cleaned or '"' in cleaned
    final_cleaned = cleaned.replace("'", "").replace('"', "")
    return final_cleaned, has_internal
```

### 2. Recursive Command Resolving
For nested shell invocations:
```python
verb = _get_command_verb(cleaned_tokens[0])
for i, t in enumerate(cleaned_tokens):
    if verb in {"powershell", "pwsh", "cmd", "bash", "sh", "zsh", "dash", "ash"}:
        # identify -Command / -c / /c flags and recursively validate next token
        pass
```
