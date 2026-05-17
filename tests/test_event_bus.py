"""Unit tests for the Asynchronous OS Hardware Event Bus."""
import os
import time
import unittest
from unittest.mock import MagicMock, patch
import pytest

from core.event_bus import OSEventBus

def test_singleton_behavior():
    bus1 = OSEventBus()
    bus2 = OSEventBus()
    assert bus1 is bus2

def test_configure_thresholds():
    bus = OSEventBus()
    res = bus.configure_os_event_bus(cpu_threshold=85.0, poll_interval=10.0)
    assert "Success" in res
    assert bus.cpu_threshold == 85.0
    assert bus.poll_interval == 10.0

@patch("psutil.cpu_percent")
@patch("psutil.virtual_memory")
@patch("psutil.sensors_battery")
@patch("core.event_bus.OSEventBus._check_network")
def test_poll_loop_spikes(mock_net, mock_battery, mock_mem, mock_cpu):
    # Setup mocks for spikes
    mock_cpu.return_value = 95.0

    mock_mem_obj = MagicMock()
    mock_mem_obj.percent = 92.0
    mock_mem.return_value = mock_mem_obj

    mock_bat_obj = MagicMock()
    mock_bat_obj.percent = 10.0
    mock_bat_obj.power_plugged = False
    mock_bat_obj.secsleft = 1000
    mock_battery.return_value = mock_bat_obj

    mock_net.return_value = False

    bus = OSEventBus()
    bus.stop()

    bus.cpu_threshold = 90.0
    bus.mem_threshold = 90.0
    bus.battery_threshold = 15.0
    bus.event_log = []

    bus.running = True
    def stop_after_one(*args, **kwargs):
        bus.running = False

    callback_events = []
    bus.register_callback(callback_events.append)

    with patch("time.sleep", side_effect=stop_after_one):
        bus._poll_loop()

    assert len(bus.event_log) >= 3
    event_types = [e["event_type"] for e in bus.event_log]
    assert "CPU_SPIKE" in event_types
    assert "MEMORY_CRITICAL" in event_types
    assert "BATTERY_CRITICAL" in event_types

    assert len(callback_events) >= 3

def test_tool_get_os_events():
    bus = OSEventBus()
    bus.event_log = [
        {
            "timestamp": time.time(),
            "event_type": "TEST_EVENT",
            "severity": "INFO",
            "message": "This is a test event log entry.",
            "telemetry": {"cpu_percent": 12.0, "memory_percent": 34.0, "network_connected": True}
        }
    ]

    log_res = bus.get_os_events()
    assert "TEST_EVENT" in log_res
    assert "This is a test event log entry." in log_res
