---
phase: 3
phase_name: Platform OS Control and Autonomy Framework
slug: 03-platform-os-control-and-autonomy-framework
date: 2026-06-26
status: research_complete
---

# Phase 3 Research: Platform OS Control and Autonomy Framework

## Orientation

Phase 3 delivers three capability clusters on top of the existing codebase:

1. **Native OS UI control** — Windows (`ops/platform/windows_ui.py`), macOS (`ops/platform/macos_ui.py`), Linux (`ops/platform/linux_desktop.py`)
2. **Hardware-aware auto-tuning** — `kernel/resources.py` + integration points in `kernel/dispatch.py`, `kernel/context.py`, `kernel/models.py`
3. **Autonomous task resilience** — `kernel/checkpoint.py`, `kernel/triage.py`, `kernel/stalls.py`

All new ops live in `ops/platform/` and must use the `@tool` decorator from `kernel/base.py`. All new kernel modules are plain Python files; no framework changes required.

---

## Area 1: Windows UI Control (`ops/platform/windows_ui.py`)

### pywin32 Status

`pywin32` is **not** in `requirements.txt` (confirmed: `grep -i pywin32 requirements.txt` → no results). Add as a platform-conditional dependency:

```
pywin32>=306; sys_platform == 'win32'
```

`pyautogui==0.9.54` is already in `requirements.txt` and serves as a cross-platform fallback for click/type if `pywin32` is absent. `Pillow==12.2.0` is also present for screenshot post-processing.

### Core API Surface

| pywin32 call | Purpose |
|---|---|
| `win32gui.EnumWindows(callback, lParam)` | Enumerate all top-level windows |
| `win32gui.GetWindowText(hwnd)` | Get window title string |
| `win32gui.GetClassName(hwnd)` | Get window class name (for filtering) |
| `win32gui.IsWindowVisible(hwnd)` | Filter invisible/hidden windows |
| `win32gui.SetForegroundWindow(hwnd)` | Bring window to front |
| `win32gui.GetWindowRect(hwnd)` | Get bounding box `(left, top, right, bottom)` |
| `win32gui.IsIconic(hwnd)` | Check if window is minimized |
| `win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)` | Restore minimized window |
| `win32api.SetCursorPos((x, y))` | Move mouse to absolute screen coordinates |
| `win32api.mouse_event(flags, dx, dy, data, info)` | Fire mouse button events |
| `win32con.MOUSEEVENTF_LEFTDOWN / MOUSEEVENTF_LEFTUP` | Mouse button event flags |
| `win32com.client.Dispatch("WScript.Shell")` | COM automation for SendKeys |

### Enumerate Windows Pattern

```python
import win32gui

def _enum_callback(hwnd, results):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        if title:
            results.append({"hwnd": hwnd, "title": title, "class": cls})

def list_windows() -> list[dict]:
    results = []
    win32gui.EnumWindows(_enum_callback, results)
    return results
```

**Gotcha**: `EnumWindows` only enumerates top-level windows. For MDI child windows use `win32gui.EnumChildWindows(parent_hwnd, callback, lParam)`.

### Focus and Click Pattern

```python
import win32gui, win32api, win32con, time

def focus_window(hwnd: int) -> None:
    """Bring a window to foreground."""
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.05)  # let Windows process the focus change

def click_at(x: int, y: int) -> None:
    """Click at absolute screen coordinates."""
    win32api.SetCursorPos((x, y))
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
```

### Typing Text with SendKeys

```python
import win32com.client

def typetext(text: str) -> None:
    """Type text into the focused window using WScript.Shell SendKeys."""
    shell = win32com.client.Dispatch("WScript.Shell")
    # Escape special SendKeys chars: +, ^, %, ~, {, }, [, ]
    safe = text.replace("+", "{+}").replace("^", "{^}").replace("%", "{%}")
    shell.SendKeys(safe, 0)  # 0 = no wait
```

**Gotcha**: `SendKeys` is unreliable with apps that use direct keyboard hooks (e.g., games, some terminals). For those, fallback to `win32api.keybd_event(vk_code, scan_code, flags, info)` with `win32con.VK_*` constants.

### UAC-Elevated Windows (Critical Gotcha)

UAC-elevated windows (admin processes) cannot receive `SetForegroundWindow` or `SendKeys` from a non-elevated caller — Windows silently ignores the call with no error code.

**Detection**:
```python
def _is_hwnd_elevated(hwnd: int) -> bool:
    import win32process, win32security, win32api, ntsecuritycon
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        token = win32security.OpenProcessToken(proc, ntsecuritycon.TOKEN_QUERY)
        elevation = win32security.GetTokenInformation(token, win32security.TokenElevation)
        return bool(elevation)
    except Exception:
        return False
```

If elevated, raise `AgentError("Window is UAC-elevated. Re-run AgenticOS as Administrator to control it.")`.

