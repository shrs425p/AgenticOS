import pytest
import os
import pathlib
from unittest.mock import MagicMock
from ops.shell.safety import SafetyMixin, RegistryGuard
from kernel.errors import AgentError, ErrorCode
from kernel.guard import resolve_with_symlink_depth

class DummySafetyWithConfig(SafetyMixin):
    def __init__(self, rules: dict, cfg: dict = None, system: str = None):
        self.rules = rules
        self.cfg = cfg or {}
        self.guard = None
        if system is not None:
            self.system = system

def test_registry_guard_rules():
    # Test normalisation
    guard = RegistryGuard({})
    assert guard.normalize_key("HKEY_LOCAL_MACHINE\\Software\\Test") == "HKLM\\SOFTWARE\\TEST"
    assert guard.normalize_key("HKCU:\\Software\\Test") == "HKCU\\SOFTWARE\\TEST"
    assert guard.normalize_key("registry::HKLM/Software/Test") == "HKLM\\SOFTWARE\\TEST"

    # Test allowed keys
    cfg = {
        "registry_policies": {
            "allowed_keys": ["HKCU\\Software\\AgenticOS\\*"],
            "blocked_keys": ["HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\*"],
            "approval_required_keys": ["HKLM\\Software\\*"]
        }
    }
    guard = RegistryGuard(cfg)
    
    # 1. Allowed key
    allowed, msg = guard.check_key("HKCU\\Software\\AgenticOS\\settings")
    assert allowed is True
    
    # 2. Explicitly blocked key (default)
    allowed, msg = guard.check_key("HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\MyBackdoor")
    assert allowed is False
    assert "strictly blocked" in msg or "explicitly blocked" in msg

    # 3. Approval required key
    allowed, msg = guard.check_key("HKLM\\Software\\Test")
    assert allowed is False
    assert msg == "HITM_REQUIRED"


def test_registry_guard_command_intercept():
    # Setup safety class with policies
    cfg = {
        "registry_policies": {
            "allowed_keys": ["HKCU\\Software\\AgenticOS\\*"],
            "blocked_keys": ["HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\*"],
            "approval_required_keys": ["HKLM\\Software\\*"]
        }
    }
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_registry_edit": True,
    }
    safety = DummySafetyWithConfig(rules, cfg, system="Windows")
    
    # Mock human guard
    mock_guard = MagicMock()
    mock_guard.ask_human.return_value = True
    safety.guard = mock_guard

    # 1. Blocked key modification
    reason = safety._blocked_command_reason("reg add HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\Backdoor")
    assert "blocked" in reason

    # 2. Allowed key modification
    reason = safety._blocked_command_reason("reg add HKCU\\Software\\AgenticOS\\settings")
    assert reason == ""

    # 3. Approval required key modification (approved)
    mock_guard.ask_human.return_value = True
    reason = safety._blocked_command_reason("reg add HKLM\\Software\\AppKey")
    assert reason == ""
    mock_guard.ask_human.assert_called_with("HKLM\\Software\\AppKey", "registry_edit")

    # 4. Approval required key modification (denied)
    mock_guard.ask_human.reset_mock()
    mock_guard.ask_human.return_value = False
    reason = safety._blocked_command_reason("reg add HKLM\\Software\\AppKey")
    assert "denied" in reason or "blocked" in reason
    mock_guard.ask_human.assert_called_with("HKLM\\Software\\AppKey", "registry_edit")

    # 5. PowerShell cmdlet
    reason = safety._blocked_command_reason("Set-ItemProperty -Path HKLM\\Software\\AppKey -Name Test")
    # should ask human
    mock_guard.ask_human.assert_called_with("HKLM\\Software\\AppKey", "registry_edit")


def test_agent_error_attributes():
    err = AgentError(
        code=ErrorCode.REGISTRY_TAMPERING,
        message="Attempt to tamper with registry",
        recovery_feasible=True,
        suggestions=["Restore registry backup", "Verify caller permissions"],
        original_exception=ValueError("Invalid key")
    )
    assert err.code == ErrorCode.REGISTRY_TAMPERING
    assert err.message == "Attempt to tamper with registry"
    assert err.recovery_feasible is True
    assert "Restore registry backup" in err.suggestions
    assert isinstance(err.original_exception, ValueError)
    
    d = err.to_dict()
    assert d["code"] == ErrorCode.REGISTRY_TAMPERING
    assert d["recovery_feasible"] is True
    assert "Invalid key" in d["original_exception"]

    s = str(err)
    assert "AgentError [REGISTRY_TAMPERING]" in s
    assert "Restore registry backup" in s


def test_unicode_and_redirection_guards():
    # Setup dummy safety
    rules = {
        "allow_shell_exec": True,
        "validate_commands": True,
    }
    safety = DummySafetyWithConfig(rules)
    
    # 1. Unicode obfuscation test
    reason = safety._blocked_command_reason("powershell -c \"echo \\u0041\"")
    assert "Unicode escape sequence detected" in reason

    # 2. Hex obfuscation test
    reason = safety._blocked_command_reason("powershell -c \"echo \\x41\"")
    assert "Hex character escape sequence detected" in reason

    # 3. PowerShell char cast test
    reason = safety._blocked_command_reason("powershell -c \"[char]0x41\"")
    assert "PowerShell character cast detected" in reason

    # 4. Redirection to script outside workspace
    mock_guard = MagicMock()
    mock_guard.check_path.return_value = (False, "outside workspace")
    safety.guard = mock_guard
    
    reason = safety._blocked_command_reason("echo payload > C:\\Windows\\System32\\exploit.ps1")
    assert "blocked writing script outside workspace" in reason or "denied" in reason


def test_symlink_depth_validation(monkeypatch):
    monkeypatch.setattr(pathlib.Path, "is_symlink", lambda self: True)
    monkeypatch.setattr(os, "readlink", lambda path: "test_link")
    # Mock resolve to avoid calling real resolve on the path
    monkeypatch.setattr(pathlib.Path, "resolve", lambda self, *args, **kwargs: self)
    
    with pytest.raises(ValueError) as exc:
        resolve_with_symlink_depth(pathlib.Path("test_link"), max_depth=5)
    
    assert "Symlink traversal depth exceeded limit of 5" in str(exc.value)
