from unittest import mock
from tools.system_tools import SystemManager

def test_exit_agent():
    sm = SystemManager()
    
    with mock.patch("os._exit") as mock_exit:
        sm.exit_agent("Goodbye")
        mock_exit.assert_called_once_with(0)


def test_get_system_telemetry():
    sm = SystemManager()
    telemetry = sm.get_system_telemetry()
    
    # Assert top-level keys
    assert "cpu" in telemetry
    assert "memory" in telemetry
    assert "disk" in telemetry
    assert "network" in telemetry

    # Assert CPU details
    assert "percent" in telemetry["cpu"]
    assert "cores_physical" in telemetry["cpu"]
    assert "cores_logical" in telemetry["cpu"]

    # Assert Virtual Memory details
    assert "total_bytes" in telemetry["memory"]
    assert "percent" in telemetry["memory"]

    # Assert Disk details
    assert "percent" in telemetry["disk"]

