---
phase: 03-runner-integration
reviewed: 2026-06-05T13:38:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - tools/terminal/runner.py
  - core/runtime.py
  - tests/test_terminal_safety_structural.py
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: active
---

# Phase 03: Code Review Report

## Summary
The changes in Phase 03 integrate the structural command safety validator (`SafetyMixin`) with the terminal execution layer (`RunnerMixin._run`). They also add deep interior validation for shell scripts (.sh, .bash, .ps1, .bat, .cmd) to prevent script-based execution bypasses. While the test suite passes, a critical security vulnerability exists in PowerShell parameter abbreviation parsing, along with minor validation gaps, log suppression edge cases, and style/duplication issues.

## Critical Issues

### CR-01: PowerShell Wrapper Parameter Parsing Bypass
- **Severity**: Critical (CR-)
- **Component**: `tools/terminal/safety.py` (referenced by `tools/terminal/runner.py`)
- **Description**: PowerShell naturally matches abbreviations or prefixes of parameter names to their full forms (e.g., calling `powershell -comm "..."` resolves to `powershell -Command "..."`). However, the `SafetyMixin._blocked_command_reason` method only checks for exact parameter matches in `{"-command", "-c", "/command", "/c"}`. As a result, using any abbreviated parameters (e.g., `-comm`, `-encodedcommand`, or `-enc`) completely bypasses the recursive validation checks, allowing blocked commands to execute.
- **Remediation**: 
  1. Implement prefix matching for PowerShell execution flags (e.g. check if the parameter starts with `-co` or `/co`).
  2. Implement decoding and validation for `-EncodedCommand` (`-enc`, `-encoded`) parameter variations.

## Warnings

### WR-01: Missing `.zsh` Script Line Validation
- **Severity**: Warning (WR-)
- **Component**: `tools/terminal/runner.py`
- **Description**: While `.zsh` is correctly mapped to `zsh` in `run_script`, `.zsh` is missing from the `_CONTINUATION_CHARS` mapping. Because of this, `_validate_script_content` returns an empty string early, completely skipping line-by-line safety checks for Zsh scripts.
- **Remediation**: Add `".zsh": "\\"` to the `_CONTINUATION_CHARS` dictionary in `tools/terminal/runner.py`.

### WR-02: Scope of `ok` and `obs_text` Variables in `core/runtime.py`
- **Severity**: Warning (WR-)
- **Component**: `core/runtime.py` (lines 725-764)
- **Description**: The variables `ok` and `obs_text` are defined inside the tool-call audit logging `try` block. If that block raises an exception (e.g. during JSON serialization), the variables remain unbound. When the subsequent security logging `try` block references `ok` or `obs_text`, it encounters an `UnboundLocalError`. Although this is caught and silenced, it prevents security validation alerts from being logged when tool-call logging fails.
- **Remediation**: Initialize `ok = False` and `obs_text = ""` with default values before entering the first `try` block, or merge the tool audit and security validation blocks.

## Info

### IN-01: Incomplete Docstrings for Public Run Tools
- **Severity**: Info (IN-)
- **Component**: `tools/terminal/runner.py`
- **Description**: The public methods `run_command`, `run_powershell`, and `run_python` have simple, single-sentence docstrings that do not comply with the Google-style docstring requirements specified in `CONVENTIONS.md` (missing `Args`, `Returns`, etc.).
- **Remediation**: Document parameters and return types using the Google docstring format.

### IN-02: Code Duplication in Command Self-Healing
- **Severity**: Info (IN-)
- **Component**: `tools/terminal/runner.py` (lines 73-96, 111-134)
- **Description**: The logic to extract the command name and trigger `self_provision_command` is duplicated verbatim between the return code check and the `FileNotFoundError` handler.
- **Remediation**: Extract this logic into a single private helper method (e.g., `_self_provision_cmd(self, command)`).

### IN-03: Non-Alphabetical Imports in `core/runtime.py`
- **Severity**: Info (IN-)
- **Component**: `core/runtime.py`
- **Description**: Standard library imports and local module imports are not strictly sorted alphabetically, violating the codebase's import sorting conventions.
- **Remediation**: Reorder the imports in alphabetical order or run `ruff check --select I --fix`.
