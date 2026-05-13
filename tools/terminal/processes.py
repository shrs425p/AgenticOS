from __future__ import annotations

import os
import subprocess


class ProcessesMixin:
    def self_pid(self) -> str:
        """Return the agent process PID (useful for self-management / debugging)."""
        try:
            return str(os.getpid())
        except Exception as e:
            return f"Error: {e}"

    def self_process_info(self) -> str:
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
                out = self.run_powershell(cmd, timeout=20)
                return out
        except Exception:
            pass

        return " ".join(info)

    def process_list(self, filter_str: str = "") -> str:
        flt = (filter_str or "").lower().strip()
        cmd = "tasklist" if self.system == "Windows" else "ps aux"
        out = self._run(cmd, timeout=30)
        if not flt:
            return out
        lines = [ln for ln in out.splitlines() if flt in ln.lower()]
        return "\n".join(lines[:200]) if lines else "No matches."

    def process_list_detailed(self, filter_str: str = "") -> str:
        """Detailed process list with command line (best-effort, Windows-focused)."""
        flt = (filter_str or "").strip()
        if getattr(self, "system", "") == "Windows":
            # Name, PID, Path, and CommandLine are invaluable for distinguishing processes.
            # Keep it readable: limit rows and truncate very long command lines.
            ps = (
                "$flt = " + repr(flt) + "; "
                "$q = Get-CimInstance Win32_Process | "
                "Select-Object Name,ProcessId,ExecutablePath,CommandLine; "
                "if($flt){ $q = $q | Where-Object { ($_.Name -like ('*'+$flt+'*')) -or ($_.CommandLine -like ('*'+$flt+'*')) } }; "
                "$q | Select-Object -First 80 Name,ProcessId,ExecutablePath,@{N='CommandLine';E={"
                "if($_.CommandLine -and $_.CommandLine.Length -gt 240){ $_.CommandLine.Substring(0,240)+'…' } else { $_.CommandLine }"
                "}} | Format-Table -AutoSize"
            )
            return self.run_powershell(ps, timeout=30)
        # Fallback: plain ps output.
        out = self._run("ps aux", timeout=30)
        if not flt:
            return out
        lines = [ln for ln in out.splitlines() if flt.lower() in ln.lower()]
        return "\n".join(lines[:200]) if lines else "No matches."

    def kill_process(self, pid: str, signal_name: str = "TERM") -> str:
        if not self.rules.get("allow_process_control", True):
            return "Error: process control is disabled by rules."
        try:
            if self.system == "Windows":
                return self._run(f"taskkill /PID {pid} /F", timeout=20)
            sig = (signal_name or "TERM").upper()
            return self._run(f"kill -s {sig} {pid}", timeout=20)
        except Exception as e:
            return f"Error: {e}"

    def kill_process_by_name(self, image_name: str) -> str:
        """Kill process(es) by image name (Windows: taskkill /IM)."""
        if not self.rules.get("allow_process_control", True):
            return "Error: process control is disabled by rules."
        name = (image_name or "").strip()
        if not name:
            return "Error: image_name is required."
        try:
            if self.system == "Windows":
                # Accept "spotify" and normalize to spotify.exe for Windows taskkill.
                if not name.lower().endswith(".exe"):
                    name = name + ".exe"
                return self._run(f"taskkill /IM {name} /F", timeout=20)
            # POSIX fallback: pkill by name.
            return self._run(f"pkill -f {name}", timeout=20)
        except Exception as e:
            return f"Error: {e}"

    def start_background(self, command: str) -> str:
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