### pyautogui Fallback

```python
try:
    import win32gui
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False
# If not _HAS_WIN32: pyautogui.click(x, y) for click_at, pyautogui.typewrite(text) for typetext
```

### File Structure

```
ops/platform/__init__.py    # OS dispatcher (cross-cutting)
ops/platform/windows_ui.py  # New file for this area
```

All functions in `windows_ui.py` wrapped with `@tool(name=..., category="platform")` from `kernel/base.py`.

---

## Area 2: macOS UI Control (`ops/platform/macos_ui.py`)

### Primary Mechanism: osascript subprocess

No new pip dependencies needed — `osascript` is always present on macOS. All calls:
```python
subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
```

### Key AppleScript Patterns

**List all foreground processes:**
```applescript
tell application "System Events" to get name of every process whose background only is false
```

**Python wrapper:**
```python
import subprocess

def list_windows() -> list[str]:
    script = 'tell application "System Events" to get name of every process whose background only is false'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        raise AgentError(f"osascript failed: {r.stderr.strip()}")
    return [s.strip() for s in r.stdout.strip().split(",") if s.strip()]
```

**Focus by app name:**
```applescript
tell application "Safari" to activate
```

**Click menu item:**
```applescript
tell application "System Events"
    tell process "Safari"
        click menu item "New Tab" of menu "File" of menu bar 1
    end tell
end tell
```

**Keystroke (Cmd+A):**
```applescript
tell application "System Events"
    keystroke "a" using {command down}
end tell
```

**Type text:**
```applescript
tell application "System Events"
    keystroke "Hello World"
end tell
```

### Accessibility Permissions Check

Without Accessibility permission: `osascript: OpenDefaultConnection: pid XXXXX is not trusted`

**Detection:**
```python
def check_accessibility_permission() -> bool:
    script = 'tell application "System Events" to get name of every process'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    return r.returncode == 0
```

**Auto-prompt (open System Preferences):**
```python
def prompt_accessibility_permission() -> None:
    url = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    subprocess.run(["open", url])
    raise AgentError(
        "macOS Accessibility permission required.\n"
        "System Preferences has been opened to Privacy & Security -> Accessibility.\n"
        "Add Terminal (or the Python executable) and re-run."
    )
```

**Optional pyobjc path:**
```python
try:
    from ApplicationServices import AXIsProcessTrusted
    _AX_TRUSTED = AXIsProcessTrusted()
except ImportError:
    _AX_TRUSTED = None  # fall back to osascript check
```

### Optional pyobjc: Quartz Window List

```python
# pyobjc-framework-Quartz — optional, NOT in base requirements.txt
# Requires Screen Recording permission (not Accessibility) on macOS 10.15+
import Quartz

def list_windows_quartz() -> list[dict]:
    opts = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    windows = Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID)
    return [
        {"pid": w.get("kCGWindowOwnerPID"), "name": w.get("kCGWindowOwnerName"),
         "title": w.get("kCGWindowName", ""), "layer": w.get("kCGWindowLayer")}
        for w in windows
    ]
```

**Gotcha**: Quartz requires Screen Recording permission; osascript requires only Accessibility. These are different macOS permission categories.

---

## Area 3: Linux Desktop Detection & Screenshots (`ops/platform/linux_desktop.py`)

### Detection Strategy: Layered env-var + socket probe

```python
import os, shutil, subprocess

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
    uid = os.getuid()
    if os.path.exists(f"/run/user/{uid}/wayland-0"):
        return {"session_type": "wayland", "desktop": desktop, "display": "wayland-0"}

    return {"session_type": "unknown", "desktop": desktop, "display": ""}
```

### Desktop Environment Classification

```python
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
```

### Screenshot Dispatch

**Wayland (grim):**
```python
def screenshot_wayland(output_path: str, monitor: str = "") -> str:
    if not shutil.which("grim"):
        raise AgentError(
            "grim not found. Install with: sudo apt install grim\n"
            "On Arch: sudo pacman -S grim\n"
            "On GNOME Wayland also install: xdg-desktop-portal-gnome"
        )
    cmd = ["grim"] + (["-o", monitor] if monitor else []) + [output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise AgentError(f"grim failed: {r.stderr.strip()}")
    return output_path
```

**X11 (scrot):**
```python
def screenshot_x11(output_path: str) -> str:
    if not shutil.which("scrot"):
        raise AgentError(
            "scrot not found. Install with: sudo apt install scrot\n"
            "On Arch: sudo pacman -S scrot"
        )
    r = subprocess.run(["scrot", output_path], capture_output=True, text=True)
    if r.returncode != 0:
        raise AgentError(f"scrot failed: {r.stderr.strip()}")
    return output_path
```

