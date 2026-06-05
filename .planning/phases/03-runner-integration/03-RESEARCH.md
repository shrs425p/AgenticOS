# Phase 3: Runner Integration - Codebase Analysis & Research Report

This report presents a detailed analysis of the codebase for **Phase 3: Runner Integration**. It covers subprocess command execution, integration of safety guardrails, line-by-line script validation, blocked error formatting, and audit logging for security validation failures.

---

## 1. Subprocess Command Execution in `tools/terminal/runner.py`

The execution of terminal operations is managed by the `RunnerMixin` class (located in [runner.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/runner.py)), which provides base execution capabilities for the terminal toolset:

### `_run`
This is the core execution pipeline for all shell operations:
- **Environment Preparation**: Merges `os.environ` with runtime overrides (`self._env_overrides`) and extra call-specific environment variables (`env_extra`). It enforces UTF-8 by setting `PYTHONIOENCODING="utf-8"` and `PYTHONUTF8="1"`.
- **Pre-execution Guardrails**: Evaluates `self._blocked_command_reason(command)` prior to launching any subprocess. If a command is blocked, it halts immediately and returns `f"Error: {blocked_reason}"`.
- **PATH Refreshing**: Performs dynamic PATH updating via `refresh_path()` right before execution to reflect newly installed commands/binaries.
- **Subprocess Invocation**: Calls `subprocess.run` with:
  - `shell=True` (and specifies `"executable": "/bin/bash"` on non-Windows/POSIX platforms to prevent default `/bin/sh` behavior).
  - `capture_output=True` to fetch standard output and errors.
  - Encoding set to `utf-8` and errors set to `replace` to prevent encoding-related execution failures.
  - User-configurable execution timeouts.
- **Self-Healing Mechanics**: If the exit code indicates command-not-found (`127` on POSIX or `9009` on Windows) or a `FileNotFoundError` is raised, it attempts to dynamically resolve and install the missing binary via `self_provision_command(cmd_name)`. If provisioning succeeds, it retries execution exactly once with `_is_retry=True`.
- **Output Assembly**: Returns standard output or standard error prefixed by `[stderr]`.

### `run_command`
- Exposes `_run` directly as a registered tool with a default timeout of 30 seconds.

### `run_powershell`
- Checks `self.system`. If the system is POSIX (Linux/macOS), it falls back to a standard shell call.
- If Windows, it executes the command via PowerShell by wrapping and escaping it: `powershell -NoProfile -Command {quoted_command}` using `self._quote_arg(command)`.

### `run_script`
- Resolves the target script file to a canonical path (`Path(path).resolve()`).
- Checks script existence, returning `Error: Script not found: {path}` on failure.
- Auto-detects the interpreter if none is provided based on the file suffix:
  - `.py` $\rightarrow$ `python`
  - `.sh` / `.bash` $\rightarrow$ `bash`
  - `.zsh` $\rightarrow$ `zsh`
  - `.ps1` $\rightarrow$ `powershell -NoProfile -ExecutionPolicy Bypass -File`
  - `.cmd` / `.bat` $\rightarrow$ `cmd /c`
- Wraps the script path using `_quote_arg` to prevent shell injection/bypass, constructs the final wrapper command (e.g., `bash "/path/to/script.sh"`), and calls `_run` with a timeout of 300 seconds.

---

## 2. Integration of AST-like Safety Validation (`SafetyMixin`)

The safety checks are implemented inside `SafetyMixin` (located in [safety.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/safety.py)) and mixed into the runtime executor.

