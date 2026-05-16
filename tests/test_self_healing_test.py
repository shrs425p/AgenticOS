import json
from unittest.mock import patch

from tools.plugins.self_healing_test import self_healing_test

def test_self_healing_test_happy_path(tmp_path, monkeypatch):
    # Mock workspace and daily logs
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Run the test
    res_str = self_healing_test()
    result = json.loads(res_str)

    assert result["outcome"] == "success"
    assert "File missing, starting recovery." in result["steps"]
    assert "Catch FileNotFoundError" in result["recovery_actions"]
    assert "Create the file" in result["recovery_actions"]
    assert "Verify file exists and is readable" in result["recovery_actions"]
    assert "Delete the file after verification" in result["recovery_actions"]

    # Check if target file is deleted
    assert not (workspace / "healing_test_target.txt").exists()

    # Check if log is written
    daily_logs_dir = workspace / "daily_logs"
    assert daily_logs_dir.exists()
    log_files = list(daily_logs_dir.glob("self_healing_*.md"))
    assert len(log_files) == 1

    content = log_files[0].read_text()
    assert "**Outcome:** success" in content

def test_self_healing_test_workspace_readonly(tmp_path, monkeypatch):
    # Mock workspace and daily logs
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Mock writing to log directory so it doesn't fail on trying to log the failure
    with patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")):
        res_str = self_healing_test()
        result = json.loads(res_str)

        assert result["outcome"] == "failure"
        assert any("[ERROR] Failed during recovery steps:" in step for step in result["steps"])
        assert "Create the file" not in result["recovery_actions"]

def test_self_healing_test_log_file_write_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Mock the log file writing to raise an exception
    with patch("pathlib.Path.write_text"):

        # We need the first write (target_file) to succeed, but log_file to fail
        # This is tricky because both use write_text. Let's patch at the function level
        # Actually it's easier to mock the open or write inside the tool
        # Wait, instead of patching write_text which is used by both,
        # let's just create a read-only directory for daily_logs
        daily_logs_dir = workspace / "daily_logs"
        daily_logs_dir.mkdir(parents=True)
        # Make the daily_logs directory read-only
        daily_logs_dir.chmod(0o400)

        try:
            res_str = self_healing_test()
            result = json.loads(res_str)
            assert result["outcome"] == "failure"
        finally:
            # Restore permissions so tmp_path cleanup doesn't fail
            daily_logs_dir.chmod(0o777)