**Dispatcher:**
```python
def takescreenshot(output_path: str, monitor: str = "") -> str:
    session = detect_linux_session()
    if session["session_type"] == "wayland":
        return screenshot_wayland(output_path, monitor)
    elif session["session_type"] == "x11":
        return screenshot_x11(output_path)
    else:
        if shutil.which("grim"):    return screenshot_wayland(output_path)
        elif shutil.which("scrot"): return screenshot_x11(output_path)
        raise AgentError("No screenshot tool found. Install grim (Wayland) or scrot (X11).")
```

### AgentError

`kernel/errors.py` currently only defines `RateLimitExhausted`. Add `AgentError` (QUAL-04) if Phase 1 did not already do so:
```python
class AgentError(Exception):
    def __init__(self, message: str, code: str = "AGENT_ERR"):
        super().__init__(message)
        self.code = code
```

---

## Area 4: Hardware Auto-Tuner (`kernel/resources.py`)

### psutil API Used

`psutil==5.9.8` is already in `requirements.txt`. Key calls:
- `psutil.virtual_memory()` → `.total` (bytes), `.available` (bytes), `.percent` (float)
- `psutil.cpu_count(logical=True)` → int (hyper-threading counted)
- `psutil.disk_usage(path)` → `.free` (bytes)

### HardwareProfile Dataclass

```python
from dataclasses import dataclass

@dataclass
class HardwareProfile:
    ram_tier: str            # "low" | "mid" | "high"
    cpu_count: int           # logical CPUs
    available_ram_gb: float  # available at profile time
    total_ram_gb: float      # total installed
    recommended_max_workers: int    # for ParallelScheduler
    recommended_context_tokens: int # for Ollama num_ctx / ContextEngine
    recommended_cache_mb: int       # disk cache budget in MB
    compact_history_threshold: int  # max messages before compact_history fires
```

### RAM Tier Thresholds & Recommended Values

| Tier | Total RAM | max_workers | context_tokens | cache_mb | compact_threshold |
|---|---|---|---|---|---|
| `low` | ≤ 4 GB | 2 | 8192 | 128 | 15 |
| `mid` | > 4 GB and ≤ 16 GB | 4 | 32768 | 512 | 30 |
| `high` | > 16 GB | `cpu_count` | 131072 | 2048 | 60 |

### profile_hardware() Function

```python
import psutil

def profile_hardware() -> HardwareProfile:
    """Run once at startup."""
    vm = psutil.virtual_memory()
    total_gb = vm.total / (1024 ** 3)
    available_gb = vm.available / (1024 ** 3)
    cpu = psutil.cpu_count(logical=True) or 2

    if total_gb <= 4.0:
        tier, workers, ctx, cache, compact = "low", 2, 8192, 128, 15
    elif total_gb <= 16.0:
        tier, workers, ctx, cache, compact = "mid", 4, 32768, 512, 30
    else:
        tier, workers, ctx, cache, compact = "high", cpu, 131072, 2048, 60

    return HardwareProfile(
        ram_tier=tier, cpu_count=cpu,
        available_ram_gb=round(available_gb, 2), total_ram_gb=round(total_gb, 2),
        recommended_max_workers=workers, recommended_context_tokens=ctx,
        recommended_cache_mb=cache, compact_history_threshold=compact,
    )
```

### Dynamic Throttle (every 60s during long tasks)

```python
def check_memory_pressure(current_workers: int) -> int:
    """If RAM use exceeds 80%, halve worker count (minimum 1)."""
    if psutil.virtual_memory().percent > 80:
        return max(1, current_workers // 2)
    return current_workers
```

### Integration Points

**`kernel/dispatch.py` — ParallelScheduler.max_workers (line 328)**:
`ParallelScheduler.__init__` currently has `max_workers: int = 4`. At agent init:
```python
from kernel.resources import profile_hardware
self.hw_profile = profile_hardware()
self.scheduler = ParallelScheduler(max_workers=self.hw_profile.recommended_max_workers)
```

**`kernel/context.py` — compact_history threshold**:
`kernel/cli.py` line 552: `max_msgs = int(self.performance.get("max_context_messages", 40))`. Override at init:
```python
self.performance["max_context_messages"] = self.hw_profile.compact_history_threshold
```

Note: The 80% token trigger (`context_engine.py` line 249: `trigger_tokens = int(max_tokens * 0.8)`) is independent — it fires on token count. `compact_history_threshold` only controls the message-count trigger. Both can fire independently.

**`kernel/models.py` — Ollama num_ctx**:
`ContextEngine.get_max_context_tokens` reads `cfg["ollama"]["num_ctx"]` (line 221). Override at init:
```python
self.cfg.setdefault("ollama", {})["num_ctx"] = self.hw_profile.recommended_context_tokens
```

---

## Area 5: Checkpoint Manager (`kernel/checkpoint.py`)

### Existing TaskTracker — Key Facts

