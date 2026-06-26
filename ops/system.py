"""System lifecycle and OS operator ops."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess

from kernel.base import tool


class SystemManager:
    """Manager for agent session, host telemetry, and OS-level operations."""

    def __init__(self, rules: dict | None = None, cfg: dict | None = None):
        self.rules = rules or {}
        self.cfg = cfg or {}
        self.system = platform.system()

    def _run(self, command: list[str], timeout: int = 60) -> str:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            parts = []
            if out:
                parts.append(out)
            if err:
                parts.append(f"[stderr]\n{err}")
            parts.append(f"[exit: {result.returncode}]")
            return "\n".join(parts)
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {timeout}s"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    def _run_shell(self, command: str, timeout: int = 60) -> str:
        shell = (
            ["powershell", "-NoProfile", "-Command", command]
            if self.system == "Windows"
            else ["/cli/sh", "-c", command]
        )
        return self._run(shell, timeout=timeout)

    def _json(self, payload: dict) -> str:
        return json.dumps(payload, indent=2, default=str)

    @tool(
        name="exitagent",
        desc="Gracefully terminates the current agent session and exits the program.",
        category="System",
    )
    def exitagent(self, reason: str = "User requested exit") -> str:
        """Exit the agent process."""
        print(f"\n[SYSTEM] Agent shutting down: {reason}")
        os._exit(0)
        return "Shutting down..."

    @tool(
        name="getsystemtelemetry",
        desc="Retrieves real-time system performance telemetry (CPU, Virtual Memory, Root Partition Disk space, and Network Bandwidth).",
        category="System",
    )
    def getsystemtelemetry(self) -> dict:
        """Return real-time resource utilization statistics for the host."""
        import psutil

        cpu_pct = psutil.cpu_percent(interval=0.1)
        kernels_phys = psutil.cpu_count(logical=False) or 1
        kernels_log = psutil.cpu_count(logical=True) or 1
        mem = psutil.virtual_memory()

        try:
            disk = psutil.disk_usage("/")
            disk_stats = {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "percent": disk.percent,
            }
        except Exception:
            disk_stats = {
                "total_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0,
                "percent": 0.0,
            }

        try:
            net = psutil.net_io_counters()
            net_stats = {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv}
        except Exception:
            net_stats = {"bytes_sent": 0, "bytes_recv": 0}

        return {
            "cpu": {
                "percent": cpu_pct,
                "kernels_physical": kernels_phys,
                "kernels_logical": kernels_log,
            },
            "memory": {
                "total_bytes": mem.total,
                "available_bytes": mem.available,
                "used_bytes": mem.used,
                "percent": mem.percent,
            },
            "disk": disk_stats,
            "network": net_stats,
        }

    @tool(
        name="osinventory",
        desc="OS-wide structured inventory. Args: scope(summary|processes|network|services|tasks|apps|startup), filter_str(optional), limit(optional)",
        category="System",
    )
    def osinventory(
        self, scope: str = "summary", filter_str: str = "", limit: int = 50
    ) -> str:
        """Return structured host inventory for autonomous OS operation."""
        import psutil

        scope = (scope or "summary").strip().lower()
        flt = (filter_str or "").strip().lower()
        try:
            limit = max(1, min(int(limit), 250))
        except Exception:
            limit = 50

        if scope == "summary":
            disks = []
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                except Exception:
                    continue
                disks.append(
                    {
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_bytes": usage.total,
                        "free_bytes": usage.free,
                        "percent": usage.percent,
                    }
                )

            battery = None
            if hasattr(psutil, "sensors_battery"):
                batt = psutil.sensors_battery()
                battery = batt._asdict() if batt else None

            return self._json(
                {
                    "platform": {
                        "system": self.system,
                        "release": platform.release(),
                        "version": platform.version(),
                        "machine": platform.machine(),
                        "python": platform.python_version(),
                    },
                    "telemetry": self.getsystemtelemetry(),
                    "boot_time": psutil.boot_time(),
                    "disks": disks,
                    "users": [u._asdict() for u in psutil.users()],
                    "battery": battery,
                }
            )

        if scope == "processes":
            procs = []
            attrs = [
                "pid",
                "name",
                "username",
                "status",
                "cpu_percent",
                "memory_percent",
                "exe",
                "cmdline",
            ]
            for proc in psutil.process_iter(attrs):
                try:
                    info = proc.info
                    haystack = " ".join(
                        str(info.get(k) or "")
                        for k in ("pid", "name", "username", "exe", "cmdline")
                    ).lower()
                    if flt and flt not in haystack:
                        continue
                    procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda p: float(p.get("memory_percent") or 0), reverse=True)
            return self._json({"processes": procs[:limit]})

        if scope == "network":
            conns = []
            for conn in psutil.net_connections(kind="inet"):
                item = conn._asdict()
                haystack = json.dumps(item, default=str).lower()
                if flt and flt not in haystack:
                    continue
                conns.append(item)
            return self._json({"connections": conns[:limit]})

        if scope == "services":
            if self.system == "Windows":
                cmd = "Get-Service | Select-Object Status,Name,DisplayName,StartType | ConvertTo-Json"
                if flt:
                    cmd = (
                        "Get-Service | "
                        f"Where-Object {{ $_.Name -like '*{flt}*' -or $_.DisplayName -like '*{flt}*' }} | "
                        "Select-Object Status,Name,DisplayName,StartType | ConvertTo-Json"
                    )
                return self._run_shell(cmd, timeout=60)
            return self._run(
                ["systemctl", "list-units", "--type=service", "--no-pager"],
                timeout=60,
            )

        if scope == "tasks":
            if self.system != "Windows":
                return self._run_shell("crontab -l 2>/dev/null || true", timeout=30)
            cmd = "Get-ScheduledTask | Select-Object TaskName,TaskPath,State | ConvertTo-Json"
            if flt:
                cmd = (
                    "Get-ScheduledTask | "
                    f"Where-Object {{ $_.TaskName -like '*{flt}*' -or $_.TaskPath -like '*{flt}*' }} | "
                    "Select-Object TaskName,TaskPath,State | ConvertTo-Json"
                )
            return self._run_shell(cmd, timeout=60)

        if scope == "apps":
            if self.system != "Windows":
                cmd = (
                    "command -v dpkg >/dev/null && dpkg -l || "
                    "command -v rpm >/dev/null && rpm -qa || "
                    "command -v brew >/dev/null && brew list --versions || true"
                )
                return self._run_shell(cmd, timeout=60)
            reg1 = self.cfg.get("windows_paths", {}).get(
                "uninstall_registry",
                "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
            )
            reg2 = self.cfg.get("windows_paths", {}).get(
                "wow6432_uninstall_registry",
                "HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
            )
            cmd = (
                f"Get-ItemProperty {reg1} , {reg2} | "
                "Where-Object { $_.DisplayName } | "
            )
            if flt:
                cmd += (
                    f"Where-Object {{ $_.DisplayName -like '*{flt}*' "
                    f"-or $_.Publisher -like '*{flt}*' }} | "
                )
            cmd += "Select-Object DisplayName,DisplayVersion,Publisher,InstallDate | ConvertTo-Json"
            return self._run_shell(cmd, timeout=60)

        if scope == "startup":
            if self.system == "Windows":
                return self._run_shell(
                    "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location,User | ConvertTo-Json",
                    timeout=60,
                )
            return self._run_shell(
                "ls -la ~/.cfg/autostart /etc/xdg/autostart 2>/dev/null || true",
                timeout=30,
            )

        return "Error: unknown scope. Use summary, processes, network, services, tasks, apps, or startup."

    @tool(
        name="osprocess",
        desc="Manage processes. Args: action(list|terminate|kill), target(optional pid/name), limit(optional)",
        category="System",
    )
    def osprocess(self, action: str = "list", target: str = "", limit: int = 50) -> str:
        """List or control host processes using psutil."""
        import psutil

        action = (action or "list").strip().lower()
        target = (target or "").strip()
        if action == "list":
            return self.osinventory("processes", target, limit)
        if action not in {"terminate", "kill"}:
            return "Error: action must be list, terminate, or kill."
        if not self.rules.get("allow_process_control", True):
            return "Error: process control is disabled by rules."
        if not target:
            return "Error: target pid or process-name substring required."

        matches = []
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                if target.isdigit() and proc.pid == int(target):
                    matches.append(proc)
                elif (
                    not target.isdigit()
                    and target.lower() in (proc.info.get("name") or "").lower()
                ):
                    matches.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not matches:
            return "No matching processes."
        results = []
        for proc in matches[:25]:
            try:
                if proc.pid == os.getpid():
                    results.append(
                        {"pid": proc.pid, "name": proc.name(), "status": "skipped_self"}
                    )
                    continue
                proc.kill() if action == "kill" else proc.terminate()
                results.append({"pid": proc.pid, "name": proc.name(), "status": action})
            except Exception as e:
                results.append(
                    {
                        "pid": getattr(proc, "pid", None),
                        "status": f"error: {type(e).__name__}: {e}",
                    }
                )
        return self._json({"results": results})

    @tool(
        name="osservice",
        desc="Manage services. Args: action(list|status|start|stop|restart), name(optional)",
        category="System",
    )
    def osservice(self, action: str = "list", name: str = "") -> str:
        """Cross-platform service inventory and control."""
        action = (action or "list").strip().lower()
        name = (name or "").strip()
        if action == "list":
            return self.osinventory("services", name, 100)
        if action not in {"status", "start", "stop", "restart"}:
            return "Error: action must be list, status, start, stop, or restart."
        if not name:
            return "Error: service name required."
        if action in {"start", "stop", "restart"} and not self.rules.get(
            "allow_service_control", False
        ):
            return "Error: service control is disabled by rules."
        if self.system == "Windows":
            verbs = {
                "status": f'Get-Service -Name "{name}" | Select-Object Status,Name,DisplayName,StartType | ConvertTo-Json',
                "start": f'Start-Service -Name "{name}" -ErrorAction Stop; "OK"',
                "stop": f'Stop-Service -Name "{name}" -ErrorAction Stop; "OK"',
                "restart": f'Restart-Service -Name "{name}" -ErrorAction Stop; "OK"',
            }
            return self._run_shell(verbs[action], timeout=60)
        verbs = {
            "status": ["systemctl", "status", name, "--no-pager"],
            "start": ["systemctl", "start", name],
            "stop": ["systemctl", "stop", name],
            "restart": ["systemctl", "restart", name],
        }
        return self._run(verbs[action], timeout=60)

    @tool(
        name="osscheduledaily",
        desc="Create a daily scheduled task. Args: task_name, command, time_hhmm(optional)",
        category="System",
    )
    def osscheduledaily(
        self, task_name: str, command: str, time_hhmm: str = "09:00"
    ) -> str:
        """Create a daily scheduled task with native OS facilities."""
        if not self.rules.get("allow_scheduled_tasks", True) or not self.rules.get(
            "allow_system_changes", False
        ):
            return "Error: scheduled task creation is disabled by rules."
        name = (task_name or "").strip()
        cmd = (command or "").strip()
        when = (time_hhmm or "09:00").strip()
        if not name or not cmd:
            return "Error: task_name and command required."
        if self.system == "Windows":
            return self._run(
                [
                    "schtasks",
                    "/Create",
                    "/F",
                    "/SC",
                    "DAILY",
                    "/TN",
                    name,
                    "/TR",
                    cmd,
                    "/ST",
                    when,
                ],
                timeout=60,
            )
        hour, minute = when.split(":", 1)
        cron_line = f"{minute} {hour} * * * {cmd}"
        return self._run_shell(
            f'(crontab -l 2>/dev/null; printf "%s\\n" {json.dumps(cron_line)}) | crontab -',
            timeout=60,
        )

    @tool(
        name="ospackage",
        desc="Check or install system packages. Args: action(check|install), name(optional)",
        category="System",
    )
    def ospackage(self, action: str = "check", name: str = "") -> str:
        """Use the host package manager for package discovery or installation."""
        action = (action or "check").strip().lower()
        name = (name or "").strip()
        managers = (
            ["winget", "choco", "scoop"]
            if self.system == "Windows"
            else ["brew", "apt-get", "dnf", "yum", "pacman"]
        )
        found = [m for m in managers if shutil.which(m)]
        if action == "check":
            return self._json({"available_package_managers": found})
        if action != "install":
            return "Error: action must be check or install."
        if not self.rules.get("allow_system_changes", False):
            return "Error: package installation is disabled by rules."
        if not name:
            return "Error: package name required."
        if not found:
            return "Error: no supported package manager found."
        mgr = found[0]
        commands = {
            "winget": [
                "winget",
                "install",
                "--accept-source-agreements",
                "--accept-package-agreements",
                name,
            ],
            "choco": ["choco", "install", "-y", name],
            "scoop": ["scoop", "install", name],
            "brew": ["brew", "install", name],
            "apt-get": ["sudo", "apt-get", "install", "-y", name],
            "dnf": ["sudo", "dnf", "install", "-y", name],
            "yum": ["sudo", "yum", "install", "-y", name],
            "pacman": ["sudo", "pacman", "-S", "--noconfirm", name],
        }
        return self._run(commands[mgr], timeout=900)
