"""Module for system_tools.py"""
import os
from core.tool_base import tool

class SystemManager:
    """
    Manager for agent session and system lifecycle.
    """
    def __init__(self, rules: dict = None, cfg: dict = None):
        self.rules = rules or {}
        self.cfg = cfg or {}

    @tool(
        name="exit_agent",
        desc="Gracefully terminates the current agent session and exits the program.",
        category="System"
    )
    def exit_agent(self, reason: str = "User requested exit") -> str:
        """
        Exits the agent process.
        Args:
            reason: The reason for exiting.
        """
        print(f"\n[SYSTEM] Agent shutting down: {reason}")
        # We use os._exit to bypass any catch-all try blocks in the runtime loop
        os._exit(0)
        return "Shutting down..."

    @tool(
        name="get_system_telemetry",
        desc="Retrieves real-time system performance telemetry (CPU, Virtual Memory, Root Partition Disk space, and Network Bandwidth).",
        category="System"
    )
    def get_system_telemetry(self) -> dict:
        """
        Retrieves real-time resource utilization statistics of the host machine.

        Returns:
            dict: Structured metrics containing CPU, virtual memory, disk storage, and network transport statistics.
        """
        import psutil

        # CPU Telemetry
        cpu_pct = psutil.cpu_percent(interval=0.1)
        cores_phys = psutil.cpu_count(logical=False) or 1
        cores_log = psutil.cpu_count(logical=True) or 1

        # Virtual Memory Telemetry
        mem = psutil.virtual_memory()

        # Disk Telemetry (Root partition)
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

        # Network Bandwidth Telemetry
        try:
            net = psutil.net_io_counters()
            net_stats = {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
            }
        except Exception:
            net_stats = {
                "bytes_sent": 0,
                "bytes_recv": 0,
            }

        return {
            "cpu": {
                "percent": cpu_pct,
                "cores_physical": cores_phys,
                "cores_logical": cores_log,
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


