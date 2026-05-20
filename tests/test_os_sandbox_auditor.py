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


@patch("core.platform_api.PlatformAPI.run_powershell")
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


@patch("platform.system")
@patch("subprocess.run")
def test_get_active_windows_unix_darwin(mock_run, mock_system):
    """Verify Darwin active application window query via AppleScript."""
    mock_system.return_value = "Darwin"
    mock_response = MagicMock()
    mock_response.returncode = 0
    mock_response.stdout = "Spotify, Finder, Terminal"
    mock_run.return_value = mock_response

    apps = _get_active_windows_unix()
    assert len(apps) == 3
    assert apps[0]["process"] == "Spotify"
    assert apps[0]["window_title"] == "Visible Desktop Application"


@patch("platform.system")
@patch("shutil.which")
@patch("subprocess.run")
def test_get_active_windows_unix_linux(mock_run, mock_which, mock_system):
    """Verify Linux active application window query via xdotool."""
    mock_system.return_value = "Linux"
    mock_which.return_value = "/usr/bin/xdotool"

    mock_search = MagicMock()
    mock_search.returncode = 0
    mock_search.stdout = "12345\n"

    mock_name = MagicMock()
    mock_name.returncode = 0
    mock_name.stdout = "My Window Title"

    mock_class = MagicMock()
    mock_class.returncode = 0
    mock_class.stdout = "MyClassName"

    mock_run.side_effect = [mock_search, mock_name, mock_class]

    apps = _get_active_windows_unix()
    assert len(apps) == 1
    assert apps[0]["process"] == "MyClassName"
    assert apps[0]["window_title"] == "My Window Title"


@patch("platform.system")
@patch("shutil.which")
@patch("subprocess.run")
@patch("core.platform_api.PlatformAPI.run_powershell")
def test_os_sandbox_auditor_windows(mock_ps_run, mock_run, mock_which, mock_system):
    """Verify full capability report structure under simulated Windows environment."""
    mock_system.return_value = "Windows"
    mock_which.return_value = "C:\\Python\\python.exe"

    # Mock PowerShell active windows query
    mock_ps_response = MagicMock()
    mock_ps_response.returncode = 0
    mock_ps_response.stdout = "code::Visual Studio Code"
    mock_ps_run.return_value = mock_ps_response
    
    # Mock pip list response
    mock_pip_response = MagicMock()
    mock_pip_response.returncode = 0
    mock_pip_response.stdout = "requests==2.31.0\npytest==9.0.3\n"

    mock_run.return_value = mock_pip_response

    report = os_sandbox_auditor()

    assert "# Cross-Platform OS & Sandbox Audit Report" in report
    assert "Operating System**: Windows" in report
    assert "Python**: Installed" in report
    assert "Active GUI Desktop Windows" in report
    assert "code` | Visual Studio Code" in report
    assert "Environment Registry Audit" in report
    assert "requests==2.31.0" in report
