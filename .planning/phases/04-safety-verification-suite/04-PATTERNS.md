# Phase 4: Safety Verification Suite - Patterns Report

## 1. Overview
This report lists the architectural role, codebase analogs, and concrete code patterns for all files to be modified or created in Phase 4. It incorporates remediations for the Phase 3 code review findings (CR-01, WR-01, WR-02, IN-01, IN-02, and IN-03) and establishes a hybrid testing pattern (unit/mock-based and live integration tests) to satisfy the **TEST-01** safety verification suite requirements.

---

## 2. File Patterns

### 1. `tools/terminal/safety.py` (Modified)
- **Role in Architecture**: Part of the **Guardrails Layer**. It provides the core safety rules validation (`SafetyMixin`) applied to terminal command executions prior to subprocess dispatch, preventing unauthorized actions, shell chaining, and obfuscation.
- **Closest Analogs & Existing Methods**:
  - `_blocked_command_reason`: Contains command block logic, string checks, and recursive wrapper checks.
  - `_contains_variable`: Scans tokens for variable expansions using regular expressions.
  - `_clean_token`: Cleans quotes and escape sequences.
- **Concrete Code Patterns & Excerpts**:
  - *Abbreviation Prefix Matching Pattern (CR-01)*:
    ```python
    def _is_powershell_command_flag(self, token: str) -> bool:
        t = token.lower()
        if not (t.startswith("-") or t.startswith("/")):
            return False
        flag = t[1:]
        return len(flag) > 0 and "command".startswith(flag)

    def _is_powershell_encoded_flag(self, token: str) -> bool:
        t = token.lower()
        if not (t.startswith("-") or t.startswith("/")):
            return False
        flag = t[1:]
        return len(flag) > 0 and "encodedcommand".startswith(flag)
    ```
  - *Base64 UTF-16LE Decoding & Recursive Validation Pattern (CR-01)*:
    ```python
    import base64

    # Inside _blocked_command_reason wrapping parameters check (e.g. for powershell/pwsh):
    if self._is_powershell_encoded_flag(token) and i + 1 < len(tokens):
        encoded_payload = self._strip_wrapping_quotes(tokens[i + 1])
        if self._contains_variable(encoded_payload):
            return (
                "Command blocked by safety rules: environment variable expansion "
                f"detected in wrapper parameters ({encoded_payload})"
            )
        try:
            # Normalize whitespace and pad base64 payload
            clean_payload = "".join(encoded_payload.split())
            missing_padding = len(clean_payload) % 4
            if missing_padding:
                clean_payload += "=" * (4 - missing_padding)
            decoded_bytes = base64.b64decode(clean_payload)
            decoded_cmd = decoded_bytes.decode("utf-16-le")
        except Exception as e:
            return f"Command blocked by safety rules: unable to decode base64 payload ({e})"

        nested_reason = self._blocked_command_reason(decoded_cmd)
        if nested_reason:
            return nested_reason
    ```

### 2. `tools/terminal/runner.py` (Modified)
- **Role in Architecture**: Part of the **Tools/Execution Layer**. Defines `RunnerMixin` which implements registered terminal tools (`run_command`, `run_powershell`, `run_python`, `run_script`), acting as a bridge to subprocess spawns while invoking safety checks.
- **Closest Analogs & Existing Methods**:
  - `_validate_script_content`: Line-by-line file parser for shell scripts.
  - `_run`: Central subprocess dispatcher.
