"""Asynchronous OS Hardware Event Bus and telemetry polling daemon."""
import time
import socket
import logging
import threading
import platform
from typing import Optional, List, Dict, Any, Callable
import psutil

from core.tool_base import tool

class OSEventBus:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OSEventBus, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, cfg: Optional[dict] = None):
        if getattr(self, "_initialized", False):
            return

        self.cfg = cfg or {}
        event_bus_cfg = self.cfg.get("event_bus", {})

        self.cpu_threshold = float(event_bus_cfg.get("cpu_threshold", 90.0))
        self.mem_threshold = float(event_bus_cfg.get("memory_threshold", 90.0))
        self.battery_threshold = float(event_bus_cfg.get("battery_threshold", 15.0))
        self.poll_interval = float(event_bus_cfg.get("poll_interval", 5.0))

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.event_log: List[Dict[str, Any]] = []
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.Lock()

        # Keep track of previous states
        self.prev_network_connected = self._check_network()
        self.prev_power_plugged = True

        self._initialized = True
        self.start()

    def register_callback(self, cb: Callable[[Dict[str, Any]], None]) -> None:
        """Registers a callback function to receive OS events."""
        with self._lock:
            if cb not in self.callbacks:
                self.callbacks.append(cb)

    def _check_network(self) -> bool:
        """Verifies active network connection by attempting socket connection to public DNS."""
        try:
            socket.setdefaulttimeout(1.5)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("1.1.1.1", 53))
            s.close()
            return True
        except Exception:
            return False

    def log_event(self, event_type: str, severity: str, message: str, telemetry: Dict[str, Any]) -> None:
        """Thread-safe logging of system event."""
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "telemetry": telemetry
        }
        with self._lock:
            self.event_log.append(event)
            if len(self.event_log) > 1000:
                self.event_log.pop(0)

        # Trigger any listeners
        for cb in self.callbacks:
            try:
                cb(event)
            except Exception as e:
                logging.error(f"Event Bus: Listener callback failed: {e}")

    def start(self) -> None:
        """Starts the background monitoring loop daemon thread."""
        with self._lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._poll_loop, daemon=True, name="OSEventBusThread")
            self.thread.start()
            logging.info("OS Event Bus: Daemon thread started successfully.")

    def stop(self) -> None:
        """Shuts down the background monitoring thread."""
        with self._lock:
            self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        logging.info("OS Event Bus: Daemon thread stopped successfully.")

    def _poll_loop(self) -> None:
        """Periodically polls CPU, Memory, Battery, and Network states."""
        while True:
            with self._lock:
                if not self.running:
                    break

            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory().percent
                battery = psutil.sensors_battery()
                network = self._check_network()

                telemetry = {
                    "cpu_percent": cpu,
                    "memory_percent": mem,
                    "network_connected": network,
                    "battery": None
                }

                if battery is not None:
                    bat_pct = battery.percent
                    plugged = battery.power_plugged
                    telemetry["battery"] = {
                        "percent": bat_pct,
                        "power_plugged": plugged,
                        "secsleft": battery.secsleft
                    }

                    if bat_pct < self.battery_threshold and not plugged:
                        self.log_event(
                            event_type="BATTERY_CRITICAL",
                            severity="CRITICAL",
                            message=f"Battery level ({bat_pct}%) has fallen below critical threshold of {self.battery_threshold}%!",
                            telemetry=telemetry
                        )

                    if plugged != self.prev_power_plugged:
                        event_msg = "AC Power connected." if plugged else "AC Power disconnected. Battery active."
                        self.log_event(
                            event_type="POWER_STATE_CHANGE",
                            severity="INFO",
                            message=event_msg,
                            telemetry=telemetry
                        )
                        self.prev_power_plugged = plugged

                if cpu > self.cpu_threshold:
                    self.log_event(
                        event_type="CPU_SPIKE",
                        severity="WARNING",
                        message=f"CPU usage is spiking at {cpu}% (threshold is {self.cpu_threshold}%)!",
                        telemetry=telemetry
                    )

                if mem > self.mem_threshold:
                    self.log_event(
                        event_type="MEMORY_CRITICAL",
                        severity="CRITICAL",
                        message=f"System virtual memory usage is dangerously high at {mem}%!",
                        telemetry=telemetry
                    )

                if network != self.prev_network_connected:
                    status = "CONNECTED" if network else "DISCONNECTED"
                    severity = "INFO" if network else "WARNING"
                    self.log_event(
                        event_type="NETWORK_STATUS_CHANGE",
                        severity=severity,
                        message=f"Network interface status transitioned to {status}.",
                        telemetry=telemetry
                    )
                    self.prev_network_connected = network

            except Exception as e:
                logging.error(f"OS Event Bus: Error in polling loop: {e}")

            time.sleep(self.poll_interval)

    @tool(name="get_os_events", desc="Retrieve the list of recent hardware and system-level events (CPU spikes, battery drops, network transitions).", category="System")
    def get_os_events(self) -> str:
        """Queries the active event log from the background Event Bus."""
        with self._lock:
            if not self.event_log:
                return "No system events have been logged by the Event Bus."

            lines = []
            for ev in self.event_log:
                t_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ev["timestamp"]))
                lines.append(
                    f"[{t_str}] [{ev['severity']}] {ev['event_type']}: {ev['message']} "
                    f"(CPU: {ev['telemetry']['cpu_percent']}%, RAM: {ev['telemetry']['memory_percent']}%, "
                    f"Network: {'Up' if ev['telemetry']['network_connected'] else 'Down'})"
                )
            return "\n".join(lines)

    @tool(name="configure_os_event_bus", desc="Set CPU, memory, battery thresholds or polling interval. Args: cpu_threshold (optional), memory_threshold (optional), battery_threshold (optional), poll_interval (optional)", category="System")
    def configure_os_event_bus(
        self,
        cpu_threshold: Optional[float] = None,
        memory_threshold: Optional[float] = None,
        battery_threshold: Optional[float] = None,
        poll_interval: Optional[float] = None
    ) -> str:
        """Updates the configuration thresholds of the background Event Bus daemon."""
        with self._lock:
            updates = []
            if cpu_threshold is not None:
                self.cpu_threshold = float(cpu_threshold)
                updates.append(f"cpu_threshold={self.cpu_threshold}%")
            if memory_threshold is not None:
                self.mem_threshold = float(memory_threshold)
                updates.append(f"memory_threshold={self.mem_threshold}%")
            if battery_threshold is not None:
                self.battery_threshold = float(battery_threshold)
                updates.append(f"battery_threshold={self.battery_threshold}%")
            if poll_interval is not None:
                self.poll_interval = float(poll_interval)
                updates.append(f"poll_interval={self.poll_interval}s")

            if not updates:
                return "No parameters provided. Configuration unchanged."
            return f"Success: Updated configuration: {', '.join(updates)}."

    @tool(name="stop_os_event_bus", desc="Shut down the background OS event loop to release resources.", category="System")
    def stop_os_event_bus(self) -> str:
        """Gracefully halts the background event loop thread."""
        self.stop()
        return "Success: Background OS Event Bus has been shut down."

    @tool(name="start_os_event_bus", desc="Initialize and start the background OS event loop.", category="System")
    def start_os_event_bus(self) -> str:
        """Starts the background event loop thread if not already running."""
        self.start()
        return "Success: Background OS Event Bus has been started."
