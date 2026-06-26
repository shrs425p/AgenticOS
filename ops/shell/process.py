"""Module for processes.py"""
from __future__ import annotations

import os
import subprocess




from kernel.base import tool
class ProcessesMixin:
    @tool(name="selfpid", desc="Get this agent process PID. Args: none", category="Terminal")
    def selfpid(self) -> str:
        """Return the agent process PID (useful for self-management / debugging)."""
        try:
            return str(os.getpid())
        except Exception as e:
            return f"Error: {e}"

    @tool(name="selfprocessinfo", desc="Get this agent process details (PID/name/path/cmdline best-effort). Args: none", category="Terminal")
    def selfprocessinfo(self) -> str:
        """Return PID + best-effort process name / path / command line for the agent itself."""
        try:
            pid = os.getpid()
        except Exception as e:
            return f"Error: {e}"

        # Cross-platform minimum.
        info = [f"pid={pid}"]

        # Best-effort details (Windows via CIM).
        try:
            if getattr(self, "system", "") == "Windows":
                # Use CIM/WMI to fetch the current process details.
                # Note: CommandLine can be long; we keep output readable.
                cmd = (
                    "Get-CimInstance Win32_Process "
                    f'-Filter "ProcessId={pid}" | '
                    "Select-Object Name,ProcessId,ExecutablePath,CommandLine | "
                    "Format-List"
                )
                out = self.runpowershell(cmd, timeout=20)
                return out
        except Exception:
            pass  # Expected: CIM query may fail on certain Windows configurations.


        return " ".join(info)

    @tool(name="startbackground", desc="Start command in background. Args: command", category="Terminal")
    def startbackground(self, command: str) -> str:
        """startbackground function."""
        if not self.rules.get("allow_shell_exec", True):
            return "Error: shell execution is disabled"
        blocked_reason = self._blocked_command_reason(command)
        if blocked_reason:
            return f"Error: {blocked_reason}"
        try:
            subprocess.Popen(command, shell=True)


            return "Started."

        except Exception as e:
            return f"Error: {e}"
