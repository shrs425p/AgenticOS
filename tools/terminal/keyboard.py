"""
AgenticOs — keyboard shortcut and input mixin
Send hotkeys, press individual keys, type text, and simulate mouse clicks.

Windows : WScript.Shell SendKeys  +  ctypes user32 for special keys
macOS   : osascript (System Events keystroke / key code)
Linux   : xdotool (X11) or ydotool (Wayland)

SendKeys special-character reference (Windows WScript.Shell):
  Modifier prefixes : ^ = Ctrl  % = Alt  + = Shift  # = Win
  Special keys      : {ENTER} {TAB} {ESC} {SPACE} {BACKSPACE} {DELETE}
                      {UP} {DOWN} {LEFT} {RIGHT} {HOME} {END}
                      {PGUP} {PGDN} {F1}–{F24} {INS} {PRTSC}
  Literal braces    : {{}  {}}
  Repeat syntax     : {KEY n}  e.g. {DOWN 3}
"""

from __future__ import annotations

import shutil
import subprocess
import time


# ── SendKeys key-name translation table ──────────────────────────────────────
# Maps common human-friendly names → WScript.Shell SendKeys notation
_SENDKEYS_MAP: dict[str, str] = {
    # Modifiers (used as prefixes in combos)
    "ctrl": "^",
    "control": "^",
    "alt": "%",
    "shift": "+",
    "win": "#",
    "windows": "#",
    "super": "#",
    # Navigation / editing
    "enter": "{ENTER}",
    "return": "{ENTER}",
    "tab": "{TAB}",
    "esc": "{ESC}",
    "escape": "{ESC}",
    "space": " ",
    "backspace": "{BACKSPACE}",
    "bs": "{BACKSPACE}",
    "delete": "{DELETE}",
    "del": "{DELETE}",
    "insert": "{INSERT}",
    "ins": "{INSERT}",
    "home": "{HOME}",
    "end": "{END}",
    "pageup": "{PGUP}",
    "pgup": "{PGUP}",
    "pagedown": "{PGDN}",
    "pgdn": "{PGDN}",
    "up": "{UP}",
    "down": "{DOWN}",
    "left": "{LEFT}",
    "right": "{RIGHT}",
    # Function keys
    **{f"f{i}": f"{{F{i}}}" for i in range(1, 25)},
    # Misc
    "printscreen": "{PRTSC}",
    "prtsc": "{PRTSC}",
    "numlock": "{NUMLOCK}",
    "capslock": "{CAPSLOCK}",
    "scrolllock": "{SCROLLLOCK}",
    "apps": "{APPS}",  # Menu / Application key
    "pause": "{PAUSE}",
    "break": "{BREAK}",
    "plus": "{+}",  # literal + (avoids modifier interpretation)
    "caret": "{^}",  # literal ^
    "percent": "{%}",  # literal %
    "tilde": "{~}",  # literal ~
    "lbrace": "{{}",
    "rbrace": "{}}",
    "lparen": "(",
    "rparen": ")",
}

# Modifier prefix tokens (order matters: ^ % + #)
_MODIFIER_PREFIXES = {
    "ctrl": "^",
    "control": "^",
    "alt": "%",
    "shift": "+",
    "win": "#",
    "windows": "#",
    "super": "#",
}


def _combo_to_sendkeys(combo: str) -> str:
    """Convert a human combo like 'ctrl+shift+s' to WScript SendKeys notation.

    Handles:
      - Modifier+key combos   : ctrl+c  ->  ^c
      - Multi-modifier combos : ctrl+alt+del  ->  ^%{DELETE}
      - Single special keys   : f5  ->  {F5}
      - Plain characters      : a  ->  a
    """
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if not parts:
        return ""

    modifiers = ""
    key_parts = []

    for part in parts:
        if part in _MODIFIER_PREFIXES:
            modifiers += _MODIFIER_PREFIXES[part]
        else:
            key_parts.append(part)

    # Build the key string for the non-modifier parts
    if not key_parts:
        return modifiers  # shouldn't happen

    key_str = ""
    for kp in key_parts:
        if kp in _SENDKEYS_MAP:
            mapped = _SENDKEYS_MAP[kp]
            # If mapped is already a prefix char (single ^/%/+/#) don't double-wrap
            key_str += mapped
        elif len(kp) == 1:
            # Literal single character — escape special SendKeys chars
            if kp in "^%+#~(){}[]":
                key_str += f"{{{kp}}}"
            else:
                key_str += kp
        else:
            # Unknown multi-char token: treat as SendKeys {TOKEN}
            key_str += f"{{{kp.upper()}}}"

    if modifiers and key_str:
        # Modifiers apply to the whole key expression — wrap key in () if multiple chars
        if len(key_str) > 1 and not key_str.startswith("{"):
            key_str = f"({key_str})"
        return f"{modifiers}{key_str}"

    return key_str or modifiers


