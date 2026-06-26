from unittest import mock
import json
from ops.system import SystemManager

def test_exitagent():
    sm = SystemManager()
    
    with mock.patch("os._exit") as mock_exit:
        sm.exitagent("Goodbye")
        mock_exit.assert_called_once_with(0)


def test_getsystemtelemetry():
    sm = SystemManager()
    telemetry = sm.getsystemtelemetry()
    
    # Assert top-level keys
    assert "cpu" in telemetry
    assert "memory" in telemetry
    assert "disk" in telemetry
    assert "network" in telemetry

    # Assert CPU details
    assert "percent" in telemetry["cpu"]
    assert "kernels_physical" in telemetry["cpu"]
    assert "kernels_logical" in telemetry["cpu"]

    # Assert Virtual Memory details
    assert "total_bytes" in telemetry["memory"]
    assert "percent" in telemetry["memory"]

    # Assert Disk details
    assert "percent" in telemetry["disk"]


def test_osinventory_summary_returns_json():
    sm = SystemManager()
    payload = json.loads(sm.osinventory("summary"))

    assert "platform" in payload
    assert "telemetry" in payload
    assert "disks" in payload


def test_osprocess_respects_policy():
    sm = SystemManager(rules={"allow_process_control": False})

    assert "process control is disabled" in sm.osprocess("terminate", "123456")


def test_osservice_respects_policy():
    sm = SystemManager(rules={"allow_service_control": False})

    assert "service control is disabled" in sm.osservice("start", "agenticos-test")


def test_ospackage_check_is_non_mutating():
    sm = SystemManager()
    payload = json.loads(sm.ospackage("check"))

    assert "available_package_managers" in payload


def test_ospackage_install_respects_policy():
    sm = SystemManager(rules={"allow_system_changes": False})

    assert "package installation is disabled" in sm.ospackage("install", "git")

