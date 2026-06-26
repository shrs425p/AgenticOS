import subprocess
from core.tool_base import tool
from core.exceptions import AgentError

def check_accessibility_permission() -> bool:
    script = 'tell application "System Events" to get name of every process'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    return r.returncode == 0

def prompt_accessibility_permission() -> None:
    url = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    subprocess.run(["open", url])
    raise AgentError(
        "SECURITY_VIOLATION",
        "macOS Accessibility permission required.\n"
        "System Preferences has been opened to Privacy & Security -> Accessibility.\n"
        "Add Terminal (or the Python executable) and re-run.",
        suggestions=["Grant Accessibility permissions to the terminal/Python application running this agent."]
    )

def _guard_accessibility() -> None:
    if not check_accessibility_permission():
        prompt_accessibility_permission()

@tool(name="macos_list_windows", category="Platform")
def list_windows() -> list[str]:
    """List all foreground processes on macOS."""
    _guard_accessibility()
    script = 'tell application "System Events" to get name of every process whose background only is false'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        raise AgentError("TOOL_EXECUTION_FAILED", f"osascript failed: {r.stderr.strip()}")
    return [s.strip() for s in r.stdout.strip().split(",") if s.strip()]

@tool(name="macos_focus_window", category="Platform")
def focus_window(app_name: str) -> None:
    """Bring the application specified by app_name to the foreground."""
    _guard_accessibility()
    script = f'tell application "{app_name}" to activate'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        raise AgentError("TOOL_EXECUTION_FAILED", f"Failed to activate app {app_name}: {r.stderr.strip()}")

@tool(name="macos_click_menu_item", category="Platform")
def click_menu_item(app_name: str, menu_item: str, menu_name: str) -> None:
    """Click menu_item under menu_name in application app_name."""
    _guard_accessibility()
    script = f'''
tell application "System Events"
    tell process "{app_name}"
        click menu item "{menu_item}" of menu "{menu_name}" of menu bar 1
    end tell
end tell
'''
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        raise AgentError("TOOL_EXECUTION_FAILED", f"Failed click menu item: {r.stderr.strip()}")

@tool(name="macos_type_text", category="Platform")
def type_text(text: str) -> None:
    """Type the specified text into the currently active application."""
    _guard_accessibility()
    # Escape quotes and backslashes in AppleScript string
    escaped_text = text.replace('\\', '\\\\').replace('"', '\\"')
    script = f'''
tell application "System Events"
    keystroke "{escaped_text}"
end tell
'''
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        raise AgentError("TOOL_EXECUTION_FAILED", f"Failed type text: {r.stderr.strip()}")