# ── macOS key-name → key code table (partial) ─────────────────────────────
_MACOS_KEYCODE: dict[str, int] = {
    "enter": 36,
    "return": 36,
    "tab": 48,
    "space": 49,
    "backspace": 51,
    "delete": 51,
    "esc": 53,
    "escape": 53,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
    "home": 115,
    "end": 119,
    "pageup": 116,
    "pgup": 116,
    "pagedown": 121,
    "pgdn": 121,
    "f1": 122,
    "f2": 120,
    "f3": 99,
    "f4": 118,
    "f5": 96,
    "f6": 97,
    "f7": 98,
    "f8": 100,
    "f9": 101,
    "f10": 109,
    "f11": 103,
    "f12": 111,
    "f13": 105,
    "caps lock": 57,
    "capslock": 57,
    "del": 51,
    "ins": 114,
    "insert": 114,
}


def _combo_to_osascript(combo: str) -> str:
    """Convert 'ctrl+shift+s' to an osascript keystroke or key code command."""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    modifiers: list[str] = []
    key_parts: list[str] = []

    mod_map = {
        "ctrl": "control down",
        "control": "control down",
        "alt": "option down",
        "option": "option down",
        "shift": "shift down",
        "win": "command down",
        "windows": "command down",
        "cmd": "command down",
        "command": "command down",
        "super": "command down",
    }

    for part in parts:
        if part in mod_map:
            modifiers.append(mod_map[part])
        else:
            key_parts.append(part)

    using_clause = f" using {{{', '.join(modifiers)}}}" if modifiers else ""
    key = " ".join(key_parts)

    if key in _MACOS_KEYCODE:
        code = _MACOS_KEYCODE[key]
        return f'tell application "System Events" to key code {code}{using_clause}'
    elif len(key) == 1:
        return f'tell application "System Events" to keystroke "{key}"{using_clause}'
    else:
        # Try key code by name via System Events
        return f'tell application "System Events" to key code (key code of "{key}"){using_clause}'


