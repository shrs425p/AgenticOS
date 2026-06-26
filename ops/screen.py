"""
AgenticOs — screen ops
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


from kernel.base import tool
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
    @tool(name="takescreenshot", desc="Take screenshot. Args: name (optional)", category="General")
    def takescreenshot(self, name: str = "") -> str:
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
            available_ops = [t for t in ["scrot", "gnome-screenshot", "import"] if shutil.which(t)]
            if not available_ops:
                return "Error: Missing screen capture ops. Please run: installsystempackage('scrot')"
            
            tool_to_use = available_ops[0]
            if tool_to_use == "scrot":
                return self._run(["scrot", path])
            elif tool_to_use == "gnome-screenshot":
                return self._run(["gnome-screenshot", "-f", path])
            else:
                return self._run(["import", "-window", "root", path])


