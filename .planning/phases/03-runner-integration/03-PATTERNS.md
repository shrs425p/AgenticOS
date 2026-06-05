# Phase 3: Runner Integration - Codebase Patterns Mapping Report

This patterns report maps the architectural roles, closest existing codebase analogs, and concrete code patterns required for implementing **Phase 3: Runner Integration**. It defines the structural layout and integration details for script validation, blocked error normalization, and explicit security audit logging.

---

## 1. tools/terminal/runner.py

### Architectural Role
* **Role**: Execution Layer / Tool Capability.
* **Explanation**: Implements `RunnerMixin`, which provides low-level subprocess execution mechanisms and wraps them in user-facing decorators (`@tool`). It acts as the final gatekeeper that translates high-level intents (e.g. `run_command`, `run_script`) into system execution calls.

### Closest Codebase Analogs
* **Analog Method 1**: `RunnerMixin._run` (checks command safety, executes subprocess, handles command self-healing).
* **Analog Method 2**: `RunnerMixin.run_script` (canonicalizes script path, auto-resolves interpreter based on file suffix, and runs the interpreter command via `_run`).

### Concrete Code Excerpts
Below are the existing patterns in `tools/terminal/runner.py` that dictate how validation and execution are structured:

#### A. Pre-Execution Guardrails Interception (from `_run`)
```python
        blocked_reason = self._blocked_command_reason(command)
        if blocked_reason:
            return f"Error: {blocked_reason}"
```

#### B. Interpreter Mapping & Canonicalization (from `run_script`)
```python
        p = Path(path).resolve()
        if not p.exists():
            return f"Error: Script not found: {path}"

        interp = (interpreter or "").strip()
        if not interp:
            suffix = p.suffix.lower()
            interp_map = {
                ".py": "python",
                ".sh": "bash",
                ".bash": "bash",
                ".zsh": "zsh",
                ".ps1": "powershell -NoProfile -ExecutionPolicy Bypass -File",
                ".cmd": "cmd /c",
                ".bat": "cmd /c",
            }
            interp = interp_map.get(suffix, "")
        cmd = f"{interp} {self._quote_arg(str(p))}".strip() if interp else str(p)
        return self._run(cmd, timeout=300)
```

### Script Scanning Integration Pattern (Planned Modification)
To validate script contents line-by-line before shell execution, we map line continuation characters per suffix:
```python
    _CONTINUATION_CHARS = {
        ".sh": "\\",
        ".bash": "\\",
        ".ps1": "`",
        ".cmd": "^",
        ".bat": "^",
    }
```
And execute a file-reading safety loop inside `run_script` before dispatching to `_run`.

---

## 2. core/runtime.py & core/audit_logger.py

### Architectural Role
* **Role**: Orchestration & Auditing.
* **Explanation**: `core/runtime.py` orchestrates the lifecycle loop (`Agent.run`), parsing and dispatching tool commands, mentally validating them (`verify_action`), and receiving tool observations. `core/audit_logger.py` records structured actions, outcomes, and failures (errors, tool telemetry) to persistent JSONL and log files for safety and diagnostic logging.

### Closest Codebase Analogs
* **Analog Method 1**: `Agent.run` loop's tool auditing pipeline (captures tool execution outcomes and writes them to `self.audit.tool_call`).
* **Analog Method 2**: `AuditLogger.error` (captures error metrics and appends records to the structured `errors.jsonl` log file).

### Concrete Code Excerpts
Below are the existing execution and auditing patterns:

#### A. Tool Success Inference & Auditing Call (from `core/runtime.py`)
```python
                    obs = self.tools.call(tool_name, args)
                    # ...
                    # Audit log tool call (no chat content).
                    try:
                        import json as _json

                        obs_text = str(obs or "")
                        validation = ""
                        # ...
                        ok = infer_success(obs_text)
                        # ...
                        self.audit.tool_call(
                            session_id=self.session_id,
                            tool_name=tool_name,
                            tool_args=_json.dumps(args, ensure_ascii=False)
                            if isinstance(args, (dict, list))
                            else str(args),
                            started_ts=started,
                            ended_ts=ended,
                            success=ok,
                            validation=validation,
                            observation_preview=obs_text,
                        )
