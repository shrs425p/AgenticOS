"""Unit tests for SafetyMixin structural command validation and obfuscation detection."""
from __future__ import annotations

import os
import pytest
from tools.terminal.safety import SafetyMixin


class DummySafety(SafetyMixin):
    """A dummy class implementing SafetyMixin for testing purposes."""

    def __init__(self, rules: dict):
        """Initialize the dummy safety instance with the given rules.

        Args:
            rules: The safety rules dictionary.
        """
        self.rules = rules


def test_basic_safety_blocks():
    """Verify that basic disallowed commands are correctly blocked."""
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_registry_edit": False,
        "allow_service_control": False,
        "allow_system_changes": False,
    }
    safety = DummySafety(rules)

    # 1. Service control blocks
    assert "Command blocked by safety rules: sc" in safety._blocked_command_reason("sc query")
    assert "Command blocked by safety rules: net stop" in safety._blocked_command_reason("net stop spooler")
    assert "Command blocked by safety rules: net start" in safety._blocked_command_reason("net start spooler")
    assert "Command blocked by safety rules: systemctl" in safety._blocked_command_reason("systemctl restart nginx")
    assert "Command blocked by safety rules: service" in safety._blocked_command_reason("service apache2 start")

    # 2. Registry edit blocks
    assert "Command blocked by safety rules: reg add" in safety._blocked_command_reason("reg add HKLM\\Software")
    assert "Command blocked by safety rules: reg delete" in safety._blocked_command_reason("reg delete HKLM\\Software")
    assert "Command blocked by safety rules: reg import" in safety._blocked_command_reason("reg import file.reg")
    assert "Command blocked by safety rules: set-itemproperty" in safety._blocked_command_reason("set-itemproperty -Path HKCU:\\")

    # 3. System change blocks
    assert "Command blocked by safety rules: shutdown" in safety._blocked_command_reason("shutdown /s /t 0")
    assert "Command blocked by safety rules: reboot" in safety._blocked_command_reason("reboot")
    assert "Command blocked by safety rules: format" in safety._blocked_command_reason("format D:")
    assert "Command blocked by safety rules: diskpart" in safety._blocked_command_reason("diskpart")


def test_executable_paths_and_extensions():
    """Verify that safety checks handle full executable paths and extensions."""
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_service_control": False,
        "allow_registry_edit": False,
    }
    safety = DummySafety(rules)

    # Basename extraction check
    assert "Command blocked by safety rules: sc" in safety._blocked_command_reason("C:\\Windows\\System32\\sc.exe query")
    assert "Command blocked by safety rules: reg delete" in safety._blocked_command_reason("C:\\Windows\\reg.exe delete HKLM")


def test_benign_commands_allowed():
    """Verify that benign commands containing substrings are not false-blocked."""
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_service_control": False,
    }
    safety = DummySafety(rules)

    # Substrings of blocked commands should be allowed if they don't form the exact verb
    assert safety._blocked_command_reason("echo sc") == ""
    assert safety._blocked_command_reason("describe_service") == ""
    assert safety._blocked_command_reason("netcat") == ""
    assert safety._blocked_command_reason("format_disk") == ""
    # Safe commands with matched parameters inside quotes should not block the outer command
    assert safety._blocked_command_reason("echo \"sc stop spooler\"") == ""
    assert safety._blocked_command_reason("git commit -m 'net stop spooler'") == ""


def test_quote_obfuscation_detection():
    """Verify that command quote obfuscation tricks are detected and blocked."""
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_service_control": False,
    }
    safety = DummySafety(rules)

    # Obfuscated command verbs
    assert "command obfuscation detected" in safety._blocked_command_reason("s'c' query")
    assert "command obfuscation detected" in safety._blocked_command_reason("n\"e\"t stop")
    assert "command obfuscation detected" in safety._blocked_command_reason("net\"\"stop")
    
    # Benign quotes (wrapping/normal usage) should not trigger obfuscation blocks
    assert safety._blocked_command_reason("echo 'hello'") == ""
    assert safety._blocked_command_reason("echo \"hello\"") == ""
    assert safety._blocked_command_reason("dir 'C:\\Program Files'") == ""