File: `kernel/tasks.py` (351 lines). Key methods:
- `__init__(workspace, session_id, cfg)` — stores in `workspace/tasks/active_task_{session_id}.json`
- `start(goal, provider, model)` — creates task with `datetime.now().strftime("%Y%m%d_%H%M%S")` as task_id
- `update_from_response(response, iteration)` — parses OBJECTIVE/PLAN/CURRENT_STEP sections
- `record_action(tool_name, args)` — appends to `actions_taken` list with timestamp
- `record_observation(observation)` — updates `last_observation`
- `complete(final_answer)` — sets `status="completed"`
- `fail(message)` — sets `status="failed"`
- `note_stall(message)` — increments `stall_count`

`CheckpointManager` is a **separate parallel system**:
- `TaskTracker` = per-session runtime tracking (in-memory + JSON, reset each session)
- `CheckpointManager` = cross-session persistence with stable goal-hash IDs

Do not modify `TaskTracker`. Initialize both independently.

### Checkpoint Schema

```json
{
    "task_id": "a3f9e2b1c47d",
    "goal": "Refactor auth module",
    "phases": [
        {
            "name": "Phase 1: Analysis",
            "status": "complete",
            "steps": ["Read auth module source", "Identify coupling points"],
            "result": "Found 3 modules to split"
        },
        {
            "name": "Phase 2: Implementation",
            "status": "running",
            "steps": ["Split auth.py", "Update imports", "Run spec"],
            "result": null
        }
    ],
    "created_at": "2026-06-26T10:00:00",
    "updated_at": "2026-06-26T17:30:00"
}
```

Valid phase `status` values: `"pending"`, `"running"`, `"complete"`.

### Goal Hashing for Stable Task IDs

```python
import hashlib

def _goal_to_task_id(goal: str) -> str:
    """Produce a stable 12-char hex ID from the goal string."""
    return hashlib.sha256(goal.strip().lower().encode("utf-8")).hexdigest()[:12]
```

**Critical**: Normalize (strip + lowercase) before hashing so minor whitespace reformatting still resolves to the same checkpoint.

### CheckpointManager Class

```python
import os, json
from datetime import datetime

class CheckpointManager:
    def __init__(self, workspace: str):
        self.workspace = workspace
        self.checkpoints_dir = os.path.join(workspace, ".checkpoints")
        os.makedirs(self.checkpoints_dir, exist_ok=True)

    def _path(self, task_id: str) -> str:
        return os.path.join(self.checkpoints_dir, f"{task_id}.json")

    def create(self, goal: str, phases: list[dict]) -> str:
        """Create a new checkpoint. Returns task_id."""
        task_id = _goal_to_task_id(goal)
        now = datetime.now().isoformat()
        data = {"task_id": task_id, "goal": goal, "phases": phases,
                "created_at": now, "updated_at": now}
        with open(self._path(task_id), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return task_id

    def load(self, goal: str) -> dict | None:
        """Load checkpoint by goal hash. Returns None if not found."""
        task_id = _goal_to_task_id(goal)
        path = self._path(task_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def update_phase(self, task_id: str, phase_name: str, status: str, result: str | None = None) -> None:
        path = self._path(task_id)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for phase in data["phases"]:
            if phase["name"] == phase_name:
                phase["status"] = status
                if result is not None:
                    phase["result"] = result
                break
        data["updated_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def next_pending_phase(self, task_id: str) -> dict | None:
        """Return first phase with status != 'complete'. Returns None if all done."""
        path = self._path(task_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for phase in data["phases"]:
            if phase.get("status") != "complete":
                return phase
        return None
```

### SQLite Secondary Storage

The existing `SqliteSessionMemory` in `kernel/store.py` manages messages/tasks/artifacts for the current session. Mixing checkpoint data into it creates coupling.

**Recommended**: Separate SQLite at `workspace/.checkpoints/checkpoints.sqlite3`:

```python
import sqlite3

def _init_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
          task_id TEXT PRIMARY KEY,
          goal TEXT NOT NULL,
          phase_count INTEGER NOT NULL DEFAULT 0,
          completed_phases INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'running',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
```

The existing `SqliteSessionMemory.start_task(task_id, goal)` and `complete_task(task_id, ...)` (lines 336-402) can optionally be called for cross-session task indexing if needed, but this is not required for Phase 3.

### Resume Logic at Task Start

In `Agent.run()` (`kernel/cli.py`), after reading `user_input`:
```python
checkpoint = self.checkpoint_manager.load(user_input)
if checkpoint:
    pending = self.checkpoint_manager.next_pending_phase(checkpoint["task_id"])
    if pending:
        print(f"Resuming '{checkpoint['goal'][:60]}...' from: {pending['name']}")
        user_input += f"\n\n[RESUME: Continue from phase '{pending['name']}'. Previous phases complete.]"
```

---

## Area 6: Retry Classifier & Stall Monitor

### Existing Loop Guard — Do Not Modify