```

#### B. Structured Error Log Entry Pattern (from `core/audit_logger.py`)
```python
    def error(self, session_id: str, where: str, message: str):
        """error function."""
        error_limit = int(self.log_cfg.get("error_truncation_limit", 4000))
        msg = _redact(message, cfg=self.cfg)[:error_limit]
        obj = {
            "ts": _now_iso(),
            "event": "error",
            "session_id": session_id,
            "where": where,
            "message": msg,
        }
        self._write_jsonl(self.errors_log, obj)
        flat = msg.replace("\r", " ").replace("\n", " ")
        self._write_log(
            self.errors_text,
            f"{obj['ts']} error session_id={session_id} where={where} message={flat!r}",
        )
```

### Safety Warning & Explicit Event Logging Pattern (Planned Integration)
To write validation errors explicitly to the structured audit error log and the main application log, we inject the following safety interception code right after `self.tools.call` returns in `core/runtime.py`:
```python
                    # Detect if tool execution was blocked by safety rules
                    if not ok and "blocked by safety rules" in obs_text.lower():
                        # Write to structured audit logs (errors.jsonl)
                        self.audit.error(
                            session_id=self.session_id,
                            where="security_validation",
                            message=f"Security warning: {obs_text}"
                        )
                        # Write to developer-facing console/file logger
                        import logging
                        security_logger = logging.getLogger("agenticos.security")
                        security_logger.warning("SECURITY WARNING: Command execution blocked by safety rules: %s", args)
```

---

## 3. tests/test_terminal_safety_structural.py

### Architectural Role
* **Role**: Verification & Quality Gate.
* **Explanation**: Provides unit tests asserting safety behaviors under different environment profiles (NT vs POSIX) using target command patterns and obfuscation tests.

### Closest Codebase Analogs
* **Analog Pattern 1**: `DummySafety` subclass (simulates class mixing to test `SafetyMixin` without instantiating the entire agent framework or database).
* **Analog Pattern 2**: Monkeypatching `os.name` to test platform-specific tokenization rules.

### Concrete Code Excerpts
Below are the existing test setup and platform-switching patterns from `tests/test_terminal_safety_structural.py`:

#### A. Dummy Safety Subclass Pattern
```python
class DummySafety(SafetyMixin):
    """A dummy class implementing SafetyMixin for testing purposes."""

    def __init__(self, rules: dict):
        """Initialize the dummy safety instance with the given rules.

        Args:
            rules: The safety rules dictionary.
        """
        self.rules = rules
```

#### B. Platform Mocking & Assertion Pattern
```python
def test_escape_obfuscation_posix(monkeypatch):
    """Verify escape obfuscation detection on POSIX/macOS (backslash)."""
    monkeypatch.setattr(os, "name", "posix")
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_service_control": True,
    }
    safety = DummySafety(rules)

    # POSIX escapes blocked
    assert "command obfuscation detected" in safety._blocked_command_reason("s\\c query")
```

### Script Validation Test Integration Pattern (Planned Integration)
To verify script content scanning, we will add unit tests using the pytest `tmp_path` fixture to dynamically write mock scripts and verify validation outcomes:
```python
def test_run_script_safety_validation(tmp_path, monkeypatch):
    """Verify that run_script reads interior lines and blocks blocked verbs."""
    # Mock TerminalExecutor or load TerminalExecutor directly
    ...
    # Create benign script
    benign_script = tmp_path / "benign.sh"
    benign_script.write_text("echo 'hello'\nls -la", encoding="utf-8")
    
    # Create malicious script
    malicious_script = tmp_path / "exploit.sh"
    malicious_script.write_text("echo 'hello'\nsc stop spooler\n", encoding="utf-8")
    
    # Assert benign runs/passes validation
    # Assert malicious is blocked and returns normalized blocked message
```
