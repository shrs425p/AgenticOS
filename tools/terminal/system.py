"""Module for system.py"""
from __future__ import annotations

import ctypes
import os
import platform
import shutil


from core.tool_base import tool
class SystemMixin:
    @tool(name="system_info", desc="Get OS/hardware info.", category="Terminal")
    def system_info(self) -> str:
        """system_info function."""
        try:
            return (
                f"os={platform.system()} {platform.release()} "
                f"arch={platform.machine()} python={platform.python_version()} "
                f"cwd={os.getcwd()} pid={os.getpid()}"
            )
        except Exception as e:
            return f"Error: {e}"

    @tool(name="disk_usage", desc="Disk usage. Args: path (optional)", category="Terminal")
    def disk_usage(self, path: str = "/") -> str:
        """disk_usage function."""
        try:
            total, used, free = shutil.disk_usage(path)
            return f"total={total} used={used} free={free}"
        except Exception as e:
            return f"Error: {e}"

    @tool(name="cpu_usage", desc="CPU usage snapshot.", category="Terminal")
    def cpu_usage(self) -> str:
        """cpu_usage function."""
        t = self.cfg.get("timeouts", {}).get("system_admin", 10)
        if self.system == "Windows":
            return self.run_powershell("Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average", timeout=t)
        return self._run("top -bn1 | head -n 5", timeout=t)

    @tool(name="memory_usage", desc="Memory usage.", category="Terminal")
    def memory_usage(self) -> str:
        """memory_usage function."""
        t = self.cfg.get("timeouts", {}).get("system_admin", 10)
        if self.system == "Windows":
            return self.run_powershell("Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory, TotalVisibleMemorySize | Format-List", timeout=t)
        return self._run("free -h", timeout=t)

    @tool(name="uptime", desc="System uptime.", category="Terminal")
    def uptime(self) -> str:
        """uptime function."""
        t = self.cfg.get("timeouts", {}).get("system_admin", 10)
        if self.system == "Windows":
            return self.run_powershell("Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty LastBootUpTime", timeout=t)
        return self._run("uptime", timeout=t)

    @tool(name="system_health", desc="Detailed report on system CPU, Memory, and Disk health, including agent process stats.", category="Terminal")
    def system_health(self) -> str:
        """Detailed report on system CPU, Memory, and Disk health, including agent process stats."""
        try:
            t_short = self.cfg.get("timeouts", {}).get("system_admin", 10)
            t_long = self.cfg.get("timeouts", {}).get("system_admin", 30)
            if self.system == "Windows":
                # Use PowerShell for a comprehensive, clean report.
                pid = os.getpid()
                script = (
                    "$os = Get-CimInstance Win32_OperatingSystem; "
                    "$cpu = Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average; "
                    "$proc = Get-Process -Id " + str(pid) + "; "
                    '$disk = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID, FreeSpace, Size; '
                    "$out = @{ "
                    '  SystemCPU_Load = "$($cpu.Average)%"; '
                    '  SystemMem_Total = "$([math]::round($os.TotalVisibleMemorySize / 1MB, 2)) GB"; '
                    '  SystemMem_Free = "$([math]::round($os.FreePhysicalMemory / 1MB, 2)) GB"; '
                    '  AgentMem_WorkingSet = "$([math]::round($proc.WorkingSet64 / 1MB, 2)) MB"; '
                    '  AgentCPU_Time = "$($proc.TotalProcessorTime.TotalSeconds)s"; '
                    "  Disks = ($disk | ForEach-Object { \"$($_.DeviceID) ($([math]::round($_.FreeSpace / 1GB, 2))GB free of $([math]::round($_.Size / 1GB, 2))GB)\" }) -join ', '; "
                    "}; "
                    "$out | ConvertTo-Json"
                )
                return self.run_powershell(script, timeout=t_long)
            else:
                # POSIX fallback
                cpu = self._run("top -bn1 | grep 'Cpu(s)'", timeout=t_short)
                mem = self._run("free -h", timeout=t_short)
                disk = self._run("df -h /", timeout=t_short)
                return f"CPU: {cpu}\nMemory: {mem}\nDisk: {disk}"
        except Exception as e:
            return f"Error gathering health stats: {e}"

    @tool(name="set_wallpaper", desc="Set Windows desktop wallpaper to local image. Args: path", category="Terminal")
    def set_wallpaper(self, path: str) -> str:
        """Set Windows desktop wallpaper to a local image path."""
        if self.system != "Windows":
            return "Error: set_wallpaper is only supported on Windows."
        p = (path or "").strip().strip('"')
        if not p:
            return "Error: path required."
        if not os.path.isabs(p):
            p = os.path.abspath(p)
        if not os.path.exists(p):
            return f"Error: file not found: {p}"

        # SPI_SETDESKWALLPAPER = 0x0014
        # SPIF_UPDATEINIFILE = 0x01, SPIF_SENDCHANGE = 0x02
        SPI_SETDESKWALLPAPER = 0x0014
        SPIF_UPDATEINIFILE = 0x01
        SPIF_SENDCHANGE = 0x02
        try:
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, p, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            return f"Wallpaper set to: {p}"
        except Exception as e:
            return f"Error setting wallpaper: {e}"