- **Concrete Code Patterns & Excerpts**:
  - *Zsh Continuation and Comments Support Pattern (WR-01)*:
    ```python
    _CONTINUATION_CHARS = {
        ".sh": "\\",
        ".bash": "\\",
        ".zsh": "\\",     # Added Zsh support
        ".ps1": "`",
        ".cmd": "^",
        ".bat": "^",
    }

    # Inside _validate_script_content:
    if suffix in (".sh", ".bash", ".zsh", ".ps1"): # Added Zsh support
        if stripped.startswith("#"):
            is_comment = True
    ```
  - *Deduplicated Self-Healing Helper Pattern (IN-02)*:
    ```python
    def _attempt_self_healing(
        self,
        command: str,
        timeout: int,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None,
        env_extra: Optional[dict] = None,
    ) -> Optional[str]:
        """Attempt to auto-provision a missing command.

        Returns:
            The execution output from retrying the command if provisioning succeeded,
            otherwise None.
        """
        cmd_name = ""
        try:
            parts = shlex.split(command)
            if parts:
                cmd_name = parts[0]
        except Exception:
            cmd_name = command.split()[0] if command.split() else ""
        cmd_name = os.path.basename(cmd_name).replace('"', '').replace("'", "")

        if cmd_name:
            try:
                from core.self_provisioner import self_provision_command
                if self_provision_command(cmd_name):
                    return self._run(
                        command,
                        timeout=timeout,
                        cwd=cwd,
                        input_data=input_data,
                        env_extra=env_extra,
                        _is_retry=True,
                    )
            except Exception:
                pass
        return None
    ```
  - *Google-style Docstring Pattern (IN-01)*:
    ```python
    @tool(name="run_command", desc="Run shell command. Args: command", category="Terminal")
    def run_command(self, command: str, timeout: int = 30) -> str:
        """Run a shell command using subprocess.

        Args:
            command: The command line string to run.
            timeout: Maximum execution time in seconds.

        Returns:
            The combined stdout and stderr of the command, or a safety block message.
        """
        return self._run(command, timeout=timeout)
    ```

### 3. `core/runtime.py` (Modified)
- **Role in Architecture**: Part of the **Runtime Coordination Layer**. Manages agent runtime loops, workspace configurations, memory sessions, tool invocation, and logs security incidents.
- **Closest Analogs & Existing Methods**:
  - `run`: Main agent execution loop.
  - Security audit and logger integration within `run` loop (lines 749-764).
- **Concrete Code Patterns & Excerpts**:
  - *Audit / Security Variable Scope Resolution Pattern (WR-02)*:
    ```python
    # Ensure default values are declared in the outer scope to prevent UnboundLocalError
    obs_text = str(obs or "")
    ok = False
    
    # Audit log tool call (no chat content).
    try:
        import json as _json
        ok = infer_success(obs_text)
        ...
        self.audit.tool_call(...)
    except Exception as exc:
        try:
            self.audit.error(self.session_id, "audit.tool_call", str(exc))
        except (IOError, OSError) as e:
            print_warning(f"Warning: Failed to log audit error: {e}")

    # Log security validation events to audit trail and logger.
    try:
        if not ok and "blocked by safety rules" in obs_text.lower():
            self.audit.error(
                self.session_id,
                "security_validation",
                f"Security warning: {obs_text}",
            )
            logger.warning(
                "SECURITY WARNING: Command execution blocked by safety rules: %s",
                _json.dumps(args, ensure_ascii=False)
                if isinstance(args, (dict, list))
                else str(args),
            )
    except Exception:
        pass
    ```
  - *Imports Alphabetical Ordering Pattern (IN-03)*:
    Standard library, third party, and local module imports are sorted alphabetically with clear separation lines.

### 4. `tests/test_terminal_safety_structural.py` (Modified)
- **Role in Architecture**: Part of the **Verification/Testing Layer**. Formulates isolated, platform-agnostic, and mock-based unit tests to assert correct safety behaviors.
- **Closest Analogs & Existing Methods**:
  - `test_basic_safety_blocks`, `test_quote_obfuscation_detection`, `test_nested_execution_recursion`, `test_variable_expansions`.
- **Concrete Code Patterns & Excerpts**:
  - *Mock Verification of PowerShell Abbreviated Commands*:
    ```python
    def test_powershell_abbreviation_blocks():
        rules = {
            "allow_shell_exec": True,
            "validate_commands": True,
            "allow_service_control": False,
        }
        safety = DummySafety(rules)
        # Verify abbreviations like -comm or -co block nested commands
        assert "Command blocked" in safety._blocked_command_reason("powershell -comm \"sc stop spooler\"")
        assert "Command blocked" in safety._blocked_command_reason("powershell -c \"sc stop spooler\"")
        assert "Command blocked" in safety._blocked_command_reason("pwsh -co \"sc stop spooler\"")
    ```
  - *Mock Verification of PowerShell Base64 Encoded Commands*:
    ```python
    def test_powershell_base64_decoding_blocks():
        rules = {
            "allow_shell_exec": True,
            "validate_commands": True,
            "allow_service_control": False,
        }
        safety = DummySafety(rules)
        # cwBjACAAcwB0AG8AcAAgAHMAcABvAG8AbABlAHIA is UTF-16LE base64 for 'sc stop spooler'
        assert "Command blocked" in safety._blocked_command_reason("powershell -enc cwBjACAAcwB0AG8AcAAgAHMAcABvAG8AbABlAHIA")
        assert "Command blocked" in safety._blocked_command_reason("powershell -encodedcommand cwBjACAAcwB0AG8AcAAgAHMAcABvAG8AbABlAHIA")
        # Invalid base64
        assert "unable to decode base64" in safety._blocked_command_reason("powershell -enc invalid_b64!!!")
    ```
  - *Zsh Script Continuation and Line Scans*:
    ```python
    def test_zsh_script_validation(tmp_path):
        script = tmp_path / "test.zsh"
        script.write_text("#!/bin/zsh\nsc \\\nstop spooler\n", encoding="utf-8")
        runner = DummyRunner(_default_rules())
        result = runner.run_script(str(script))
        assert "blocked by safety rules" in result.lower()
    ```

### 5. `tests/test_terminal_safety_integration.py` (New File)
- **Role in Architecture**: Part of the **Verification/Testing Layer**. Contains live host-OS execution integration tests to verify real subprocesses are blocked and log security alerts.
- **Closest Analogs & Existing Methods**:
  - `tests/integration/test_tool_chains.py` (uses direct tool calls on a real workspace registry).
- **Concrete Code Patterns & Excerpts**:
  - *Environment Detection and Live Testing Structure*:
    ```python
    import shutil
    import pytest
    from core.tool_registry import ToolRegistry

    @pytest.fixture
    def registry():
        cfg = {
            "agent": {"workspace": "workspace"},
            "rules": {
                "allow_shell_exec": True,
                "validate_commands": True,
                "allow_service_control": False,
                "allow_registry_edit": False,
            },
        }
        return ToolRegistry(cfg=cfg)

    @pytest.mark.skipif(not shutil.which("powershell"), reason="PowerShell not installed")
    def test_live_powershell_blocked_by_safety(registry):
        # Verify a live powershell call trying to execute service control gets blocked
        result = registry.call("run_powershell", {"command": "sc stop spooler"})
        assert "Error: Command blocked by safety rules:" in result

    def test_live_bash_blocked_by_safety(registry):
        if not shutil.which("bash"):
            pytest.skip("Bash shell not found on this host")
        result = registry.call("run_command", {"command": "bash -c 'sc stop spooler'"})
        assert "Error: Command blocked by safety rules:" in result
    ```
