import os
from tools.plugins.log_analyzer import search_logs, get_log_errors, _get_log_path
from unittest.mock import patch

def test_search_logs_file_missing():
    with patch("os.path.exists", return_value=False):
        res = search_logs("test")
        assert "not found" in res

def test_search_logs_success(tmp_path):
    log_file = tmp_path / "agenticos.log"
    log_content = (
        "[2026-05-20 12:00:00] [INFO] [startup] Starting AgenticOS...\n"
        "[2026-05-20 12:00:01] [WARNING] [core] Slow connection detected.\n"
        "[2026-05-20 12:00:02] [ERROR] [runtime] Failed to open folder.\n"
    )
    log_file.write_text(log_content, encoding="utf-8")

    with patch("tools.plugins.log_analyzer._get_log_path", return_value=str(log_file)):
        # Test basic search
        res1 = search_logs("WARNING")
        assert "Slow connection detected" in res1
        assert "Failed to open folder" not in res1

        # Test case-insensitivity
        res2 = search_logs("starting")
        assert "Starting AgenticOS" in res2

        # Test limit
        res3 = search_logs("2026", limit=1)
        assert len(res3.splitlines()) == 1

        # Test empty query
        res4 = search_logs("")
        assert "query parameter is empty" in res4

        # Test query not found
        res5 = search_logs("NotThere")
        assert "No matches found" in res5

def test_get_log_errors(tmp_path):
    log_file = tmp_path / "agenticos.log"
    log_content = (
        "[2026-05-20 12:00:00] [INFO] [startup] Starting...\n"
        "[2026-05-20 12:00:01] [WARNING] [core] warning 1\n"
        "[2026-05-20 12:00:02] [ERROR] [runtime] error 1\n"
        "Traceback (most recent call last):\n"
        "  File \"main.py\", line 10, in <module>\n"
        "    some_function()\n"
        "Exception: crash!\n"
    )
    log_file.write_text(log_content, encoding="utf-8")

    with patch("tools.plugins.log_analyzer._get_log_path", return_value=str(log_file)):
        res = get_log_errors()
        assert "Errors detected: 1" in res
        assert "Warnings detected: 1" in res
        assert "Tracebacks/Exceptions: 1" in res
        assert "error 1" in res
        assert "warning 1" in res
        assert "Exception: crash!" in res
