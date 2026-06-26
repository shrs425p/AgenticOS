"""
AgenticOs — terminal ops
Shell command execution, process management, environment, system info.
Supports PowerShell (Windows), Bash/Zsh (Unix/macOS), CMD.
"""

from __future__ import annotations

import platform

from ops.shell.clipboard import ClipboardMixin
from ops.shell.keyboard import KeyboardMixin
from ops.shell.media import MediaMixin
from ops.shell.open import OpenersMixin
from ops.shell.paths import PathsMixin
from ops.shell.process import ProcessesMixin
from ops.shell.runner import RunnerMixin
from ops.shell.safety import SafetyMixin
from ops.shell.admin import SystemAdminMixin
from ops.shell.system import SystemMixin
from ops.shell.windows import WindowsWindowsMixin


class TerminalExecutor(
    SafetyMixin,
    RunnerMixin,
    ClipboardMixin,
    PathsMixin,
    ProcessesMixin,
    OpenersMixin,
    SystemMixin,
    SystemAdminMixin,
    WindowsWindowsMixin,
    MediaMixin,
    KeyboardMixin,
):
    def __init__(
        self,
        rules: dict | None = None,
        custom_keys: dict | None = None,
        cfg: dict | None = None,
    ):
        self.rules = rules or {}
        self.cfg = cfg or {}
        self._env_overrides: dict = {}
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin'
        # User-defined named shortcuts loaded from cfg.yaml custom_keys section.
        self.custom_keys: dict[str, str] = {
            k.lower(): v for k, v in (custom_keys or {}).items()
        }

    def _get_timeout(self, key: str, default: int) -> int:
        """Get timeout from cfg or use default."""
        return self.cfg.get("timeouts", {}).get(key, default)
