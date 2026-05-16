"""Module for network.py"""
from __future__ import annotations

import socket
import time


from core.tool_base import tool
class NetworkMixin:
    @tool(name="network_interfaces", desc="List network interfaces.", category="Terminal")
    def network_interfaces(self) -> str:
        if self.system == "Windows":
            return self._run("ipconfig /all", timeout=30)
        return self._run("ifconfig || ip a", timeout=30)

    @tool(name="ping", desc="Ping a host. Args: host, count (optional)", category="Terminal")
    def ping(self, host: str, count: str = "3") -> str:
        c = int(count) if str(count).isdigit() else 3
        if self.system == "Windows":
            return self._run(f"ping -n {c} {host}", timeout=30)
        return self._run(f"ping -c {c} {host}", timeout=30)

    @tool(name="traceroute", desc="Traceroute to host. Args: host", category="Terminal")
    def traceroute(self, host: str) -> str:
        if self.system == "Windows":
            return self._run(f"tracert {host}", timeout=60)
        return self._run(f"traceroute {host}", timeout=60)

    @tool(name="netstat", desc="Show active network connections.", category="Terminal")
    def netstat(self) -> str:
        if self.system == "Windows":
            return self._run("netstat -ano", timeout=30)
        return self._run("netstat -anp", timeout=30)

    def wait_for_port(
        self, port: str, host: str = "localhost", timeout: str = "10"  # DevSkim: ignore
    ) -> str:



        try:
            p = int(port)
            t = float(timeout)
            start = time.time()
            while time.time() - start < t:
                try:
                    with socket.create_connection((host, p), timeout=1):
                        return "open"
                except OSError:
                    time.sleep(0.25)
            return "timeout"
        except Exception as e:
            return f"Error: {e}"
