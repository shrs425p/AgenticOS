"""Tests for the sys_package_installer plugin."""
from unittest.mock import MagicMock, patch
from tools.plugins.sys_package_installer import (
    _get_available_managers,
    check_package_managers,
    install_system_package,
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
    mock_which.side_effect = lambda cmd: "/usr/local/bin/brew" if "brew" in cmd else None

    managers = _get_available_managers()
    assert managers["brew"] == "/usr/local/bin/brew"


@patch("platform.system")
@patch("shutil.which")
def test_get_available_managers_linux(mock_which, mock_system):
    """Verify apt-get detection on Linux."""
    mock_system.return_value = "Linux"
    mock_which.side_effect = lambda cmd: "/usr/bin/apt-get" if "apt-get" in cmd else None

    managers = _get_available_managers()
    assert managers["apt-get"] == "/usr/bin/apt-get"


@patch("platform.system")
@patch("tools.plugins.sys_package_installer._get_available_managers")
def test_check_package_managers_report(mock_managers, mock_system):
    """Verify markdown diagnostic report generation."""
    mock_system.return_value = "Windows"
    mock_managers.return_value = {
        "winget": "C:\\Program Files\\winget.exe",
        "choco": "Not Installed"
    }

    report = check_package_managers()
    assert "# Cross-Platform Package Manager Diagnostic Report" in report
    assert "Operating System**: Windows" in report
    assert "WINGET**: Active" in report


@patch("subprocess.run")
@patch("platform.system")
@patch("tools.plugins.sys_package_installer._get_available_managers")
def test_install_system_package_windows_winget(mock_managers, mock_system, mock_run):
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

    result = install_system_package("git")
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
@patch("tools.plugins.sys_package_installer._get_available_managers")
def test_install_system_package_linux_apt(mock_managers, mock_system, mock_run):
    """Verify autonomous installation trigger on Linux via apt-get."""
    mock_system.return_value = "Linux"
    mock_managers.return_value = {
        "apt-get": "/usr/bin/apt-get"
    }

    mock_response = MagicMock()
    mock_response.returncode = 0
    mock_response.stdout = "Successfully installed ffmpeg"
    mock_run.return_value = mock_response

    result = install_system_package("ffmpeg")
    assert "Success" in result
    assert "using apt-get" in result
    mock_run.assert_called_once_with(
        ["sudo", "apt-get", "install", "-y", "ffmpeg"],
        capture_output=True,
        text=True,
        timeout=180.0
    )
