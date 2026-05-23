"""Plugin module for unified cross-platform system package manager probing and installation."""
import platform
import shutil
import subprocess
from core.tool_registry import tool


def _get_available_managers() -> dict:
    """Probes the host operating system to identify active package managers."""
    sys_name = platform.system()
    managers = {}

    if sys_name == "Windows":
        # Check Winget
        winget_path = shutil.which("winget")
        managers["winget"] = winget_path if winget_path else "Not Installed"
        # Check Chocolatey
        choco_path = shutil.which("choco")
        managers["choco"] = choco_path if choco_path else "Not Installed"
    elif sys_name == "Darwin":
        # Check Homebrew
        brew_path = shutil.which("brew")
        managers["brew"] = brew_path if brew_path else "Not Installed"
    else:
        # Linux package managers
        for pm in ["apt-get", "apt", "dnf", "yum", "pacman", "apk"]:
            path = shutil.which(pm)
            if path:
                managers[pm] = path

    return managers


@tool(name="check_package_managers", category="System", desc="Identify available system package managers (e.g. winget, brew, apt) on the host machine.")
def check_package_managers() -> str:
    """Probes and identifies available package managers on the host machine.

    Returns:
        str: A markdown report of available package managers and their installation paths.
    """
    sys_name = platform.system()
    managers = _get_available_managers()

    report = [
        "# Cross-Platform Package Manager Diagnostic Report",
        "",
        f"- **Operating System**: {sys_name}",
        "",
        "## Discovered Package Managers",
        ""
    ]

    active_pms = [pm for pm, path in managers.items() if path != "Not Installed"]

    if active_pms:
        for pm in active_pms:
            report.append(f"- [X] **{pm.upper()}**: Active (Path: `{managers[pm]}`)")
    else:
        report.append("- [ ] **No active system package managers detected on the current user path.**")

    return "\n".join(report)


@tool(name="install_system_package", category="System", desc="Autonomously install system utilities (e.g. git, ffmpeg) using the local package manager.")
def install_system_package(package_name: str) -> str:
    """Autonomously installs a system utility package using the preferred local manager.

    Args:
        package_name (str): Name of the package to install (e.g. 'ffmpeg', 'git', 'curl').

    Returns:
        str: The outcome details of the installation attempt.
    """
    sys_name = platform.system()
    managers = _get_available_managers()
    pkg = package_name.strip()

    if sys_name == "Windows":
        # Prefer Winget, then Choco
        if managers.get("winget") and managers["winget"] != "Not Installed":
            # winget install --silent --accept-source-agreements --accept-package-agreements
            cmd = ["winget", "install", "--silent", "--accept-source-agreements", "--accept-package-agreements", pkg]
            manager_used = "Winget"
        elif managers.get("choco") and managers["choco"] != "Not Installed":
            # choco install -y
            cmd = ["choco", "install", "-y", pkg]
            manager_used = "Chocolatey"
        else:
            return "Error: Neither 'winget' nor 'choco' package manager is installed or accessible on Windows."

    elif sys_name == "Darwin":
        if managers.get("brew") and managers["brew"] != "Not Installed":
            # brew install
            cmd = ["brew", "install", pkg]
            manager_used = "Homebrew"
        else:
            return "Error: Homebrew ('brew') is not installed or accessible on macOS."

    else:
        # Linux
        supported_pms = ["apt-get", "apt", "dnf", "yum", "pacman", "apk"]
        manager_used = None
        for pm in supported_pms:
            if pm in managers:
                manager_used = pm
                break

        if not manager_used:
            return "Error: No supported Linux package manager (apt, dnf, yum, pacman, apk) was detected."

        if manager_used in ["apt-get", "apt"]:
            cmd = ["sudo", manager_used, "install", "-y", pkg]
        elif manager_used in ["dnf", "yum"]:
            cmd = ["sudo", manager_used, "install", "-y", pkg]
        elif manager_used == "pacman":
            cmd = ["sudo", "pacman", "-S", "--noconfirm", pkg]
        elif manager_used == "apk":
            cmd = ["sudo", "apk", "add", pkg]
        else:
            cmd = [manager_used, "install", pkg]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180.0)
        if result.returncode == 0:
            return f"Success: Installs '{pkg}' successfully using {manager_used}.\nOutput:\n{result.stdout.strip()}"
        else:
            return f"Failure: Installation command failed (Exit code: {result.returncode}) using {manager_used}.\nError:\n{result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return f"Failure: Installation command for '{pkg}' timed out using {manager_used} after 180 seconds."
    except Exception as e:
        return f"Failure: System exception occurred during installation: {str(e)}"