def test_nested_execution_recursion():
    """Verify that nested wrappers (cmd, powershell, bash) are validated recursively."""
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_service_control": False,
        "allow_registry_edit": False,
    }
    safety = DummySafety(rules)

    # powershell nested checks
    assert "Command blocked by safety rules: sc" in safety._blocked_command_reason("powershell -Command \"sc stop spooler\"")
    assert "Command blocked by safety rules: sc" in safety._blocked_command_reason("pwsh -c sc stop")

    # cmd nested checks
    assert "Command blocked by safety rules: reg delete" in safety._blocked_command_reason("cmd.exe /c \"reg delete HKLM\"")
    assert "Command blocked by safety rules: reg delete" in safety._blocked_command_reason("cmd /k reg delete HKLM")

    # bash nested checks
    assert "Command blocked by safety rules: sc" in safety._blocked_command_reason("bash -c \"sc stop\"")
    assert "Command blocked by safety rules: sc" in safety._blocked_command_reason("sh -c sc")


def test_chaining_operators(monkeypatch):
    """Verify that unquoted chaining operators are blocked, while quoted ones are allowed."""
    monkeypatch.setattr(os, "name", "posix")
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_service_control": False,
    }
    safety = DummySafety(rules)

    # Chaining operators (blocked)
    assert "shell chaining operator detected" in safety._blocked_command_reason("echo hello && sc stop")
    assert "shell chaining operator detected" in safety._blocked_command_reason("echo hello; sc stop")
    assert "shell chaining operator detected" in safety._blocked_command_reason("echo hello|sc stop")
    assert "shell chaining operator detected" in safety._blocked_command_reason("echo $(whoami)")
    assert "shell chaining operator detected" in safety._blocked_command_reason("echo `whoami`")

    # Quoted chaining operators (allowed/not blocked by chaining check)
    # Note: they might be blocked by other rules if they contain blocked commands,
    # but here we check they don't trigger the "shell chaining operator detected" block.
    assert "shell chaining operator detected" not in safety._blocked_command_reason("echo \"hello && welcome\"")
    assert "shell chaining operator detected" not in safety._blocked_command_reason("echo 'hello; world'")


def test_variable_expansions():
    """Verify that environment variables are contextually blocked."""
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_service_control": False,
    }
    safety = DummySafety(rules)

    # Blocked in command verb position
    assert "environment variable expansion detected in verb position" in safety._blocked_command_reason("%COMSPEC% /c sc")
    assert "environment variable expansion detected in verb position" in safety._blocked_command_reason("$VAR stop")
    assert "environment variable expansion detected in verb position" in safety._blocked_command_reason("${VAR} start")
    assert "environment variable expansion detected in verb position" in safety._blocked_command_reason("$env:VAR start")

    # Blocked in nested wrapper parameter position
    assert "environment variable expansion detected in wrapper parameters" in safety._blocked_command_reason("powershell -c $a")
    assert "environment variable expansion detected in wrapper parameters" in safety._blocked_command_reason("cmd /c %VAR%")
    assert "environment variable expansion detected in wrapper parameters" in safety._blocked_command_reason("bash -c $VAR")

    # Allowed in normal argument position
    assert safety._blocked_command_reason("echo $PATH") == ""
    assert safety._blocked_command_reason("echo %USERNAME%") == ""


def test_escape_obfuscation_windows(monkeypatch):
    """Verify escape obfuscation detection on Windows (caret and backtick)."""
    monkeypatch.setattr(os, "name", "nt")
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_service_control": True,
    }
    safety = DummySafety(rules)

    # Windows escapes blocked
    assert "command obfuscation detected" in safety._blocked_command_reason("n^e^t stop")
    assert "command obfuscation detected" in safety._blocked_command_reason("n`e`t start")

    # Backslash is a path separator on Windows, not an escape, so allowed
    assert safety._blocked_command_reason("C:\\Windows\\System32\\sc.exe query") == ""
    assert "command obfuscation detected" not in safety._blocked_command_reason("s\\c query")


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

    # Caret and backtick are not escapes on POSIX, so not blocked as escape obfuscation
    assert "command obfuscation detected" not in safety._blocked_command_reason("n^e^t stop")
    assert "command obfuscation detected" not in safety._blocked_command_reason("n`e`t start")


# ---------------------------------------------------------------------------
# Wave 2 — Phase 3: Runner Integration tests
# ---------------------------------------------------------------------------

from pathlib import Path
from tools.terminal.runner import RunnerMixin


