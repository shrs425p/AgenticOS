"""Module for windows_windows.py"""
from __future__ import annotations

import base64
import platform
import subprocess
import time


from core.tool_base import tool
class WindowsWindowsMixin:
    """Windows window management via PowerShell.

    Uses COM/Shell techniques rather than fragile coordinate automation.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ps_encoded(self, script: str, timeout: int = 30) -> str:
        """Run a PowerShell script safely via -EncodedCommand (avoids all quoting issues)."""
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded,
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            if out:
                return out
            if err:
                return f"[stderr] {err}"
            return "(no output)"
        except subprocess.TimeoutExpired:
            return f"Error: timed out after {timeout}s"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    def _clipboard_get_ps(self) -> str:
        """Read clipboard text via PowerShell (no dependency on ClipboardMixin)."""
        script = "Get-Clipboard"
        return self._ps_encoded(script, timeout=10)

    # ------------------------------------------------------------------
    # Window management
    # ------------------------------------------------------------------

    @tool(name="window_list", desc="List windows with titles (Windows). Args: filter_str(optional)", category="Terminal")
    def window_list(self, filter_str: str = "") -> str:
        if platform.system() != "Windows":
            return "Error: window_list is only supported on Windows."
        flt = (filter_str or "").strip()
        script = (
            f'$flt = "{flt}";\n'
            "$p = Get-Process | Where-Object { $_.MainWindowTitle -and $_.MainWindowTitle.Trim() -ne '' };\n"
            "if ($flt) { $p = $p | Where-Object { $_.MainWindowTitle -like ('*'+$flt+'*') -or $_.ProcessName -like ('*'+$flt+'*') } };\n"
            "$p | Select-Object ProcessName,Id,MainWindowTitle | Sort-Object ProcessName | Format-Table -AutoSize"
        )
        return self._ps_encoded(script, timeout=30)

    @tool(name="window_focus", desc="Focus a window by title substring (Windows). Args: title", category="Terminal")
    def window_focus(self, title: str) -> str:
        """Focus the first window whose title contains the given substring.

        Args:
            title: Substring to match against window titles (case-insensitive).
        """
        if platform.system() != "Windows":
            return "Error: window_focus is only supported on Windows."
        t = (title or "").strip()
        if not t:
            return "Error: title required."
        # Escape embedded double-quotes inside the PowerShell string literal.
        t_escaped = t.replace('"', '`"')
        script = f"""
$sig = @"
using System;
using System.Runtime.InteropServices;
public static class Win32Focus {{
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
}}
"@
Add-Type $sig -ErrorAction SilentlyContinue | Out-Null
$t = "{t_escaped}"
$p = Get-Process | Where-Object {{ $_.MainWindowTitle -like ('*'+$t+'*') }} | Select-Object -First 1
if (!$p) {{ 'Not found: ' + $t; exit 0 }}
[Win32Focus]::ShowWindowAsync($p.MainWindowHandle, 5) | Out-Null
[Win32Focus]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
'Focused: ' + $p.ProcessName + ' (' + $p.Id + ') ' + $p.MainWindowTitle
"""
        return self._ps_encoded(script, timeout=30)

    @tool(name="window_close", desc="Close a window by title substring (Windows). Args: title", category="Terminal")
    def window_close(self, title: str) -> str:
        """Close the first window whose title contains the given substring.

        Args:
            title: Substring to match against window titles (case-insensitive).
        """
        if platform.system() != "Windows":
            return "Error: window_close is only supported on Windows."
        t = (title or "").strip()
        if not t:
            return "Error: title required."
        t_escaped = t.replace('"', '`"')
        script = f"""
$t = "{t_escaped}"
$p = Get-Process | Where-Object {{ $_.MainWindowTitle -like ('*'+$t+'*') }} | Select-Object -First 1
if (!$p) {{ 'Not found: ' + $t; exit 0 }}
$null = $p.CloseMainWindow()
Start-Sleep -Milliseconds 400
if (Get-Process -Id $p.Id -ErrorAction SilentlyContinue) {{ 'Close requested, process still running.' }} else {{ 'Closed.' }}
"""
        return self._ps_encoded(script, timeout=30)

    # ------------------------------------------------------------------
    # Browser content reading
    # ------------------------------------------------------------------

    @tool(name="get_browser_url", desc="Get the current URL shown in the active browser tab. Args: browser(optional, e.g. 'brave')", category="Terminal")
    def get_browser_url(self, browser: str = "") -> str:
        """Read the URL currently shown in the active browser tab.

        Focuses the browser address bar (Ctrl+L), copies its contents, and
        returns the URL via clipboard. Works with any browser.

        Args:
            browser: Optional process/window name hint to focus first (e.g. 'brave', 'chrome').
                     If omitted, assumes the browser window is already active.
        """
        if browser:
            self.focus_app(browser)
            time.sleep(0.3)

        try:
            # Ctrl+L focuses the address bar; Ctrl+A selects all; Ctrl+C copies the URL
            self.hotkey("ctrl+l")
            time.sleep(0.25)
            self.hotkey("ctrl+a")
            time.sleep(0.1)
            self.hotkey("ctrl+c")
            time.sleep(0.35)
            url = self._clipboard_get_ps().strip()
            # Escape closes the address bar popup and restores page focus
            self.press_key("escape")
            if not url:
                return (
                    "Error: clipboard empty after Ctrl+L — is a browser window focused?"
                )
            return url
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @tool(name="browser_read_page_text", desc="Read all visible text from the active browser tab (Ctrl+A+C). Args: browser(optional)", category="Terminal")
    def browser_read_page_text(self, browser: str = "") -> str:
        """Read all visible text from the currently active browser tab.

        Selects all page content (Ctrl+A), copies it (Ctrl+C), and returns
        the clipboard text. Works best on simple pages; Gmail/SPAs may return
        partial text due to virtual DOM rendering.

        Args:
            browser: Optional process/window name hint to focus first (e.g. 'brave', 'chrome').
                     If omitted, assumes the browser window is already active.
        """
        if browser:
            self.focus_app(browser)
            time.sleep(0.4)

        # Clear clipboard first so we can detect if copy failed
        self._ps_encoded("Set-Clipboard -Value ''", timeout=5)

        self.hotkey("ctrl+a")
        time.sleep(0.3)
        self.hotkey("ctrl+c")
        time.sleep(0.5)

        text = self._clipboard_get_ps().strip()
        if not text:
            return "Error: clipboard empty — no text was copied. Is a browser/document window focused?"
        return text

    @tool(name="browser_read_selection", desc="Read the currently selected/highlighted text in the browser. Args: browser(optional)", category="Terminal")
    def browser_read_selection(self, browser: str = "") -> str:
        """Read the text currently selected/highlighted in the active browser tab.

        Copies whatever the browser has selected (Ctrl+C) and returns it from
        the clipboard. Useful for reading a specific section of a page that
        the user or agent has highlighted.

        Args:
            browser: Optional process/window name hint to focus first (e.g. 'brave', 'chrome').
                     If omitted, assumes the browser window is already active.
        """
        if browser:
            self.focus_app(browser)
            time.sleep(0.3)

        self._ps_encoded("Set-Clipboard -Value ''", timeout=5)
        self.hotkey("ctrl+c")
        time.sleep(0.4)

        text = self._clipboard_get_ps().strip()
        if not text:
            return "(no text selected)"
        return text