In `kernel/cli.py`, `repeated_action_count` logic at lines **558–746**:
- **Line 558**: `repeated_action_count = 0` — initialized per `run()` call
- **Line 731**: `current_signature = "||".join([f"{t}|{args}" for t, args in actions])` — action fingerprint
- **Lines 732–736**: Increments if signature matches `last_action_signature`; resets to 0 on new signature
- **Line 738**: `if repeated_action_count >= 2:` — blocks identical sequence, injects "Blocked repeated action sequence" observation

**Relationship**: `repeated_action_count` = loop guard. `RetryClassifier` = error router for tool execution failures. Different failure modes, different layers. Do not modify the existing guard.

### RetryClassifier (`kernel/triage.py`)

```python
from dataclasses import dataclass
import re

@dataclass
class RetryDecision:
    action: str      # "retry" | "abandon" | "escalate"
    reason: str
    max_retries: int

class RetryClassifier:
    TRANSIENT_PATTERNS = [
        r"timeout", r"timed out", r"network", r"connection reset",
        r"connection refused", r"locked", r"temporarily unavailable",
        r"retry", r"\b503\b", r"\b429\b", r"ETIMEDOUT", r"ECONNREFUSED",
        r"rate limit", r"too many requests", r"service unavailable",
        r"resource temporarily unavailable",
    ]
    PERMANENT_PATTERNS = [
        r"permission denied", r"not found", r"no such file",
        r"syntax error", r"invalid argument", r"invalid syntax",
        r"ENOENT", r"\bEPERM\b", r"\bEACCES\b",
        r"not a valid", r"unrecognized", r"command not found",
        r"module not found", r"no module named",
    ]
    PERMANENT_EXIT_CODES = {1, 2, 127, 128, 130}

    def __init__(self):
        self._transient_re = re.compile("|".join(self.TRANSIENT_PATTERNS), re.IGNORECASE)
        self._permanent_re = re.compile("|".join(self.PERMANENT_PATTERNS), re.IGNORECASE)

    def classify(self, error_msg: str, exit_code: int | None = None) -> RetryDecision:
        """Classify error into retry | abandon | escalate.

        Exit code is primary signal (most reliable). Message patterns are fallback.
        Default for ambiguous: retry 2 times then escalate.
        """
        if exit_code is not None and exit_code in self.PERMANENT_EXIT_CODES:
            return RetryDecision(action="abandon", reason=f"Exit code {exit_code} is permanent", max_retries=0)

        is_transient = bool(self._transient_re.search(error_msg))
        is_permanent = bool(self._permanent_re.search(error_msg))

        if is_permanent and not is_transient:
            return RetryDecision(action="abandon", reason="Permanent error pattern in message", max_retries=0)
        if is_transient:
            return RetryDecision(action="retry", reason="Transient error — will retry", max_retries=3)

        # Ambiguous
        return RetryDecision(action="escalate", reason="Ambiguous error — escalating after 2 retries", max_retries=2)
```

**Scope**: Tool execution errors only. LLM API errors handled by `FallbackRouter` (kernel/models.py) + `retry_call` (kernel/retry.py). Do not overlap.

### StallMonitor (`kernel/stalls.py`)

```python
import time
from dataclasses import dataclass

@dataclass
class StallWarning:
    tool_name: str
    elapsed_seconds: float
    threshold_seconds: float
    suggestion: str  # faster alternative

class StallMonitor:
    THRESHOLDS = {
        "file_ops": 30,           # read_file, write_file, list_dir, copy_file
        "network": 60,            # fetchurl, http_request, websearch
        "package_install": 300,   # pip, npm, apt
        "general": 120,           # runcommand, execute_code, default
    }
    TOOL_CATEGORIES = {
        "read_file": "file_ops", "write_file": "file_ops",
        "list_dir": "file_ops",  "copy_file": "file_ops",
        "fetchurl": "network",  "http_request": "network", "websearch": "network",
        "runcommand": "general", "execute_code": "general",
    }
    FASTER_ALTERNATIVES = {
        "copy_file":        "Archive large directories with `tar czf` first, then copy the archive",
        "runcommand:grep": "Use `rg` (ripgrep) instead of grep — 10-100x faster on large codebases",
        "runcommand:find": "Use `fd` instead of `find` — faster and respects .gitignore",
        "fetchurl":        "Cache responses locally with save_file if repeatedly fetching",
        "runcommand:pip":  "Add --find-links /tmp/pip-cache or --no-build-isolation to speed up",
        "runcommand:npm":  "Use --prefer-offline if packages are already cached locally",
        "runcommand:du":   "Use `dust` (Rust du) for large directories — significantly faster",
        "runcommand:sort": "Pipe through LC_ALL=C sort for ASCII data — 3x faster",
        "runcommand:awk":  "Use `mlr` (Miller) for structured CSV data — faster and cleaner",
        "runcommand:sed":  "Use `sd` (Rust sed) for large files — simpler syntax and faster",
    }

    def __init__(self):
        self._timers: dict[str, float] = {}

    def start(self, tool_name: str) -> None:
        self._timers[tool_name] = time.monotonic()

    def check_stall(self, tool_name: str) -> "StallWarning | None":
        """Returns StallWarning if tool has exceeded its category threshold."""
        if tool_name not in self._timers:
            return None
        elapsed = time.monotonic() - self._timers[tool_name]
        category = self.TOOL_CATEGORIES.get(tool_name, "general")
        threshold = self.THRESHOLDS.get(category, 120)
        if elapsed >= threshold:
            suggestion = self.FASTER_ALTERNATIVES.get(tool_name, "")
            if not suggestion:
                for k, v in self.FASTER_ALTERNATIVES.items():
                    if tool_name.startswith(k):
                        suggestion = v
                        break
            suggestion = suggestion or "Consider breaking this operation into smaller chunks."
            return StallWarning(tool_name, elapsed, threshold, suggestion)
        return None

    def stop(self, tool_name: str) -> None:
        self._timers.pop(tool_name, None)
```

