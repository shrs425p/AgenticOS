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
        try:
            import psutil
            return f"{psutil.cpu_percent(interval=0.1)}%"
        except Exception as e:
            return f"Error: {e}"

    @tool(name="memory_usage", desc="Memory usage.", category="Terminal")
    def memory_usage(self) -> str:
        """memory_usage function."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return f"total={mem.total} used={mem.used} free={mem.available} percent={mem.percent}%"
        except Exception as e:
            return f"Error: {e}"

    @tool(name="uptime", desc="System uptime.", category="Terminal")
    def uptime(self) -> str:
        """uptime function."""
        try:
            import psutil
            import time
            uptime_seconds = time.time() - psutil.boot_time()
            hours, remainder = divmod(uptime_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"Uptime: {int(hours)}h {int(minutes)}m {int(seconds)}s"
        except Exception as e:
            return f"Error: {e}"

    @tool(name="system_health", desc="Detailed report on system CPU, Memory, and Disk health, including agent process stats.", category="Terminal")
    def system_health(self) -> str:
        """Detailed report on system CPU, Memory, and Disk health, including agent process stats."""
        try:
            import psutil
            import os
            pid = os.getpid()
            proc = psutil.Process(pid)
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            # Format output strings
            return (
                f"CPU Load: {cpu}%\n"
                f"Memory: {mem.percent}% used ({mem.available // (1024**2)}MB free of {mem.total // (1024**2)}MB)\n"
                f"Disk (/): {disk.percent}% used ({disk.free // (1024**3)}GB free of {disk.total // (1024**3)}GB)\n"
                f"Agent Process: CPU={proc.cpu_percent()}%, Mem={proc.memory_info().rss // (1024**2)}MB"
            )
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
        try:
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, p, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            return f"Wallpaper set to: {p}"
        except Exception as e:
            return f"Error setting wallpaper: {e}"
