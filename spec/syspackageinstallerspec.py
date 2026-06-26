"""Tests for the sys_package_installer plugin."""
from unittest.mock import MagicMock, patch
from ops.addons.package import (
    _get_available_managers,
    checkpackagemanagers,
    installsystempackage,
)


@patch("platform.system")
@patch("shutil.which")
def test_get_available_managers_windows(mock_which, mock_system):
    """Verify available package managers detection on Windows."""
    mock_system.return_value = "Windows"
    mock_which.side_effect = lambda cmd: "C:\\Program Files\\winget.exe" if "winget" in cmd else None

    managers = _get_available_managers()
    assert managers["winget"] == "C:\\Program Files\\winget.exe"
    assert managers["choco"] == "Not Installed"


@patch("platform.system")
@patch("shutil.which")
def test_get_available_managers_darwin(mock_which, mock_system):
    """Verify Homebrew detection on macOS."""
    mock_system.return_value = "Darwin"
    mock_which.side_effect = lambda cmd: "/usr/local/cli/brew" if "brew" in cmd else None

    managers = _get_available_managers()
    assert managers["brew"] == "/usr/local/cli/brew"


@patch("platform.system")
@patch("shutil.which")
def test_get_available_managers_linux(mock_which, mock_system):
    """Verify apt-get detection on Linux."""
    mock_system.return_value = "Linux"
    mock_which.side_effect = lambda cmd: "/usr/cli/apt-get" if "apt-get" in cmd else None

    managers = _get_available_managers()
    assert managers["apt-get"] == "/usr/cli/apt-get"


@patch("platform.system")
@patch("ops.addons.package._get_available_managers")
def test_checkpackagemanagers_report(mock_managers, mock_system):
    """Verify markdown diagnostic report generation."""
    mock_system.return_value = "Windows"
    mock_managers.return_value = {
        "winget": "C:\\Program Files\\winget.exe",
        "choco": "Not Installed"
    }

    report = checkpackagemanagers()
    assert "# Cross-Platform Package Manager Diagnostic Report" in report
    assert "Operating System**: Windows" in report
    assert "WINGET**: Active" in report


@patch("subprocess.run")
@patch("platform.system")
@patch("ops.addons.package._get_available_managers")
def test_installsystempackage_windows_winget(mock_managers, mock_system, mock_run):
    """Verify autonomous installation trigger on Windows via winget."""
    mock_system.return_value = "Windows"
    mock_managers.return_value = {
        "winget": "C:\\Program Files\\winget.exe",
        "choco": "Not Installed"
    }

    mock_response = MagicMock()
    mock_response.returncode = 0
    mock_response.stdout = "Successfully installed git"
    mock_run.return_value = mock_response

    result = installsystempackage("git")
    assert "Success" in result
    assert "using Winget" in result
    mock_run.assert_called_once_with(
        ["winget", "install", "--silent", "--accept-source-agreements", "--accept-package-agreements", "git"],
        capture_output=True,
        text=True,
        timeout=180.0
    )


@patch("subprocess.run")
@patch("platform.system")
@patch("ops.addons.package._get_available_managers")
def test_installsystempackage_linux_apt(mock_managers, mock_system, mock_run):
    """Verify autonomous installation trigger on Linux via apt-get."""
    mock_system.return_value = "Linux"
    mock_managers.return_value = {
        "apt-get": "/usr/cli/apt-get"
    }

    mock_response = MagicMock()
    mock_response.returncode = 0
    mock_response.stdout = "Successfully installed ffmpeg"
    mock_run.return_value = mock_response

    result = installsystempackage("ffmpeg")
    assert "Success" in result
    assert "using apt-get" in result
    mock_run.assert_called_once_with(
        ["sudo", "apt-get", "install", "-y", "ffmpeg"],
        capture_output=True,
        text=True,
        timeout=180.0
    )
