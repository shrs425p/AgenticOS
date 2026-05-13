"""
AgenticOs — screen tools
Cross-platform screen capture and window management.
Windows: uses Pillow + PowerShell
macOS:   uses screencapture / osascript
Linux:   uses scrot / gnome-screenshot / xdotool
"""

import os
import platform
import subprocess
import shutil
from datetime import datetime


class ScreenManager:
    def __init__(self, rules: dict = None, base_dir: str = "workspace"):
        self.rules = rules or {}
        self.system = platform.system()
        self.base_dir = base_dir
        self.screenshots_dir = os.path.join(base_dir, "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def _run(self, args: list, timeout: int = 15) -> str:
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode != 0:
                err = result.stderr.strip()
                return (
                    f"Error (exit {result.returncode}): {err}"
                    if err
                    else f"Exit code: {result.returncode}"
                )
            return result.stdout.strip() or "Success"
        except FileNotFoundError:
            return f"Error: Command not found: {args[0]}"
        except Exception as e:
            return f"Error: {e}"

    def _run_ps(self, cmd: str) -> str:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout.strip() or "Success"
        except Exception as e:
            return f"Error: {e}"

    def _make_name(self, name: str) -> str:
        if not name:
            name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if not name.lower().endswith((".png", ".jpg", ".jpeg")):
            name += ".png"
        return os.path.join(self.screenshots_dir, name)

    # ── Screenshot ────────────────────────────────────────────────────────────
    def take_screenshot(self, name: str = "") -> str:
        """Take a screenshot of the entire screen and save it.

        Args:
            name: Optional filename (default: screenshot_YYYYMMDD_HHMMSS.png)
        """
        path = self._make_name(name)

        if self.system == "Windows":
            try:
                from PIL import ImageGrab

                img = ImageGrab.grab()
                img.save(path)
                return f"Screenshot saved: {path}"
            except ImportError:
                # Fallback: PowerShell
                ps_cmd = f"""
Add-Type -AssemblyName System.Windows.Forms;
Add-Type -AssemblyName System.Drawing;
$bounds  = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;
$bmp     = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height);
$g       = [System.Drawing.Graphics]::FromImage($bmp);
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size);
$bmp.Save("{path}");
$g.Dispose(); $bmp.Dispose();
"""
                return self._run_ps(ps_cmd)
            except Exception as e:
                return f"Error taking screenshot: {e}"

        elif self.system == "Darwin":
            return self._run(["screencapture", "-x", path])

        else:
            # Linux
            if shutil.which("scrot"):
                return self._run(["scrot", path])
            elif shutil.which("gnome-screenshot"):
                return self._run(["gnome-screenshot", "-f", path])
            elif shutil.which("import"):  # ImageMagick
                return self._run(["import", "-window", "root", path])
            else:
                return "Error: No screenshot tool found. Install scrot: sudo apt install scrot"

    # ── Window management ─────────────────────────────────────────────────────
    def minimize_all(self) -> str:
        """Minimize all open windows to show the desktop."""
        if self.system == "Windows":
            ps_cmd = "(New-Object -ComObject Shell.Application).MinimizeAll()"
            return self._run_ps(ps_cmd)
        elif self.system == "Darwin":
            script = 'tell application "System Events" to keystroke "h" using {command down, option down}'
            return self._run(["osascript", "-e", script])
        else:
            if shutil.which("wmctrl"):
                return self._run(["wmctrl", "-k", "on"])
            elif shutil.which("xdotool"):
                return self._run(["xdotool", "key", "super+d"])
            else:
                return "Error: Install wmctrl: sudo apt install wmctrl"

    def minimize_app(self, app_name: str) -> str:
        """Minimize a specific application by name.

        Args:
            app_name: Process name or window title (e.g. 'notepad', 'chrome')
        """
        if self.system == "Windows":
            ps_cmd = f"""
$sig  = '[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);';
$type = Add-Type -MemberDefinition $sig -Name 'Win32' -Namespace 'Util' -PassThru;
$procs = Get-Process -Name "{app_name}" -ErrorAction SilentlyContinue;
if (!$procs) {{ $procs = Get-Process | Where-Object {{ $_.MainWindowTitle -like "*{app_name}*" }} }};
if ($procs) {{
    foreach ($p in $procs) {{
        if ($p.MainWindowHandle -ne 0) {{ $type::ShowWindow($p.MainWindowHandle, 6) }}
    }}
    Write-Output "Minimized {app_name}."
}} else {{ Write-Output "App not found: {app_name}" }}
"""
            return self._run_ps(ps_cmd)
        elif self.system == "Darwin":
            script = (
                f'tell application "{app_name}" to set miniaturized of windows to true'
            )
            return self._run(["osascript", "-e", script])
        else:
            if shutil.which("wmctrl"):
                result = subprocess.run(
                    ["wmctrl", "-l"], capture_output=True, text=True
                )
                for line in result.stdout.splitlines():
                    if app_name.lower() in line.lower():
                        wid = line.split()[0]
                        self._run(["wmctrl", "-i", "-r", wid, "-b", "add,hidden"])
                        return f"Minimized window matching '{app_name}'"
                return f"Window not found: {app_name}"
            elif shutil.which("xdotool"):
                return self._run(
                    [
                        "xdotool",
                        "search",
                        "--name",
                        app_name,
                        "windowminimize",
                        "--sync",
                    ]
                )
            else:
                return "Error: Install wmctrl: sudo apt install wmctrl"

    def maximize_app(self, app_name: str) -> str:
        """Maximize a specific application by name.

        Args:
            app_name: Process name or window title (e.g. 'notepad', 'chrome')
        """
        if self.system == "Windows":
            ps_cmd = f"""
$sig  = '[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);';
$type = Add-Type -MemberDefinition $sig -Name 'Win32' -Namespace 'Util' -PassThru;
$procs = Get-Process -Name "{app_name}" -ErrorAction SilentlyContinue;
if (!$procs) {{ $procs = Get-Process | Where-Object {{ $_.MainWindowTitle -like "*{app_name}*" }} }};
if ($procs) {{
    foreach ($p in $procs) {{
        if ($p.MainWindowHandle -ne 0) {{ $type::ShowWindow($p.MainWindowHandle, 3) }}
    }}
    Write-Output "Maximized {app_name}."
}} else {{ Write-Output "App not found: {app_name}" }}
"""
            return self._run_ps(ps_cmd)
        elif self.system == "Darwin":
            script = f'tell application "{app_name}" to set zoomed of windows to true'
            return self._run(["osascript", "-e", script])
        else:
            if shutil.which("wmctrl"):
                return self._run(
                    [
                        "wmctrl",
                        "-r",
                        app_name,
                        "-b",
                        "add,maximized_vert,maximized_horz",
                    ]
                )
            elif shutil.which("xdotool"):
                return self._run(
                    [
                        "xdotool",
                        "search",
                        "--name",
                        app_name,
                        "windowmaximize",
                        "--sync",
                    ]
                )
            else:
                return "Error: Install wmctrl: sudo apt install wmctrl"

    def list_windows(self, filter_str: str = "") -> str:
        """List visible application windows, optionally filtered by title."""
        filter_text = filter_str.lower().strip()

        if self.system == "Windows":
            ps_cmd = r"""
$procs = Get-Process | Where-Object { $_.MainWindowTitle -and $_.MainWindowHandle -ne 0 }
foreach ($p in $procs) {
    "{0} | PID={1} | {2}" -f $p.ProcessName, $p.Id, $p.MainWindowTitle
}
"""
            output = self._run_ps(ps_cmd)
            lines = [line for line in output.splitlines() if line.strip()]
        elif self.system == "Darwin":
            script = 'tell application "System Events" to get name of every process whose visible is true'
            output = self._run(["osascript", "-e", script])
            lines = [item.strip() for item in output.split(",") if item.strip()]
        else:
            if shutil.which("wmctrl"):
                output = self._run(["wmctrl", "-l"])
                lines = [line.strip() for line in output.splitlines() if line.strip()]
            else:
                return "Error: Install wmctrl: sudo apt install wmctrl"

        if filter_text:
            lines = [line for line in lines if filter_text in line.lower()]
        return "\n".join(lines[:100]) if lines else "No matching windows found."

    def focus_app(self, app_name: str) -> str:
        """Bring a matching application window to the foreground."""
        if self.system == "Windows":
            ps_cmd = f"""
$sig = @"
using System;
using System.Runtime.InteropServices;
public static class Win32 {{
    [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}}
"@;
Add-Type $sig -ErrorAction SilentlyContinue | Out-Null;
$procs = Get-Process -Name "{app_name}" -ErrorAction SilentlyContinue;
if (!$procs) {{ $procs = Get-Process | Where-Object {{ $_.MainWindowTitle -like "*{app_name}*" }} }};
if ($procs) {{
    foreach ($p in $procs) {{
        if ($p.MainWindowHandle -ne 0) {{
            [Win32]::ShowWindowAsync($p.MainWindowHandle, 9) | Out-Null;
            [Win32]::SetForegroundWindow($p.MainWindowHandle) | Out-Null;
            Write-Output "Focused {app_name}.";
            exit 0;
        }}
    }}
}}
Write-Output "App not found: {app_name}"
"""
            return self._run_ps(ps_cmd)
        elif self.system == "Darwin":
            script = f'tell application "{app_name}" to activate'
            return self._run(["osascript", "-e", script])
        else:
            if shutil.which("wmctrl"):
                return self._run(["wmctrl", "-a", app_name])
            elif shutil.which("xdotool"):
                return self._run(
                    [
                        "xdotool",
                        "search",
                        "--name",
                        app_name,
                        "windowactivate",
                        "--sync",
                    ]
                )
            else:
                return "Error: Install wmctrl: sudo apt install wmctrl"
