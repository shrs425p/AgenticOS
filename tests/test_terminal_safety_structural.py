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
