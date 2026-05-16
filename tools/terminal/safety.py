"""Module for safety.py"""
from __future__ import annotations


class SafetyMixin:
    def _blocked_command_reason(self, command: str) -> str:
        if not self.rules.get("allow_shell_exec", True):
            return "shell execution is disabled"

        if not self.rules.get("validate_commands", False):
            return ""

        lowered = (command or "").lower().strip()
        blocked_groups = []
        if not self.rules.get("allow_registry_edit", False):
            blocked_groups.extend(
                ("reg add", "reg delete", "reg import", "set-itemproperty")
            )
        if not self.rules.get("allow_service_control", False):
            blocked_groups.extend(
                ("sc ", "net stop", "net start", "systemctl", "service ")
            )
        if not self.rules.get("allow_system_changes", False):
            blocked_groups.extend(
                ("shutdown", "restart-computer", "reboot", "format ", "diskpart")
            )

        for token in blocked_groups:
            if lowered.startswith(token) or f" {token}" in lowered:
                return f"Command blocked by safety rules: {token.strip()}"
        return ""