class DummyRunner(SafetyMixin, RunnerMixin):
    """Minimal stub combining SafetyMixin + RunnerMixin for testing.

    Overrides ``_run`` so no real subprocess is launched.
    """

    def __init__(self, rules: dict, system: str = "Windows"):
        """Initialize the dummy runner.

        Args:
            rules: The safety rules dictionary.
            system: The OS platform string.
        """
        self.rules = rules
        self.system = system
        self._env_overrides = {}

    def _run(self, command: str, timeout: int = 60, **kwargs) -> str:
        """Stub _run that only performs safety validation (no subprocess)."""
        blocked_reason = self._blocked_command_reason(command)
        if blocked_reason:
            if not blocked_reason.startswith("Command blocked by safety rules:"):
                blocked_reason = f"Command blocked by safety rules: {blocked_reason}"
            return f"Error: {blocked_reason}"
        return f"OK: {command}"


def _default_rules() -> dict:
    """Return a standard restrictive rules dict for testing."""
    return {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_registry_edit": False,
        "allow_service_control": False,
        "allow_system_changes": False,
    }


# --- Task 4: Script validation tests ---


def test_script_blocks_dangerous_sh(tmp_path):
    """Shell script containing a blocked command should be intercepted."""
    script = tmp_path / "danger.sh"
    script.write_text("#!/bin/bash\necho hello\nsc stop spooler\n", encoding="utf-8")
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "Error:" in result
    assert "blocked by safety rules" in result.lower()


def test_script_blocks_dangerous_bat(tmp_path):
    """Batch script containing a blocked command should be intercepted."""
    script = tmp_path / "danger.bat"
    script.write_text("@echo off\nreg delete HKLM\\Software\n", encoding="utf-8")
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "Error:" in result
    assert "blocked by safety rules" in result.lower()


def test_script_blocks_dangerous_ps1(tmp_path):
    """PowerShell script containing a blocked command should be intercepted."""
    script = tmp_path / "danger.ps1"
    script.write_text("# A PowerShell script\nshutdown /s /t 0\n", encoding="utf-8")
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "Error:" in result
    assert "blocked by safety rules" in result.lower()


def test_script_allows_safe_sh(tmp_path):
    """Shell script with only safe commands should execute normally."""
    script = tmp_path / "safe.sh"
    script.write_text("#!/bin/bash\necho hello\nls -la\n", encoding="utf-8")
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "OK:" in result


def test_script_skips_comments_sh(tmp_path):
    """Comments containing blocked commands should not trigger blocking."""
    script = tmp_path / "comments.sh"
    script.write_text(
        "#!/bin/bash\n# sc stop spooler\necho safe\n", encoding="utf-8"
    )
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "OK:" in result


def test_script_skips_comments_bat(tmp_path):
    """Batch REM/:: comments containing blocked commands should be skipped."""
    script = tmp_path / "comments.bat"
    script.write_text(
        "@echo off\nREM reg delete HKLM\\Software\n:: shutdown /s\necho safe\n",
        encoding="utf-8",
    )
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "OK:" in result


def test_script_skips_blank_lines(tmp_path):
    """Blank lines should be silently ignored."""
    script = tmp_path / "blanks.sh"
    script.write_text(
        "#!/bin/bash\n\n\n\necho hello\n\n", encoding="utf-8"
    )
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "OK:" in result


def test_script_line_continuation_sh(tmp_path):
    """POSIX backslash continuations should be merged before validation."""
    script = tmp_path / "cont.sh"
    # "sc \\\n stop spooler" should be reconstructed as "sc stop spooler"
    script.write_text("sc \\\nstop spooler\n", encoding="utf-8")
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "Error:" in result
    assert "blocked by safety rules" in result.lower()


def test_script_line_continuation_bat(tmp_path):
    """Batch caret continuations should be merged before validation."""
    script = tmp_path / "cont.bat"
    # "reg ^\n delete HKLM" should be reconstructed as "reg delete HKLM"
    script.write_text("reg ^\ndelete HKLM\\Software\n", encoding="utf-8")
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "Error:" in result
    assert "blocked by safety rules" in result.lower()


def test_script_line_continuation_ps1(tmp_path):
    """PowerShell backtick continuations should be merged before validation."""
    script = tmp_path / "cont.ps1"
    script.write_text("shutdown `\n/s /t 0\n", encoding="utf-8")
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    assert "Error:" in result
    assert "blocked by safety rules" in result.lower()


