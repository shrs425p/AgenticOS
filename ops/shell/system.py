"""Module for system.py"""
from __future__ import annotations

from kernel.base import tool
class SystemMixin:
    @tool(name="systemhealth", desc="Detailed report on system CPU, Memory, and Disk health, including agent process stats.", category="Terminal")
    def systemhealth(self) -> str:
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