class KeyboardMixin:
    """Keyboard shortcut, hotkey, and text-input methods."""

    # ── internal helpers ──────────────────────────────────────────────────────

    def _sendkeys(self, keys: str, delay_ms: int = 0) -> str:
        """Send a WScript.Shell SendKeys string on Windows."""
        escaped = keys.replace('"', '\\"')
        delay_cmd = f"Start-Sleep -Milliseconds {delay_ms}; " if delay_ms > 0 else ""
        ps_cmd = (
            f"{delay_cmd}"
            f"$wsh = New-Object -ComObject WScript.Shell; "
            f'$wsh.SendKeys("{escaped}")'
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                err = result.stderr.strip()
                return f"Error: {err}" if err else f"Exit {result.returncode}"
            return "OK"
        except Exception as e:
            return f"Error: {e}"

    def _xdotool(self, *args: str) -> str:
        """Run xdotool on Linux."""
        if not shutil.which("xdotool"):
            if shutil.which("ydotool"):
                return self._ydotool(*args)
            return "Error: xdotool not installed. Run: sudo apt install xdotool"
        try:
            result = subprocess.run(
                ["xdotool", *args],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or "OK"
        except Exception as e:
            return f"Error: {e}"

    def _ydotool(self, *args: str) -> str:
        """Run ydotool on Linux (Wayland)."""
        if not shutil.which("ydotool"):
            return "Error: ydotool not installed."
        try:
            result = subprocess.run(
                ["ydotool", *args],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or "OK"
        except Exception as e:
            return f"Error: {e}"

    def _osascript(self, script: str) -> str:
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or "OK"
        except Exception as e:
            return f"Error: {e}"

    def _run_ps(self, cmd: str, timeout: int = 10) -> str:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout.strip() or "OK"
        except Exception as e:
            return f"Error: {e}"

    def _resolve_keys(self, keys: str) -> str:
        """Resolve a key name: if it's a custom key alias, return the mapped combo.

        Checks self.custom_keys (populated from config.yaml custom_keys section).
        Falls through to the raw key string if no match found.
        """
        k = (keys or "").strip()
        alias = k.lower().replace(" ", "_")
        custom = getattr(self, "custom_keys", {})
        if alias in custom:
            return custom[alias]
        return k

    def hotkey(self, keys: str, window: str = "") -> str:
        """Send a keyboard shortcut / hotkey combination.

        Args:
            keys  : Key combo OR a custom named shortcut defined in config.yaml.
                    Use + to separate modifiers and keys.
                    Examples: ctrl+c  ctrl+shift+s  alt+f4  win+d
                              screenshot  emoji_picker  my_custom_action
            window: (optional) Bring this window title to foreground first.

        Built-in shortcuts (examples):
            ctrl+c / ctrl+x / ctrl+v   Copy / Cut / Paste
            ctrl+z / ctrl+y            Undo / Redo
            ctrl+s                     Save
            ctrl+a                     Select all
            ctrl+f                     Find
            ctrl+w                     Close tab/window
            ctrl+t                     New tab
            ctrl+shift+t               Reopen closed tab
            alt+f4                     Close application
            alt+tab                    Switch window
            win+d                      Show desktop
            win+l                      Lock screen
            win+e                      File Explorer
            win+r                      Run dialog
            win+s                      Windows Search
            win+.                      Emoji picker
            win+shift+s                Snip & Sketch / screenshot
            ctrl+shift+esc             Task Manager
            ctrl+alt+delete            Security screen
            f5                         Refresh
            f11                        Fullscreen toggle
            printscreen                Screenshot

        Custom shortcuts are defined in config.yaml under 'custom_keys'.
        Use hotkey_list to see all defined custom shortcuts.
        """
        raw = (keys or "").strip()
        if not raw:
            return "Error: keys required."

        # Resolve alias → actual combo
        k = self._resolve_keys(raw)
        resolved_note = f" (alias '{raw}' → '{k}')" if k != raw else ""

        if self.system == "Windows":
            if window:
                focus_cmd = (
                    f"$wsh = New-Object -ComObject WScript.Shell; "
                    f'$wsh.AppActivate("{window}"); '
                    f"Start-Sleep -Milliseconds 300"
                )
                self._run_ps(focus_cmd)

            sendkeys_str = _combo_to_sendkeys(k)
            result = self._sendkeys(sendkeys_str)
            return f"Sent hotkey [{k}]{resolved_note} → SendKeys({sendkeys_str!r}): {result}"

        elif self.system == "Darwin":
            script = _combo_to_osascript(k)
            result = self._osascript(script)
            return f"Sent hotkey [{k}]{resolved_note}: {result}"

        else:  # Linux
            xdo_key = k.lower().replace("win+", "super+").replace("windows+", "super+")
            result = self._xdotool("key", "--clearmodifiers", xdo_key)
            return f"Sent hotkey [{k}]{resolved_note}: {result}"

    # ── custom key management ─────────────────────────────────────────────────

    def hotkey_list(self) -> str:
        """List all custom named shortcut aliases defined for this session.

        Shows both shortcuts loaded from config.yaml and any added via hotkey_set.
        """
        custom = getattr(self, "custom_keys", {})
        if not custom:
            return "No custom shortcuts defined. Add them in config.yaml under 'custom_keys' or use hotkey_set."
        lines = [f"  {name:25s} → {combo}" for name, combo in sorted(custom.items())]
        return f"Custom shortcuts ({len(custom)}):\n" + "\n".join(lines)

    def hotkey_set(self, name: str, keys: str) -> str:
        """Define or update a custom named shortcut alias for this session.

        Args:
            name: Alias name for the shortcut (e.g. 'screenshot', 'emoji', 'save_all').
                  Use underscores for multi-word names.
            keys: The key combo to bind (e.g. 'win+shift+s', 'ctrl+shift+s').

        Example:
            hotkey_set(name='screenshot', keys='win+shift+s')
            hotkey_set(name='emoji', keys='win+.')
            hotkey_set(name='lock', keys='win+l')

        Note: Changes are session-only. To persist across restarts, add to
              config.yaml under the 'custom_keys' section.
        """
        n = (name or "").strip().lower().replace(" ", "_")
        k = (keys or "").strip()
        if not n:
            return "Error: name required."
        if not k:
            return "Error: keys required."
        if not hasattr(self, "custom_keys"):
            self.custom_keys = {}
        self.custom_keys[n] = k
        return f"Custom shortcut set: '{n}' → '{k}'. Use hotkey('{n}') to trigger it."

    def hotkey_delete(self, name: str) -> str:
        """Remove a custom named shortcut alias from this session.

        Args:
            name: The alias name to remove.
        """
        n = (name or "").strip().lower().replace(" ", "_")
        if not n:
            return "Error: name required."
        custom = getattr(self, "custom_keys", {})
        if n not in custom:
            defined = ", ".join(sorted(custom.keys())) or "(none)"
            return f"No custom shortcut named '{n}'. Defined: {defined}"
        del custom[n]
        return f"Removed custom shortcut: '{n}'."

    def press_key(self, key: str, repeat: int = 1) -> str:
        """Press a single key (or repeat it N times).

        Args:
            key   : Key name. Examples: enter, tab, esc, f5, up, down,
                    left, right, home, end, delete, backspace, space,
                    pageup, pagedown, capslock, f1–f24
            repeat: How many times to press the key (default 1).
        """
        k = (key or "").strip().lower()
        if not k:
            return "Error: key required."
        try:
            n = max(1, int(repeat))
        except (TypeError, ValueError):
            n = 1

        if self.system == "Windows":
            mapped = _SENDKEYS_MAP.get(k, f"{{{k.upper()}}}")
            if n > 1 and mapped.startswith("{") and mapped.endswith("}"):
                # Use SendKeys repeat syntax {KEY n}
                inner = mapped[1:-1]
                sendkeys_str = f"{{{inner} {n}}}"
            else:
                sendkeys_str = mapped * n
            result = self._sendkeys(sendkeys_str)
            return f"Pressed [{key}] x{n}: {result}"

        elif self.system == "Darwin":
            if k in _MACOS_KEYCODE:
                code = _MACOS_KEYCODE[k]
                script = "\n".join(
                    [f'tell application "System Events" to key code {code}'] * n
                )
            else:
                script = "\n".join(
                    [f'tell application "System Events" to keystroke "{k}"'] * n
                )
            result = self._osascript(script)
            return f"Pressed [{key}] x{n}: {result}"

        else:
            xdo_key = k.replace("win", "super")
            cmds = ["key", "--clearmodifiers"] + [xdo_key] * n
            result = self._xdotool(*cmds)
            return f"Pressed [{key}] x{n}: {result}"

    def type_text(self, text: str, delay_ms: int = 0) -> str:
        """Type a string of text as keyboard input (simulates typing).

        Args:
            text    : The text to type. Supports Unicode on Windows/Linux.
            delay_ms: Delay between keystrokes in milliseconds (0 = instant).
                      Use 30–100 for more human-like typing speed.

        Note: Special characters (e.g. quotes, braces) are handled automatically.
        """
        t = text  # do NOT strip — preserve leading/trailing spaces
        if t is None:
            return "Error: text required."

        if self.system == "Windows":
            # Escape SendKeys special chars in the literal text
            safe = ""
            for ch in t:
                if ch in "^%+#~(){}[]":
                    safe += f"{{{ch}}}"
                else:
                    safe += ch
            result = self._sendkeys(safe, delay_ms=delay_ms)
            return f"Typed {len(t)} characters: {result}"

        elif self.system == "Darwin":
            # osascript keystroke handles Unicode
            escaped = t.replace('"', '\\"').replace("\\", "\\\\")
            script = f'tell application "System Events" to keystroke "{escaped}"'
            result = self._osascript(script)
            return f"Typed {len(t)} characters: {result}"

        else:
            if delay_ms > 0:
                delay_arg = ["--delay", str(delay_ms)]
            else:
                delay_arg = []
            if shutil.which("xdotool"):
                result = self._xdotool("type", "--clearmodifiers", *delay_arg, "--", t)
            else:
                result = "Error: xdotool not installed."
            return f"Typed {len(t)} characters: {result}"

    def key_down(self, key: str) -> str:
        """Hold a key down (useful for drag-and-drop or sustained modifier presses).

        Args:
            key: Key name (e.g. shift, ctrl, alt, f, a).
        """
        k = (key or "").strip().lower()
        if not k:
            return "Error: key required."

        if self.system == "Windows":
            # ctypes keybd_event for key-down without key-up
            ps_cmd = f"""
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class KBD {{
    [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);
}}
'@ -ErrorAction SilentlyContinue;
[KBD]::keybd_event({self._key_to_vk(k)}, 0, 0, 0);
"""
            return self._run_ps(ps_cmd) + f" (key_down: {key})"

        elif self.system == "Darwin":
            xk = self._darwin_mod(k)
            return self._osascript(
                f'tell application "System Events" to key down "{xk}"'
            )

        else:
            return self._xdotool("keydown", k)

    def key_up(self, key: str) -> str:
        """Release a previously held key.

        Args:
            key: Key name (e.g. shift, ctrl, alt).
        """
        k = (key or "").strip().lower()
        if not k:
            return "Error: key required."

        if self.system == "Windows":
            ps_cmd = f"""
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class KBD {{
    [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);
}}
'@ -ErrorAction SilentlyContinue;
[KBD]::keybd_event({self._key_to_vk(k)}, 0, 2, 0);
"""
            return self._run_ps(ps_cmd) + f" (key_up: {key})"

        elif self.system == "Darwin":
            xk = self._darwin_mod(k)
            return self._osascript(f'tell application "System Events" to key up "{xk}"')

        else:
            return self._xdotool("keyup", k)

    # ── mouse helpers ─────────────────────────────────────────────────────────

    def mouse_click(self, button: str = "left", x: int = -1, y: int = -1) -> str:
        """Simulate a mouse click, optionally at screen coordinates.

        Args:
            button: 'left', 'right', or 'middle' (default: left).
            x     : Screen X coordinate (-1 = current position).
            y     : Screen Y coordinate (-1 = current position).
        """
        btn = (button or "left").strip().lower()
        btn_map = {"left": 1, "right": 2, "middle": 3}
        if btn not in btn_map:
            return f"Error: button must be left/right/middle, got '{btn}'."

        if self.system == "Windows":

            btn_down = (
                0x0002 if btn == "left" else (0x0008 if btn == "right" else 0x0020)
            )
            btn_up = 0x0004 if btn == "left" else (0x0010 if btn == "right" else 0x0040)

            ps_cmd = f"""
Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue | Out-Null;
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class Mouse {{
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, int dwExtraInfo);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
}}
'@ -ErrorAction SilentlyContinue;
{"[Mouse]::SetCursorPos(" + str(x) + ", " + str(y) + ");" if x >= 0 and y >= 0 else ""}
[Mouse]::mouse_event({btn_down}, 0, 0, 0, 0);
Start-Sleep -Milliseconds 50;
[Mouse]::mouse_event({btn_up}, 0, 0, 0, 0);
Write-Output "Clicked {btn} at ({x if x >= 0 else "current"}, {y if y >= 0 else "current"})."
"""
            return self._run_ps(ps_cmd)

        elif self.system == "Darwin":
            if x >= 0 and y >= 0:
                script = f'tell application "System Events" to click at {{{x}, {y}}}'
            else:
                script = 'tell application "System Events" to click'
            return self._osascript(script)

        else:
            btn_num = str(btn_map[btn])
            if x >= 0 and y >= 0:
                result = self._xdotool("mousemove", str(x), str(y))
            result = self._xdotool("click", btn_num)
            return f"Clicked {btn}: {result}"

    def mouse_move(self, x: int, y: int) -> str:
        """Move the mouse cursor to absolute screen coordinates.

        Args:
            x: Screen X coordinate in pixels.
            y: Screen Y coordinate in pixels.
        """
        if self.system == "Windows":
            ps_cmd = f"""
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public class Mouse {{
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
}}
'@ -ErrorAction SilentlyContinue;
[Mouse]::SetCursorPos({x}, {y}) | Out-Null;
Write-Output "Moved to ({x}, {y})."
"""
            return self._run_ps(ps_cmd)
        elif self.system == "Darwin":
            return self._osascript(
                f'tell application "System Events" to set mouse position to {{{x}, {y}}}'
            )
        else:
            return self._xdotool("mousemove", str(x), str(y))

    def mouse_scroll(self, direction: str = "down", clicks: int = 3) -> str:
        """Scroll the mouse wheel.

        Args:
            direction: 'up' or 'down' (default: down).
            clicks   : Number of scroll steps (default: 3).
        """
        d = (direction or "down").strip().lower()
        if d not in ("up", "down"):
            return "Error: direction must be 'up' or 'down'."
        try:
            n = max(1, int(clicks))
        except (TypeError, ValueError):
            n = 3

        if self.system == "Windows":
            delta = 120 * n * (1 if d == "up" else -1)
            ps_cmd = f"""
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public class Mouse {{
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, int dwExtraInfo);
}}
'@ -ErrorAction SilentlyContinue;
[Mouse]::mouse_event(0x0800, 0, 0, {delta}, 0);
Write-Output "Scrolled {d} {n} click(s)."
"""
            return self._run_ps(ps_cmd)
        elif self.system == "Darwin":
            amt = n if d == "up" else -n
            return self._osascript(
                f'tell application "System Events" to scroll (get mouse position) by {amt}'
            )
        else:
            btn = "4" if d == "up" else "5"
            for _ in range(n):
                self._xdotool("click", btn)
            return f"Scrolled {d} {n} click(s)"

    # ── utility (VK codes for ctypes) ─────────────────────────────────────────

    def _key_to_vk(self, key: str) -> int:
        """Map key name to Windows Virtual Key code integer."""
        vk_table: dict[str, int] = {
            "shift": 0x10,
            "ctrl": 0x11,
            "control": 0x11,
            "alt": 0x12,
            "win": 0x5B,
            "windows": 0x5B,
            "enter": 0x0D,
            "return": 0x0D,
            "tab": 0x09,
            "esc": 0x1B,
            "escape": 0x1B,
            "space": 0x20,
            "backspace": 0x08,
            "delete": 0x2E,
            "insert": 0x2D,
            "home": 0x24,
            "end": 0x23,
            "pageup": 0x21,
            "pagedown": 0x22,
            "up": 0x26,
            "down": 0x28,
            "left": 0x25,
            "right": 0x27,
            **{f"f{i}": 0x6F + i for i in range(1, 25)},
            "capslock": 0x14,
            "numlock": 0x90,
            "scrolllock": 0x91,
        }
        k = key.lower()
        if k in vk_table:
            return vk_table[k]
        if len(k) == 1:
            return ord(k.upper())
        return 0

    def _darwin_mod(self, key: str) -> str:
        """Map modifier name to macOS AppleScript key name."""
        return {
            "ctrl": "control",
            "alt": "option",
            "win": "command",
            "super": "command",
        }.get(key, key)

    # ── window-focus helper ───────────────────────────────────────────────────

    def focus_window_and_hotkey(self, window: str, keys: str) -> str:
        """Focus a window by title and then send a hotkey.

        Args:
            window: Partial window title to match and bring to foreground.
            keys  : Key combo to send (e.g. ctrl+s, f5).

        Useful for sending shortcuts to a specific app without clicking manually.
        """
        w = (window or "").strip()
        k = (keys or "").strip()
        if not w or not k:
            return "Error: window and keys are required."

        if self.system == "Windows":
            sendkeys_str = _combo_to_sendkeys(k)
            ps_cmd = (
                f"$wsh = New-Object -ComObject WScript.Shell; "
                f'$wsh.AppActivate("{w}"); '
                f"Start-Sleep -Milliseconds 400; "
                f'$wsh.SendKeys("{sendkeys_str}")'
            )
            result = self._run_ps(ps_cmd)
            return f"Focused '{w}' and sent [{k}]: {result}"
        elif self.system == "Darwin":
            activate = f'tell application "{w}" to activate'
            self._osascript(activate)
            time.sleep(0.4)
            return self.hotkey(k)
        else:
            focus = self._xdotool("search", "--name", w, "windowactivate", "--sync")
            time.sleep(0.3)
            result = self.hotkey(k)
            return f"Focused '{w}' ({focus}) and sent [{k}]: {result}"
