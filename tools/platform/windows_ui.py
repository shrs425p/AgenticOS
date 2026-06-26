import time
from core.tool_base import tool
from core.exceptions import AgentError

try:
    import win32gui
    import win32process
    import win32security
    import win32api
    import win32con
    import win32com.client as win32com_client
    import ntsecuritycon
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False

def _is_hwnd_elevated(hwnd: int) -> bool:
    if not _HAS_WIN32:
        return False
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        token = win32security.OpenProcessToken(proc, ntsecuritycon.TOKEN_QUERY)
        elevation = win32security.GetTokenInformation(token, win32security.TokenElevation)
        return bool(elevation)
    except Exception:
        return False

@tool(name="windows_list_windows", category="Platform")
def list_windows() -> list[dict]:
    """List all top-level visible windows with their hwnds and titles."""
    if not _HAS_WIN32:
        raise AgentError("SYSTEM_CRASH", "pywin32 is not installed or available on this platform.")
    
    results = []
    def _enum_callback(hwnd, res):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            if title:
                res.append({"hwnd": hwnd, "title": title, "class": cls})
    win32gui.EnumWindows(_enum_callback, results)
    return results

@tool(name="windows_focus_window", category="Platform")
def focus_window(hwnd: int) -> None:
    """Bring the window specified by hwnd to the foreground."""
    if not _HAS_WIN32:
        raise AgentError("SYSTEM_CRASH", "pywin32 is not installed or available on this platform.")
    
    if _is_hwnd_elevated(hwnd):
        raise AgentError(
            "SECURITY_VIOLATION",
            "Window is UAC-elevated. Re-run AgenticOS as Administrator to control it.",
            suggestions=["Run your command prompt/terminal as Administrator and restart the agent."]
        )
    
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.05)
    except Exception as e:
        raise AgentError("TOOL_EXECUTION_FAILED", f"Failed to focus window: {str(e)}", original_exception=e)

@tool(name="windows_click_at", category="Platform")
def click_at(x: int, y: int) -> None:
    """Click mouse at absolute screen coordinates (x, y)."""
    if _HAS_WIN32:
        try:
            win32api.SetCursorPos((x, y))
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
        except Exception as e:
            raise AgentError("TOOL_EXECUTION_FAILED", f"Failed click via win32: {str(e)}", original_exception=e)
    elif _HAS_PYAUTOGUI:
        try:
            pyautogui.click(x, y)
        except Exception as e:
            raise AgentError("TOOL_EXECUTION_FAILED", f"Failed click via pyautogui: {str(e)}", original_exception=e)
    else:
        raise AgentError("SYSTEM_CRASH", "Neither pywin32 nor pyautogui is available.")

@tool(name="windows_type_text", category="Platform")
def type_text(text: str) -> None:
    """Type the specified text into the currently active window."""
    if _HAS_WIN32:
        try:
            shell = win32com_client.Dispatch("WScript.Shell")
            # Escape special SendKeys characters: +, ^, %, ~, {, }, [, ]
            safe_chars = []
            for char in text:
                if char in "+^%~{}[]":
                    safe_chars.append(f"{{{char}}}")
                else:
                    safe_chars.append(char)
            safe = "".join(safe_chars)
            shell.SendKeys(safe, 0)
        except Exception as e:
            raise AgentError("TOOL_EXECUTION_FAILED", f"Failed type via win32 SendKeys: {str(e)}", original_exception=e)
    elif _HAS_PYAUTOGUI:
        try:
            pyautogui.typewrite(text)
        except Exception as e:
            raise AgentError("TOOL_EXECUTION_FAILED", f"Failed type via pyautogui: {str(e)}", original_exception=e)
    else:
        raise AgentError("SYSTEM_CRASH", "Neither pywin32 nor pyautogui is available.")
