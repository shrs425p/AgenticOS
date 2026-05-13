from __future__ import annotations

import ctypes
import os
import platform
import shutil


class SystemMixin:
    def system_info(self) -> str:
        try:
            return (
                f"os={platform.system()} {platform.release()} "
                f"arch={platform.machine()} python={platform.python_version()} "
                f"cwd={os.getcwd()} pid={os.getpid()}"
            )
        except Exception as e:
            return f"Error: {e}"

    def disk_usage(self, path: str = "/") -> str:
        try:
            total, used, free = shutil.disk_usage(path)
            return f"total={total} used={used} free={free}"
        except Exception as e:
            return f"Error: {e}"

    def cpu_usage(self) -> str:
        if self.system == "Windows":
            return self._run("wmic cpu get loadpercentage", timeout=10)
        return self._run("top -bn1 | head -n 5", timeout=10)

    def memory_usage(self) -> str:
        if self.system == "Windows":
            return self._run(
                "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value",
                timeout=10,
            )
        return self._run("free -h", timeout=10)

    def uptime(self) -> str:
        if self.system == "Windows":
            return self._run("wmic os get lastbootuptime", timeout=10)
        return self._run("uptime", timeout=10)

    def system_health(self) -> str:
        """Detailed report on system CPU, Memory, and Disk health, including agent process stats."""
        try:
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
                return self.run_powershell(script, timeout=30)
            else:
                # POSIX fallback
                cpu = self._run("top -bn1 | grep 'Cpu(s)'", timeout=10)
                mem = self._run("free -h", timeout=10)
                disk = self._run("df -h /", timeout=10)
                return f"CPU: {cpu}\nMemory: {mem}\nDisk: {disk}"
        except Exception as e:
            return f"Error gathering health stats: {e}"

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
        flags = SPIF_UPDATEINIFILE | SPIF_SENDCHANGE

        try:
            SystemParametersInfoW = ctypes.windll.user32.SystemParametersInfoW  # type: ignore[attr-defined]
            SystemParametersInfoW.argtypes = [
                ctypes.c_uint,
                ctypes.c_uint,
                ctypes.c_wchar_p,
                ctypes.c_uint,
            ]
            SystemParametersInfoW.restype = ctypes.c_bool
            ok = bool(SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, p, flags))
            if not ok:
                try:
                    err = ctypes.GetLastError()  # type: ignore[attr-defined]
                except Exception:
                    err = "unknown"
                return f"Error: SystemParametersInfoW failed (GetLastError={err})"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

        # Best-effort verification: read back registry value and also try a refresh.
        reg = self.run_powershell(
            "Get-ItemProperty -Path 'HKCU:\\\\Control Panel\\\\Desktop' -Name Wallpaper | "
            "Select-Object -ExpandProperty Wallpaper",
            timeout=20,
        ).strip()
        # Force a refresh as a fallback (some systems need it even after SPI).
        try:
            self.run_command(
                "RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters", timeout=20
            )
        except Exception:
            pass
        if reg and reg.strip().lower() != p.lower():
            return f"Error: wallpaper registry did not update.\nExpected: {p}\nRegistry: {reg}"
        return f"Wallpaper set to: {p}\nRegistry Wallpaper: {reg}".strip()
