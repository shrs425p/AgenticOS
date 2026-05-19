import platform
import subprocess
import os
import shutil
from typing import Any, Optional

class PlatformAPI:
    """Platform abstraction layer for OS-specific calls."""

    @staticmethod
    def is_windows() -> bool:
        return platform.system() == "Windows"

    @staticmethod
    def is_mac() -> bool:
        return platform.system() == "Darwin"

    @staticmethod
    def is_linux() -> bool:
        return platform.system() == "Linux"

    @staticmethod
    def run_powershell(script: str, **kwargs: Any) -> subprocess.CompletedProcess:
        """Runs a PowerShell script using subprocess.run."""
        if not PlatformAPI.is_windows() and not shutil.which("powershell"):
            raise EnvironmentError("PowerShell is not available on this platform.")
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
        return subprocess.run(cmd, **kwargs)

    @staticmethod
    def check_output_powershell(script: str, **kwargs: Any) -> str:
        """Runs a PowerShell script using subprocess.check_output."""
        if not PlatformAPI.is_windows() and not shutil.which("powershell"):
            raise EnvironmentError("PowerShell is not available on this platform.")
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
        return subprocess.check_output(cmd, **kwargs)

    @staticmethod
    def popen_powershell(script: str, **kwargs: Any) -> subprocess.Popen:
        """Starts a PowerShell script using subprocess.Popen."""
        if not PlatformAPI.is_windows() and not shutil.which("powershell"):
            raise EnvironmentError("PowerShell is not available on this platform.")
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
        return subprocess.Popen(cmd, **kwargs)

    @staticmethod
    def find_windows_app(app_name: str) -> Optional[str]:
        """Finds a Windows app using Registry App Paths and Start Menu shortcuts."""
        if not PlatformAPI.is_windows():
            return None

        name = (app_name or "").strip().strip('"').strip("'")
        if not name:
            return None

        exe = name
        if not exe.lower().endswith(".exe") and " " not in exe and "\\" not in exe:
            exe = exe + ".exe"

        # Registry App Paths
        try:
            import winreg

            sub = r"Software\Microsoft\Windows\CurrentVersion\App Paths"
            candidates = [
                (winreg.HKEY_CURRENT_USER, f"{sub}\\{exe}"),
                (winreg.HKEY_LOCAL_MACHINE, f"{sub}\\{exe}"),
                (winreg.HKEY_CURRENT_USER, f"{sub}\\{name}"),
                (winreg.HKEY_LOCAL_MACHINE, f"{sub}\\{name}"),
            ]
            for root, key in candidates:
                try:
                    with winreg.OpenKey(root, key) as h:
                        val, _ = winreg.QueryValueEx(h, "")
                        if val and os.path.exists(val):
                            return val
                except (OSError, EnvironmentError):
                    continue
        except (OSError, EnvironmentError, ImportError):
            pass

        # Start Menu shortcuts by name
        try:
            start_dirs = [
                os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
                os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
            ]
            needle = (name or "").lower()
            for sd in start_dirs:
                if not sd or not os.path.isdir(sd):
                    continue
                for root, _dirs, files in os.walk(sd):
                    for fn in files:
                        if not fn.lower().endswith(".lnk"):
                            continue
                        if needle and needle not in fn.lower():
                            continue
                        p = os.path.join(root, fn)
                        if os.path.exists(p):
                            return p
        except (OSError, FileNotFoundError):
            pass

        return None
