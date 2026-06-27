from kernel.stalls import StallMonitor

def test_stall_monitor_categories():
    monitor = StallMonitor()
    assert monitor.get_category("read_file") == "file operations"
    assert monitor.get_category("websearch") == "network"
    assert monitor.get_category("install_package") == "package install"
    assert monitor.get_category("runcommand") == "general"

def test_stall_monitor_no_stall():
    monitor = StallMonitor()
    warning = monitor.check_stall("read_file", 10.0)
    assert warning is None

def test_stall_monitor_stall_detected():
    monitor = StallMonitor()
    warning = monitor.check_stall("read_file", 35.0)
    assert warning is not None
    assert warning.category == "file operations"
    assert warning.threshold == 30.0
    assert warning.elapsed == 35.0
    assert "ripgrep" in warning.suggestion

    warning = monitor.check_stall("web_fetch", 65.0)
    assert warning is not None
    assert warning.category == "network"
    assert warning.threshold == 60.0
    assert "browser automation" in warning.suggestion