### Success Criteria Parser (AUTO-02)

```python
import re

_CRITERIA_PATTERNS = [
    re.compile(r"verify\s+that\s+(.+?)(?:[,.]|$)", re.IGNORECASE),
    re.compile(r"make\s+sure\s+(?:that\s+)?(.+?)(?:[,.]|$)", re.IGNORECASE),
    re.compile(r"confirm\s+(?:that\s+)?(.+?)(?:[,.]|$)", re.IGNORECASE),
    re.compile(r"check\s+that\s+(.+?)(?:[,.]|$)", re.IGNORECASE),
    re.compile(r"ensure\s+(?:that\s+)?(.+?)(?:[,.]|$)", re.IGNORECASE),
]

def parse_success_criteria(goal: str) -> list[str]:
    """Extract success criteria phrases like 'verify that X', 'ensure Y' from a goal."""
    criteria = []
    for pattern in _CRITERIA_PATTERNS:
        for m in pattern.finditer(goal):
            criterion = m.group(1).strip().rstrip(".,:;")
            if criterion and len(criterion) > 5:
                criteria.append(criterion)
    return criteria
```

**Integration**: At FINAL ANSWER handling in `kernel/cli.py`, before breaking the loop:
```python
criteria = parse_success_criteria(original_user_input)
if criteria:
    unverified = [c for c in criteria if c.lower() not in response.lower()]
    if unverified:
        nudge = "Before terminating, verify these criteria are met:\n" + "\n".join(f"- {c}" for c in unverified)
        messages.append({"role": "user", "content": nudge})
        continue  # Re-enter loop to verify
```

---

## Validation Architecture

### Area 1: Windows UI Tools (no real Windows GUI)

Mock `win32gui`, `win32api`, `win32com`, `win32con`, `win32process`, `win32security` in `sys.modules` **before** importing the module under test:

```python
# spec/platform/test_windows_ui.py
import sys
from unittest.mock import MagicMock

for mod in ["win32gui", "win32api", "win32com", "win32com.client",
            "win32con", "win32process", "win32security", "ntsecuritycon"]:
    sys.modules[mod] = MagicMock()

from ops.platform.windows_ui import list_windows

def test_list_windows():
    import win32gui
    win32gui.IsWindowVisible.return_value = True
    win32gui.GetWindowText.return_value = "Notepad"
    win32gui.GetClassName.return_value = "Notepad"
    win32gui.EnumWindows.side_effect = lambda cb, lst: cb(12345, lst)
    result = list_windows()
    assert result[0]["hwnd"] == 12345
    assert result[0]["title"] == "Notepad"
```

Key: Install mocks **before** import; use `side_effect` to simulate callback-based APIs.

### Area 2: macOS Tools (non-Mac)

Mock `subprocess.run` return values:
```python
from unittest.mock import patch, MagicMock

def test_list_windows_parses_csv():
    r = MagicMock(returncode=0, stdout="Safari, Terminal, Finder\n")
    with patch("subprocess.run", return_value=r):
        from ops.platform.macos_ui import list_windows
        assert list_windows() == ["Safari", "Terminal", "Finder"]

def test_accessibility_check_false_on_error():
    r = MagicMock(returncode=1, stderr="not trusted")
    with patch("subprocess.run", return_value=r):
        from ops.platform.macos_ui import check_accessibility_permission
        assert check_accessibility_permission() is False
```

### Area 3: Linux Tools (no Wayland/X11 session)

