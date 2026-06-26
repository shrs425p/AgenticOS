"""Integration spec for terminal command safety on the host OS."""

from __future__ import annotations

import os
import shutil
import pytest
from ops.shell.safety import SafetyMixin
from ops.shell.runner import RunnerMixin


class IntegrationRunner(SafetyMixin, RunnerMixin):
    """A runner class that uses actual RunnerMixin._run to spawn subprocesses."""

    def __init__(self, rules: dict, system: str = None):
        """Initialize the integration runner.

        Args:
            rules: The safety rules dictionary.
            system: Optional OS platform name, defaults to host OS name.
        """
        self.rules = rules
        self.system = system or ("Windows" if os.name == "nt" else "Linux")
        self._env_overrides = {}


def _default_rules() -> dict:
    """Restrictive rules for testing."""
    return {
        "allow_shell_exec": True,
        "validate_commands": True,
        "allow_registry_edit": False,
        "allow_service_control": False,
        "allow_system_changes": False,
    }


# Detect available shells
has_powershell = (
    shutil.which("powershell") is not None or shutil.which("pwsh") is not None
)
has_bash = shutil.which("bash") is not None


@pytest.mark.skipif(
    not has_powershell, reason="PowerShell is not available on this host"
)
def test_integration_powershell_blocked_command():
    """Verify that runpowershell blocks service control commands on host OS."""
    runner = IntegrationRunner(_default_rules())

    # 1. Direct blocked command
    res1 = runner.runpowershell("sc query")
    assert res1.startswith("Error: Command blocked by safety rules:")
    assert "sc" in res1

    # 2. Blocked command inside powershell wrapper flag
    res2 = runner.runcommand('powershell -Command "sc stop spooler"')
    assert res2.startswith("Error: Command blocked by safety rules:")
    assert "sc" in res2


@pytest.mark.skipif(not has_bash, reason="Bash is not available on this host")
def test_integration_bash_blocked_command():
    """Verify that runcommand with bash -c blocks commands on host OS."""
    runner = IntegrationRunner(_default_rules())

    res = runner.runcommand('bash -c "sc stop"')
    assert res.startswith("Error: Command blocked by safety rules:")
    assert "sc" in res


def test_integration_benign_command_runs():
    """Verify that allowed benign commands run successfully and return output."""
    runner = IntegrationRunner(_default_rules())

    # We use a basic cross-platform compatible command
    res = runner.runcommand("echo integration_test_hello")
    assert "integration_test_hello" in res
    assert "[exit: 0]" in res
