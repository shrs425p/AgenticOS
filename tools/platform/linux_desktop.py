import os
import shutil
import subprocess
from core.tool_base import tool
from core.exceptions import AgentError

def detect_linux_session() -> dict:
    """Returns {'session_type': 'wayland'|'x11'|'unknown', 'desktop': str, 'display': str}"""
    xdg_type = os.environ.get("XDG_SESSION_TYPE", "").lower()   # wayland / x11 / mir
    wayland_display = os.environ.get("WAYLAND_DISPLAY", "")      # e.g. wayland-0
    x11_display = os.environ.get("DISPLAY", "")                  # e.g. :0
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()  # gnome / kde / i3 / sway

    # Primary: trust $XDG_SESSION_TYPE
    if xdg_type in ("wayland", "x11"):
        return {"session_type": xdg_type, "desktop": desktop, "display": wayland_display or x11_display}

    # Fallback: other env vars
    if wayland_display:
        return {"session_type": "wayland", "desktop": desktop, "display": wayland_display}
    if x11_display:
        return {"session_type": "x11", "desktop": desktop, "display": x11_display}

    # Runtime probe: Wayland socket existence
    try:
        uid = os.getuid()
        if os.path.exists(f"/run/user/{uid}/wayland-0"):
            return {"session_type": "wayland", "desktop": desktop, "display": "wayland-0"}
    except AttributeError:
        pass # getuid not available on Windows/etc.

    return {"session_type": "unknown", "desktop": desktop, "display": ""}

def classify_desktop(desktop_env: str) -> str:
    """Returns 'gnome' | 'kde' | 'i3' | 'sway' | 'xfce' | 'lxde' | 'unknown'"""
    d = desktop_env.lower()
    if "gnome" in d: return "gnome"
    if "kde" in d:   return "kde"
    if "i3" in d:    return "i3"
    if "sway" in d:  return "sway"
    if "xfce" in d:  return "xfce"
    if "lxde" in d:  return "lxde"
    return "unknown"

def screenshot_wayland(output_path: str, monitor: str = "") -> str:
    if not shutil.which("grim"):
        raise AgentError(
            "TOOL_EXECUTION_FAILED",
            "grim not found. Install with: sudo apt install grim\n"
            "On Arch: sudo pacman -S grim\n"
            "On GNOME Wayland also install: xdg-desktop-portal-gnome",
            suggestions=["sudo apt install grim", "sudo pacman -S grim"]
        )
    cmd = ["grim"] + (["-o", monitor] if monitor else []) + [output_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise AgentError("TOOL_EXECUTION_FAILED", f"grim failed: {r.stderr.strip()}")
    return output_path

def screenshot_x11(output_path: str) -> str:
    if not shutil.which("scrot"):
        raise AgentError(
            "TOOL_EXECUTION_FAILED",
            "scrot not found. Install with: sudo apt install scrot\n"
            "On Arch: sudo pacman -S scrot",
            suggestions=["sudo apt install scrot", "sudo pacman -S scrot"]
        )
    r = subprocess.run(["scrot", output_path], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise AgentError("TOOL_EXECUTION_FAILED", f"scrot failed: {r.stderr.strip()}")
    return output_path

@tool(name="linux_take_screenshot", category="Platform")
def take_screenshot(output_path: str, monitor: str = "") -> str:
    """Take a screenshot on Linux using grim or scrot."""
    session = detect_linux_session()
    if session["session_type"] == "wayland":
        return screenshot_wayland(output_path, monitor)
    elif session["session_type"] == "x11":
        return screenshot_x11(output_path)
    else:
        if shutil.which("grim"):    return screenshot_wayland(output_path)
        elif shutil.which("scrot"): return screenshot_x11(output_path)
        raise AgentError(
            "TOOL_EXECUTION_FAILED",
            "No screenshot tool found. Install grim (Wayland) or scrot (X11).",
            suggestions=["Install grim or scrot via your package manager."]
        )
