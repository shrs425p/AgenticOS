"""Unit spec for the Dynamic Self-Provisioning and Auto-Compiler Engine."""
from unittest.mock import MagicMock, patch

from kernel.provision import self_provision_command, refresh_path
from ops.shell.runner import RunnerMixin

class MockTerminalTool(RunnerMixin):
    def __init__(self):
        self.system = "Windows"
        self._env_overrides = {}
        self.base_dir = "mock_workspace"

    def _blocked_command_reason(self, cmd):
        return None

def test_refresh_path():
    # Verify refresh_path runs without exceptions
    with patch("platform.system", return_value="Windows"), \
         patch("os.path.isdir", return_value=True):
        refresh_path()

def test_self_provision_command_existing():
    # If the command exists, it should return True immediately without doing anything
    with patch("shutil.which", return_value="/usr/cli/existing_cmd"):
        assert self_provision_command("existing_cmd") is True

@patch("ops.addons.package.installsystempackage")
@patch("shutil.which")
@patch("os.path.exists", return_value=False)
@patch("builtins.open")
@patch("os.makedirs")
def test_self_provision_command_missing_success(mock_makedirs, mock_open, mock_exists, mock_which, mock_install):
    # Simulate first shutil.which returns None (not found), then after install returns path (installed!)
    state = {"is_installed": False}

    def which_side_effect(cmd):
        if state["is_installed"]:
            return "/usr/cli/missing_cmd"
        return None

    def install_side_effect(cmd):
        state["is_installed"] = True
        return "Success: Installs 'missing_cmd' successfully using Winget."

    mock_which.side_effect = which_side_effect
    mock_install.side_effect = install_side_effect
    mock_install.return_value = "Success: Installs 'missing_cmd' successfully using Winget."

    assert self_provision_command("missing_cmd") is True
    mock_install.assert_called_once_with("missing_cmd")
    mock_makedirs.assert_called_once()
    assert any('automissingcmd.py' in str(call) for call in mock_open.mock_calls)

@patch("ops.addons.package.installsystempackage")
@patch("shutil.which", return_value=None)
def test_self_provision_command_missing_failure(mock_which, mock_install):
    mock_install.return_value = "Failure: package not found."
    assert self_provision_command("missing_cmd") is False

@patch("kernel.provision.self_provision_command", return_value=True)
@patch("subprocess.run")
def test_runner_self_healing_file_not_found(mock_run, mock_provision):
    # Test that FileNotFoundError triggers self-healing retry
    runner = MockTerminalTool()

    # First call raises FileNotFoundError, second call returns clean mock process
    mock_process = MagicMock()
    mock_process.stdout = "healed output"
    mock_process.stderr = ""
    mock_process.returncode = 0
    mock_run.side_effect = [FileNotFoundError("no such file"), mock_process]

    res = runner._run("missing_cliary --args")
    assert "healed output" in res
    mock_provision.assert_called_once_with("missing_cliary")

@patch("kernel.provision.self_provision_command", return_value=True)
@patch("subprocess.run")
def test_runner_self_healing_exit_code(mock_run, mock_provision):
    # Test that 9009 exit code triggers self-healing retry
    runner = MockTerminalTool()

    # First call returns exit code 9009, second call returns exit code 0
    mock_process_fail = MagicMock()
    mock_process_fail.stdout = ""
    mock_process_fail.stderr = "command not found error"
    mock_process_fail.returncode = 9009

    mock_process_ok = MagicMock()
    mock_process_ok.stdout = "healed exit output"
    mock_process_ok.stderr = ""
    mock_process_ok.returncode = 0

    mock_run.side_effect = [mock_process_fail, mock_process_ok]

    res = runner._run("missing_cliary --args")
    assert "healed exit output" in res
    mock_provision.assert_called_once_with("missing_cliary")