### Integration Mechanism
In [__init__.py](file:///c:/Users/shrs/AgenticOS/tools/terminal/__init__.py), the class `TerminalExecutor` is defined using multiple inheritance:
```python
class TerminalExecutor(
    SafetyMixin,
    RunnerMixin,
    # ... other mixins
):
```
Because `SafetyMixin` precedes `RunnerMixin` in the class signature (MRO), all methods of `SafetyMixin` are bound to `self`.

### Evaluation Points
During execution, `RunnerMixin._run` performs safety validation at the entry point of the method:
```python
# tools/terminal/runner.py (Line 42)
blocked_reason = self._blocked_command_reason(command)
if blocked_reason:
    return f"Error: {blocked_reason}"
```
This is evaluated *before* any subprocess is created, preventing dangerous operations from ever executing. The evaluation covers:
1. **Shell Disabled Check**: Verifies `self.rules.get("allow_shell_exec", True)`.
2. **Command Validation Check**: Verifies `self.rules.get("validate_commands", False)`.
3. **Chaining Operators Check**: Pre-tokenization scanner (`_has_chaining_operators`) looks for unquoted command separators (`&&`, `||`, `;`, `|`, `` ` ``, `$()`) that could bypass tokenization.
4. **Obfuscation Detection**: Reconstructs tokens by stripping quoting/escaping combinations and flags them if a token's characters are purely alphanumeric/hyphens/underscores but contain internal quotes or escapes (e.g., `s'c'` or `n\e\t`).
5. **Environment Variables Check**: Scans for variable patterns (e.g., `%VAR%`, `$VAR`, `${VAR}`) in command verb positions.
6. **Command Registry Matches**: Blocks registry edits, service modifications, and system-level commands (e.g., `sc`, `reg`, `systemctl`, `shutdown`) if restricted by policy.
7. **Recursive Wrapper Check**: Performs recursive validation on nested shell command parameters (e.g. `cmd /c`, `powershell -c`, `bash -c`).

---

## 3. Line-by-Line Script Validation Design & Implementation

### The Security Vulnerability
Currently, `run_script` only validates the wrapper command launching the script (e.g., `bash "/path/to/script.sh"`). The interior lines of the script are **never** validated. If a script contains blocked actions (like `sc stop` or `reg delete`), it bypasses `_blocked_command_reason` because the interpreter executes the file directly in a subprocess.

### Line-by-Line Parser Design
To prevent this, `run_script` must validate the content of the script line-by-line prior to executing it.

1. **Target Identification**: Check if the script's extension is a shell script (`.ps1`, `.bat`, `.cmd`, `.sh`, `.bash`).
2. **File Reading**: Load the content of the script securely using UTF-8 with character replacement to avoid crashes on non-Unicode characters.
3. **Comment Filtering**: Strip line comments based on the interpreter syntax:
   - For POSIX shells (`.sh`, `.bash`) and PowerShell (`.ps1`): Comments start with `#`.
   - For Batch/CMD (`.bat`, `.cmd`): Comments start with `REM` (case-insensitive) or `::`.
4. **Line Continuation Reconstruction**: Evasion attempts might split commands across lines using line continuation characters:
   - POSIX (`\`)
   - PowerShell (`` ` ``)
   - Batch/CMD (`^`)
   We must merge continued lines before validation.
5. **Failure Handling**: If any reconstructed command line fails `_blocked_command_reason`, abort execution immediately and return the formatted error string.

### Python Implementation Blueprint for `run_script`

We can integrate the following validation sequence inside `run_script` before executing `self._run`:

```python
    # Map of line continuation characters by suffix
    _CONTINUATION_CHARS = {
        ".sh": "\\",
        ".bash": "\\",
        ".ps1": "`",
        ".cmd": "^",
        ".bat": "^",
    }

    # Inside run_script:
    suffix = p.suffix.lower()
    if suffix in self._CONTINUATION_CHARS:
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            continuation_char = self._CONTINUATION_CHARS[suffix]
            
            current_line = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                
                # Filter full-line comments
                is_comment = False
                if suffix in (".sh", ".bash", ".ps1"):
                    if stripped.startswith("#"):
                        is_comment = True
                elif suffix in (".bat", ".cmd"):
                    # Match REM followed by a space, REM at end-of-line, or :: comments
                    up = stripped.upper()
                    if up.startswith("REM ") or up == "REM" or stripped.startswith("::"):
                        is_comment = True
                
                if is_comment:
                    continue
                
                # Check for line continuation
                if stripped.endswith(continuation_char):
                    # Strip the continuation character and accumulate
                    current_line.append(stripped[:-1].strip())
                    continue
                else:
                    current_line.append(stripped)
                    full_command = " ".join(current_line).strip()
                    current_line = []
                    
                    if full_command:
                        reason = self._blocked_command_reason(full_command)
                        if reason:
                            # Normalize formatting contract
                            if not reason.startswith("Command blocked by safety rules:"):
                                reason = f"Command blocked by safety rules: {reason}"
                            return f"Error: {reason}"
            
            # Handle trailing continuation if script ends on a continued line
            if current_line:
                full_command = " ".join(current_line).strip()
                if full_command:
                    reason = self._blocked_command_reason(full_command)
                    if reason:
                        if not reason.startswith("Command blocked by safety rules:"):
                            reason = f"Command blocked by safety rules: {reason}"
                        return f"Error: {reason}"
                        
        except Exception as e:
            return f"Error reading script file for safety validation: {e}"
```

---

## 4. Normalizing Blocked Error Formatting

The system requires blocked commands to return error strings in the format:
`Error: Command blocked by safety rules: [Reason]`

Currently, `_blocked_command_reason` returns `"shell execution is disabled"` when shell execution is entirely disabled, which results in `Error: shell execution is disabled`. 

To guarantee that all blocked operations return the normalized format, we should wrap the blocked reason formatting:

```python
        blocked_reason = self._blocked_command_reason(command)
        if blocked_reason:
            if not blocked_reason.startswith("Command blocked by safety rules:"):
                blocked_reason = f"Command blocked by safety rules: {blocked_reason}"
            return f"Error: {blocked_reason}"
```

This enforces the exact target format across `_run` and the line-by-line script validator.

---

## 5. Audit Logging & Security Warning Integration

### Audit Logger Setup
The `AuditLogger` in [audit_logger.py](file:///c:/Users/shrs/AgenticOS/core/audit_logger.py) writes JSONL records to `session.jsonl`, `tools.jsonl`, `errors.jsonl`, and `paths.jsonl`.

### Processing Blocked Commands
1. **Failure Classification**: When a command is blocked, it returns a string starting with `"Error:"`. In `runtime.py`, this is processed through `infer_success(obs)` which flags it as a failure (`success=False`).
2. **Tool Log Entry**: The tool execution loop logs this failure to `tools.jsonl`:
   ```json
   {
     "ts": "2026-06-05 18:00:00",
     "event": "tool_call",
     "session_id": "...",
     "tool": "run_command",
     "args": "...",
     "duration_ms": 1,
     "success": false,
     "validation": "",
     "observation_preview": "Error: Command blocked by safety rules: ..."
   }
   ```

### Implementing Explicit Security Warning Logs
A blocked command represents a security event rather than a general tool error. To log this explicitly:

1. **Structured Audit Error**: Write validation failures as explicit security events to `errors.jsonl` using the existing audit error recorder. Inside `core/runtime.py` where tool responses are evaluated:
   ```python
   # Detect if tool execution was blocked by safety rules
   if not ok and "blocked by safety rules" in obs_text.lower():
       self.audit.error(
           session_id=self.session_id,
           where="security_validation",
           message=f"Security warning: {obs_text}"
       )
   ```
   This generates an entry in the structured errors log:
   ```json
   {
     "ts": "2026-06-05 18:00:00",
     "event": "error",
     "session_id": "...",
     "where": "security_validation",
     "message": "Security warning: Error: Command blocked by safety rules: ..."
   }
   ```

2. **Centralized Log File Alert**: Write to the centralized logger (`data/logs/agenticos.log`) using the standard logger.
   ```python
   import logging
   logger = logging.getLogger("agenticos.security")
   logger.warning("SECURITY WARNING: Command execution blocked by safety rules: %s", command)
   ```
   This ensures security events are captured in both the structured audit trail and the developer-facing application log files.