def test_script_python_skips_scanning(tmp_path):
    """Python scripts should not be scanned line-by-line for shell commands."""
    script = tmp_path / "dangerous.py"
    # Even though this contains "sc stop", it's a Python file — skip interior scanning.
    script.write_text("import os\nos.system('sc stop spooler')\n", encoding="utf-8")
    runner = DummyRunner(_default_rules())

    result = runner.run_script(str(script))
    # Python scripts pass through to _run which validates the wrapper "python <path>",
    # not the interior lines.
    assert "OK:" in result


def test_script_not_found():
    """Non-existent script path should return a file-not-found error."""
    runner = DummyRunner(_default_rules())
    result = runner.run_script("/nonexistent/path/foo.sh")
    assert "Error: Script not found:" in result


# --- Task 4 cont: Normalized error formatting ---


def test_run_error_format_normalized():
    """Blocked commands through _run should return the normalized error format."""
    runner = DummyRunner(_default_rules())
    result = runner._run("sc stop spooler")
    assert result.startswith("Error: Command blocked by safety rules:")


def test_run_error_format_contains_reason():
    """The error string should contain the specific blocked reason."""
    runner = DummyRunner(_default_rules())
    result = runner._run("shutdown /s /t 0")
    assert "shutdown" in result.lower()


# --- Task 4 cont: Audit logging integration ---


