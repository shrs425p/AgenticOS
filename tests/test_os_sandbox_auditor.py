"""Tests for the os_sandbox_auditor plugin."""
from unittest.mock import MagicMock, patch
from tools.plugins.os_sandbox_auditor import (
    _detect_runtime_path,
    _get_active_windows_windows,
    _get_active_windows_unix,
    os_sandbox_auditor,
)


def test_detect_runtime_path():
    """Verify runtime executable detection pathways."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/python"
        path = _detect_runtime_path("python")
        assert path == "/usr/bin/python"

        mock_which.return_value = None
        path = _detect_runtime_path("non_existent_binary")
        assert path == "Not Installed"


@patch("subprocess.run")
def test_get_active_windows_windows(mock_run):
    """Verify active desktop window extraction on Windows."""
    mock_response = MagicMock()
    mock_response.returncode = 0
    mock_response.stdout = "chrome::Google Chrome\ncode::Visual Studio Code\n"
    mock_run.return_value = mock_response

    windows = _get_active_windows_windows()
    assert len(windows) == 2
    assert windows[0]["process"] == "chrome"
    assert windows[0]["window_title"] == "Google Chrome"


@patch("subprocess.run")
def test_get_active_windows_unix(mock_run):
    """Verify fallback process listing on Unix platforms."""
    mock_response = MagicMock()
    mock_response.returncode = 0
    mock_response.stdout = "PID COMMAND\n100 bash --login\n200 python main.py\n"
    mock_run.return_value = mock_response

    apps = _get_active_windows_unix()
    assert len(apps) >= 1
    assert apps[0]["process"] == "100"


@patch("platform.system")
@patch("shutil.which")
@patch("subprocess.run")
def test_os_sandbox_auditor_windows(mock_run, mock_which, mock_system):
    """Verify full capability report structure under simulated Windows environment."""
    mock_system.return_value = "Windows"
    mock_which.return_value = "C:\\Python\\python.exe"

    # Mock PowerShell active windows query
    mock_ps_response = MagicMock()
    mock_ps_response.returncode = 0
    mock_ps_response.stdout = "code::Visual Studio Code"
    
    # Mock pip list response
    mock_pip_response = MagicMock()
    mock_pip_response.returncode = 0
    mock_pip_response.stdout = "requests==2.31.0\npytest==9.0.3\n"

    mock_run.side_effect = [mock_ps_response, mock_pip_response]

    report = os_sandbox_auditor()

    assert "# Cross-Platform OS & Sandbox Audit Report" in report
    assert "Operating System**: Windows" in report
    assert "Python**: Installed" in report
    assert "Active GUI Desktop Windows" in report
    assert "code` | Visual Studio Code" in report
    assert "Environment Registry Audit" in report
    assert "requests==2.31.0" in report
