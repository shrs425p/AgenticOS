from __future__ import annotations

import socket
import time


class NetworkMixin:
    def network_interfaces(self) -> str:
        if self.system == "Windows":
            return self._run("ipconfig /all", timeout=30)
        return self._run("ifconfig || ip a", timeout=30)

    def ping(self, host: str, count: str = "3") -> str:
        c = int(count) if str(count).isdigit() else 3
        if self.system == "Windows":
            return self._run(f"ping -n {c} {host}", timeout=30)
        return self._run(f"ping -c {c} {host}", timeout=30)

    def traceroute(self, host: str) -> str:
        if self.system == "Windows":
            return self._run(f"tracert {host}", timeout=60)
        return self._run(f"traceroute {host}", timeout=60)

    def netstat(self) -> str:
        if self.system == "Windows":
            return self._run("netstat -ano", timeout=30)
        return self._run("netstat -anp", timeout=30)

    def wait_for_port(
        self, port: str, host: str = "localhost", timeout: str = "10"
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