def test_audit_security_validation_logged(tmp_path):
    """Verify that AuditLogger.error is called with where='security_validation'."""
    import json
    from core.audit_logger import AuditLogger

    audit_dir = str(tmp_path / "audit")
    audit = AuditLogger(log_dir=audit_dir, enabled=True, fmt="jsonl", cfg={})

    # Simulate the security validation audit call from runtime.py
    obs_text = "Error: Command blocked by safety rules: sc stop is not allowed"
    audit.error("test-session", "security_validation", f"Security warning: {obs_text}")

    errors_log = Path(audit_dir) / "errors.jsonl"
    assert errors_log.exists(), "errors.jsonl should be created"

    entries = [json.loads(line) for line in errors_log.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["event"] == "error"
    assert entry["where"] == "security_validation"
    assert "blocked by safety rules" in entry["message"].lower()
    assert entry["session_id"] == "test-session"


# --- Task 5: Performance benchmark ---


def test_safety_validation_performance():
    """Verify that _blocked_command_reason executes in <10ms average over 100 iterations.

    This validates the performance constraint from the project requirements.
    """
    import time

    safety = DummySafety(_default_rules())

    # A representative mix of blocked and benign commands
    test_commands = [
        "sc stop spooler",
        "echo hello",
        "reg delete HKLM\\Software",
        "git commit -m 'update'",
        "shutdown /s /t 0",
        "ls -la",
        "net stop spooler",
        "python main.py",
        "systemctl restart nginx",
        "echo 'hello world'",
    ]

    iterations = 100
    total_time = 0.0

    for _ in range(iterations):
        for cmd in test_commands:
            start = time.perf_counter()
            safety._blocked_command_reason(cmd)
            elapsed = time.perf_counter() - start
            total_time += elapsed

    total_calls = iterations * len(test_commands)
    avg_ms = (total_time / total_calls) * 1000

    # Must be under 10ms average per call
    assert avg_ms < 10.0, (
        f"Average validation time {avg_ms:.3f}ms exceeds 10ms threshold"
    )


def test_powershell_flag_abbreviations_and_case():
    """Verify that PowerShell wrapper flags support abbreviations and case insensitivity."""
    rules = _default_rules()
    safety = DummySafety(rules)

    # PowerShell command flags
    assert safety._is_powershell_command_flag("-c")
    assert safety._is_powershell_command_flag("-co")
    assert safety._is_powershell_command_flag("-comm")
    assert safety._is_powershell_command_flag("-command")
    assert safety._is_powershell_command_flag("/command")
    assert safety._is_powershell_command_flag("-CoMmAnD")
    
    # Non-command flags starting with c
    assert not safety._is_powershell_command_flag("-config")
    
    # PowerShell encoded command flags
    assert safety._is_powershell_encoded_flag("-en")
    assert safety._is_powershell_encoded_flag("-enc")
    assert safety._is_powershell_encoded_flag("-encoded")
    assert safety._is_powershell_encoded_flag("-encodedcommand")
    assert safety._is_powershell_encoded_flag("/enc")
    assert safety._is_powershell_encoded_flag("-EnCoDeDCoMmAnD")

    # Short/ambiguous/other flags
    assert not safety._is_powershell_encoded_flag("-e")
    assert not safety._is_powershell_encoded_flag("-file")


def test_powershell_base64_encoded_blocked_commands():
    """Verify that blocked commands nested inside Base64 parameters are blocked."""
    import base64
    rules = _default_rules()
    safety = DummySafety(rules)

    # Encode "sc stop spooler" in UTF-16LE Base64
    blocked_cmd = "sc stop spooler"
    encoded_payload = base64.b64encode(blocked_cmd.encode("utf-16-le")).decode("ascii")

    # Test via powershell -encodedcommand <base64>
    command1 = f"powershell -encodedcommand {encoded_payload}"
    assert "Command blocked by safety rules: sc" in safety._blocked_command_reason(command1)

    command2 = f"powershell -enc {encoded_payload}"
    assert "Command blocked by safety rules: sc" in safety._blocked_command_reason(command2)

    # Encode a benign command: "echo hello"
    benign_cmd = "echo hello"
    benign_payload = base64.b64encode(benign_cmd.encode("utf-16-le")).decode("ascii")
    command3 = f"powershell -enc {benign_payload}"
    assert safety._blocked_command_reason(command3) == ""


def test_powershell_base64_invalid_and_variables():
    """Verify handling of invalid base64 payloads and payloads with variable expansion."""
    rules = _default_rules()
    safety = DummySafety(rules)

    # 1. Invalid base64 payload should block with base64-decode-failure warning
    command_invalid = "powershell -enc InvalidBase64Text!!!"
    assert "base64-decode-failure" in safety._blocked_command_reason(command_invalid)

    # 2. Base64 payload decoding to a command with variable expansion in verb position
    import base64
    var_cmd = "$x stop"
    encoded_var = base64.b64encode(var_cmd.encode("utf-16-le")).decode("ascii")
    command_var = f"powershell -enc {encoded_var}"
    assert "environment variable expansion detected in verb position" in safety._blocked_command_reason(command_var)


def test_zsh_script_validation(tmp_path):
    """Verify Zsh script support for line continuation and comment skipping."""
    runner = DummyRunner(_default_rules())

    # 1. Blocked command in .zsh script
    script_danger = tmp_path / "danger.zsh"
    script_danger.write_text("#!/bin/zsh\n# comment here\nsc stop spooler\n", encoding="utf-8")
    assert "blocked by safety rules" in runner.run_script(str(script_danger)).lower()

    # 2. Safe .zsh script with comment and continuation
    script_safe = tmp_path / "safe.zsh"
    script_safe.write_text("#!/bin/zsh\n# sc stop spooler\necho \\\n  \"hello\"\n", encoding="utf-8")
    assert "OK:" in runner.run_script(str(script_safe))


def test_extra_chaining_operators():
    """Verify extra shell chaining operators like subshells and backticks."""
    rules = _default_rules()
    safety = DummySafety(rules)

    # POSIX backticks subshell: blocked as chaining operator on Unix or obfuscation/escape on Windows.
    reason_backtick = safety._blocked_command_reason("echo `whoami`")
    assert "Command blocked by safety rules" in reason_backtick
    # Subshell syntax
    assert "shell chaining operator detected" in safety._blocked_command_reason("echo $(whoami)")


def test_command_verb_obfuscation():
    """Verify command verb obfuscation checks (ticks, slashes, carets, nested quotes)."""
    rules = _default_rules()
    safety = DummySafety(rules)

    # Obfuscation tricks
    assert "command obfuscation detected" in safety._blocked_command_reason("s''c query")
    assert "command obfuscation detected" in safety._blocked_command_reason("s\"\"c query")
    assert "command obfuscation detected" in safety._blocked_command_reason("s`c query")


def test_env_var_expansions_in_wrappers():
    """Verify environment variable expansions in wrapper parameters."""
    rules = _default_rules()
    safety = DummySafety(rules)

    assert "environment variable expansion detected in wrapper parameters" in safety._blocked_command_reason("powershell -c $nested_cmd")
    assert "environment variable expansion detected in wrapper parameters" in safety._blocked_command_reason("cmd /c %nested_cmd%")