Mock `os.environ`, `shutil.which`, `subprocess.run`, `os.path.exists`:
```python
import os
from unittest.mock import patch, MagicMock

def test_detect_wayland_from_env():
    env = {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0", "XDG_CURRENT_DESKTOP": "GNOME"}
    with patch.dict(os.environ, env, clear=True):
        from ops.platform.linux_desktop import detect_linux_session
        r = detect_linux_session()
    assert r["session_type"] == "wayland"
    assert r["desktop"] == "gnome"

def test_missing_grim_raises_agent_error():
    from kernel.errors import AgentError
    with patch("shutil.which", return_value=None):
        from ops.platform.linux_desktop import screenshot_wayland
        try:
            screenshot_wayland("/tmp/x.png")
            assert False
        except AgentError as e:
            assert "grim not found" in str(e)

def test_socket_probe_fallback():
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=True):
            from ops.platform.linux_desktop import detect_linux_session
            r = detect_linux_session()
    assert r["session_type"] == "wayland"
```

### Area 4: Auto-Tuner (no real hardware)

Mock `psutil.virtual_memory` and `psutil.cpu_count`:
```python
from unittest.mock import patch, MagicMock
from kernel.resources import profile_hardware, check_memory_pressure

def _vm(total_gb, percent=30.0):
    m = MagicMock()
    m.total = int(total_gb * 1024**3)
    m.available = int(total_gb * 1024**3 * (1 - percent/100))
    m.percent = percent
    return m

def test_low_ram_tier():
    with patch("psutil.virtual_memory", return_value=_vm(3.5)), \
         patch("psutil.cpu_count", return_value=4):
        p = profile_hardware()
    assert p.ram_tier == "low"
    assert p.recommended_max_workers == 2
    assert p.recommended_context_tokens == 8192
    assert p.compact_history_threshold == 15

def test_high_ram_uses_cpu_count():
    with patch("psutil.virtual_memory", return_value=_vm(32.0)), \
         patch("psutil.cpu_count", return_value=16):
        p = profile_hardware()
    assert p.ram_tier == "high"
    assert p.recommended_max_workers == 16

def test_pressure_halves_workers():
    with patch("psutil.virtual_memory", return_value=_vm(8.0, percent=85.0)):
        assert check_memory_pressure(4) == 2

def test_no_pressure_unchanged():
    with patch("psutil.virtual_memory", return_value=_vm(8.0, percent=50.0)):
        assert check_memory_pressure(4) == 4
```

### Area 5: Checkpoint Manager (temp directory)

`tempfile.TemporaryDirectory` provides isolation — no mocking of disk I/O:
```python
import tempfile
from kernel.checkpoint import CheckpointManager, _goal_to_task_id

def test_create_and_load():
    with tempfile.TemporaryDirectory() as tmp:
        cm = CheckpointManager(tmp)
        phases = [{"name": "P1", "status": "pending", "steps": [], "result": None}]
        task_id = cm.create("Fix auth", phases)
        loaded = cm.load("Fix auth")
    assert loaded["task_id"] == task_id

def test_hash_normalization():
    assert _goal_to_task_id("Fix auth") == _goal_to_task_id("  fix auth  ")

def test_next_pending_skips_complete():
    with tempfile.TemporaryDirectory() as tmp:
        cm = CheckpointManager(tmp)
        task_id = cm.create("Goal", [
            {"name": "P1", "status": "complete", "steps": [], "result": "done"},
            {"name": "P2", "status": "pending", "steps": [], "result": None},
        ])
        assert cm.next_pending_phase(task_id)["name"] == "P2"

def test_all_complete_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        cm = CheckpointManager(tmp)
        task_id = cm.create("Done", [{"name": "P1", "status": "complete", "steps": [], "result": "done"}])
        assert cm.next_pending_phase(task_id) is None

def test_load_nonexistent_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        cm = CheckpointManager(tmp)
        assert cm.load("Brand new goal") is None
```

### Area 6: Retry Classifier & Stall Monitor (pure unit spec)

