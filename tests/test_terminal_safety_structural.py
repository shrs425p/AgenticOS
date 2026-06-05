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
