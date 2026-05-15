"""
AgenticOs — terminal tools
Shell command execution, process management, environment, system info.
Supports PowerShell (Windows), Bash/Zsh (Unix/macOS), CMD.
"""

from __future__ import annotations

import platform

from tools.terminal.clipboard import ClipboardMixin
from tools.terminal.dev import DevToolsMixin
from tools.terminal.env import EnvMixin
from tools.terminal.keyboard import KeyboardMixin
from tools.terminal.media import MediaMixin
from tools.terminal.network import NetworkMixin
from tools.terminal.openers import OpenersMixin
from tools.terminal.paths import PathsMixin
from tools.terminal.processes import ProcessesMixin
from tools.terminal.runner import RunnerMixin
from tools.terminal.safety import SafetyMixin
from tools.terminal.system_admin import SystemAdminMixin
from tools.terminal.system import SystemMixin
from tools.terminal.windows_windows import WindowsWindowsMixin


class TerminalExecutor(
    SafetyMixin,
    RunnerMixin,
    ClipboardMixin,
    EnvMixin,
    PathsMixin,
    ProcessesMixin,
    OpenersMixin,
    SystemMixin,
    SystemAdminMixin,
    NetworkMixin,
    DevToolsMixin,
    WindowsWindowsMixin,
    MediaMixin,
    KeyboardMixin,
):
    def __init__(self, rules: dict | None = None, custom_keys: dict | None = None):
        self.rules = rules or {}
        self._env_overrides: dict = {}
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin'
        # User-defined named shortcuts loaded from config.yaml custom_keys section.
        self.custom_keys: dict[str, str] = {
            k.lower(): v for k, v in (custom_keys or {}).items()
        }