No mocking needed — pure logic, no I/O:
```python
from kernel.triage import RetryClassifier, parse_success_criteria
from kernel.stalls import StallMonitor
from unittest.mock import patch

# RetryClassifier
def test_transient_network():
    assert RetryClassifier().classify("ECONNREFUSED: connection refused").action == "retry"

def test_permanent_permission():
    assert RetryClassifier().classify("Permission denied: /etc/passwd").action == "abandon"

def test_permanent_exit_127():
    assert RetryClassifier().classify("cmd failed", exit_code=127).action == "abandon"

def test_ambiguous_escalates():
    d = RetryClassifier().classify("Unexpected error -1")
    assert d.action == "escalate" and d.max_retries == 2

def test_429_is_transient():
    assert RetryClassifier().classify("HTTP 429 Too Many Requests").action == "retry"

def test_enoent_is_permanent():
    assert RetryClassifier().classify("ENOENT: /missing/file").action == "abandon"

# Success criteria
def test_criteria_verify_that():
    c = parse_success_criteria("Fix it. Verify that the spec pass.")
    assert any("spec pass" in x for x in c)

def test_criteria_ensure():
    c = parse_success_criteria("Ensure that login works.")
    assert any("login works" in x for x in c)

def test_criteria_empty_plain_goal():
    assert parse_success_criteria("Just fix the bug.") == []

# StallMonitor
def test_no_stall_below_threshold():
    sm = StallMonitor()
    with patch("time.monotonic", side_effect=[0.0, 15.0]):
        sm.start("read_file")
        assert sm.check_stall("read_file") is None  # 15s < 30s threshold

def test_stall_above_threshold():
    sm = StallMonitor()
    with patch("time.monotonic", side_effect=[0.0, 45.0]):
        sm.start("read_file")
        w = sm.check_stall("read_file")
    assert w is not None and w.elapsed_seconds == 45.0

def test_faster_alt_for_fetch():
    sm = StallMonitor()
    with patch("time.monotonic", side_effect=[0.0, 65.0]):
        sm.start("fetchurl")
        w = sm.check_stall("fetchurl")
    assert "cache" in w.suggestion.lower()

def test_stop_clears_timer():
    sm = StallMonitor()
    with patch("time.monotonic", return_value=0.0):
        sm.start("read_file")
    sm.stop("read_file")
    assert sm.check_stall("read_file") is None
```

---

## Cross-Cutting: `ops/platform/__init__.py` OS Dispatcher

```python
import platform as _platform
_sys = _platform.system()

if _sys == "Windows":
    from ops.platform.windows_ui import list_windows, focus_window, click_at, typetext
elif _sys == "Darwin":
    from ops.platform.macos_ui import (
        list_windows, focus_window, click_at, typetext,
        check_accessibility_permission, prompt_accessibility_permission
    )
elif _sys == "Linux":
    from ops.platform.linux_desktop import detect_linux_session, takescreenshot, classify_desktop
    def list_windows():
        raise NotImplementedError("Window listing not supported on headless Linux. Use takescreenshot().")
```

Extend `kernel/osio.py` (`PlatformAPI`) — do not replace. Add `get_ui_backend()` static method returning `ops.platform`.

---

## Dependency Summary

| Package | Status | Condition |
|---|---|---|
| `psutil==5.9.8` | Already in requirements.txt | All platforms |
| `pyautogui==0.9.54` | Already in requirements.txt | All platforms (UI fallback) |
| `Pillow==12.2.0` | Already in requirements.txt | All platforms |
| `pywin32>=306` | **Must add to requirements.txt** | `sys_platform == 'win32'` |
| `pyobjc-framework-Quartz` | Optional, do not add to base | macOS only, Quartz window list |
| `pyobjc-framework-ApplicationServices` | Optional, do not add to base | macOS only, AX element tree |
| `grim` (system cliary) | Linux Wayland — not pip | User installs via distro package manager |
| `scrot` (system cliary) | Linux X11 — not pip | User installs via distro package manager |

---

## Key Gotchas Summary

1. **Windows UAC**: `SetForegroundWindow` silently fails on elevated windows from a non-elevated caller. Always detect elevation; raise `AgentError` with "Re-run as Administrator" instructions.

2. **macOS Accessibility**: All `System Events` AppleScript fails without the permission. Always call `check_accessibility_permission()` first, then `prompt_accessibility_permission()` if needed.

3. **Linux `$XDG_SESSION_TYPE` unreliable**: Some distros do not set it. Always fall back through `WAYLAND_DISPLAY`/`DISPLAY` env vars, then the `/run/user/{uid}/wayland-0` socket probe.

4. **Goal hash normalization**: Strip + lowercase before hashing. Without normalization, "Fix auth" and "  Fix auth  " produce different hashes and resume fails.

5. **CheckpointManager vs TaskTracker**: These are parallel systems. `TaskTracker` = per-session runtime. `CheckpointManager` = cross-session persistence. Do not merge.

6. **RetryClassifier vs repeated_action_count**: Parallel systems. `repeated_action_count` (lines 558–746 in runtime.py) = loop guard. `RetryClassifier` = error router for tool failures. Do not modify the existing loop guard.

7. **FallbackRouter scope**: `kernel/models.py` handles LLM API errors. `RetryClassifier` handles tool execution errors only. Do not duplicate LLM retry logic in `RetryClassifier`.

8. **pywin32 import guard**: On non-Windows, `import win32gui` raises `ModuleNotFoundError`. Always wrap with `try/except ImportError` and fall back to `pyautogui`.

9. **compact_history threshold independence**: `compact_history_threshold` controls the message-count trigger. The 80% token trigger in `context_engine.py` line 249 is independent and always active. Both can fire.

10. **GNOME Wayland + grim**: Also requires `xdg-desktop-portal-gnome`. Include this in the `AgentError` install instructions for Wayland screenshots on GNOME.
