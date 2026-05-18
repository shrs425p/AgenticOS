"""Plugin module for auditing OS environment runtimes, active window telemetry, and package registries."""
import platform
import subprocess
import shutil
from core.tool_registry import tool


def _detect_runtime_path(binary_name: str) -> str:
    """Finds the absolute path of a binary executable using shutil.which."""
    path = shutil.which(binary_name)
    return path if path else "Not Installed"


def _get_active_windows_windows() -> list:
    """Retrieves active desktop window titles on Windows via native PowerShell."""
    try:
        # PowerShell query for processes with visible main window titles
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Process | Where-Object {$_.MainWindowTitle} | ForEach-Object { \"$($_.ProcessName)::$($_.MainWindowTitle)\" }"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
        windows = []
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "::" in line:
                    proc, title = line.split("::", 1)
                    windows.append({"process": proc.strip(), "window_title": title.strip()})
        return windows
    except Exception:
        return []


def _get_active_windows_unix() -> list:
    """Fallback active process/window listing for macOS/Linux."""
    sys_name = platform.system()
    try:
        # macOS Darwin GUI Window Auditing
        if sys_name == "Darwin":
            cmd = ["osascript", "-e", 'tell application "System Events" to get name of every process whose visible is true']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
            if result.returncode == 0:
                apps = [a.strip() for a in result.stdout.strip().split(",")]
                return [{"process": app, "window_title": "Visible Desktop Application"} for app in apps if app]

        # Linux X11 GUI Window Auditing
        elif shutil.which("xdotool"):
            cmd = ["xdotool", "search", "--onlyvisible", "--class", ""]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
            windows = []
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    wid = line.strip()
                    if not wid:
                        continue
                    # Retrieve the window name
                    name_cmd = ["xdotool", "getwindowname", wid]
                    name_res = subprocess.run(name_cmd, capture_output=True, text=True, timeout=2.0)
                    # Retrieve the window class/process name
                    class_cmd = ["xdotool", "getwindowclassname", wid]
                    class_res = subprocess.run(class_cmd, capture_output=True, text=True, timeout=2.0)
                    
                    if name_res.returncode == 0:
                        wname = name_res.stdout.strip()
                        cname = class_res.stdout.strip() if class_res.returncode == 0 else "Unknown Process"
                        windows.append({"process": cname, "window_title": wname})
                return windows[:15]

        # Standard Fallback
        return []
    except Exception:
        return []


@tool(name="os_sandbox_auditor", category="System", desc="Automated description")
def os_sandbox_auditor() -> str:
    """Performs a deep audit of the host environment, runtimes, package modules, and active windows.

    Identifies installed interpreters/compilers, active GUI desktop windows,
    and returns a formatted plain-English cross-platform capability report.

    Returns:
        str: A detailed markdown capability and diagnostics report.
    """
    sys_name = platform.system()
    sys_release = platform.release()
    sys_arch = platform.machine()

    report = [
        "# Cross-Platform OS & Sandbox Audit Report",
        "",
        "## Host Telemetry Profile",
        f"- **Operating System**: {sys_name} ({sys_release})",
        f"- **Architecture**: {sys_arch}",
        f"- **Python Version**: {platform.python_version()}",
        "",
        "## Runtime Interpreter & Compiler Map",
        ""
    ]

    # Probing standard runtimes, compilers, and shells
    runtimes = ["python", "node", "git", "rustc", "go", "java", "powershell", "bash", "gcc"]
    for rt in runtimes:
        exe_name = f"{rt}.exe" if sys_name == "Windows" else rt
        path = _detect_runtime_path(exe_name)
        status = "Installed" if path != "Not Installed" else "Not Detected"
        report.append(f"- **{rt.capitalize()}**: {status} (Path: `{path}`)")

    # Probing Active GUI Applications & Desktop Windows
    report.append("\n## Active GUI Desktop Windows\n")
    if sys_name == "Windows":
        active_windows = _get_active_windows_windows()
    else:
        active_windows = _get_active_windows_unix()

    if active_windows:
        report.append("| Process Name | Window Title / Parameter |")
        report.append("| :--- | :--- |")
        for win in active_windows:
            report.append(f"| `{win['process']}` | {win['window_title']} |")
    else:
        report.append("- No active GUI desktop windows were isolated or query bypassed due to OS level constraints.")

    # Probing Python Pip Packages
    report.append("\n## Environment Registry Audit\n")
    try:
        pip_result = subprocess.run(
            ["pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        if pip_result.returncode == 0:
            packages = pip_result.stdout.splitlines()[:15]  # Top 15 installed packages
            report.append("**Top 15 Installed Pip Packages**:")
            for pkg in packages:
                report.append(f"- `{pkg}`")
        else:
            report.append("- Pip package registry query returned non-zero exit code.")
    except Exception:
        report.append("- Pip package registry query timed out or failed.")

    return "\n".join(report)
