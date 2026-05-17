import os
import json
import pytest
from core.audit_logger import (
    AuditLogger,
    _redact,
    _estimate_tokens,
    infer_success,
    _now_iso
)

def test_redact():
    assert _redact(None) == ""
    assert _redact("") == ""
    text = "NVIDIA_API_KEY=abcde123"
    redacted = _redact(text)
    assert redacted == "NVIDIA_API_KEY=[REDACTED]"
    
    # Test fallback pattern match
    text2 = "Authorization: Bearer mysecrettoken12345"
    redacted2 = _redact(text2)
    assert redacted2 == "Authorization: Bearer [REDACTED]"
    
    # Test custom pattern
    custom_patterns = [(r"secret_([a-z]+)", r"[HIDDEN_\1]")]
    assert _redact("my secret_abc code", patterns=custom_patterns) == "my [HIDDEN_abc] code"

def test_estimate_tokens():
    assert _estimate_tokens(None) == 1
    assert _estimate_tokens("") == 1
    assert _estimate_tokens("a" * 40) == 10

def test_infer_success():
    assert infer_success(None) is True
    assert infer_success("") is True
    assert infer_success("all good") is True
    assert infer_success("Error: bad argument") is False
    assert infer_success("permission denied to write file") is False
    assert infer_success("File not found") is False

def test_audit_logger_init(tmp_path):
    log_dir = str(tmp_path / "logs")
    logger = AuditLogger(log_dir)
    assert os.path.exists(log_dir)
    assert logger.session_log.endswith("session.jsonl")
    assert logger.tools_log.endswith("tools.jsonl")

def test_audit_logger_session_start_end(tmp_path):
    log_dir = str(tmp_path)
    logger = AuditLogger(log_dir, enabled=True, fmt="both")
    
    logger.session_start("sess_1", "nvidia", "llama", "/workspace")
    logger.session_end("sess_1", "completed")
    
    # Verify JSONL
    with open(logger.session_log, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 2
        start_evt = json.loads(lines[0])
        assert start_evt["event"] == "session_start"
        assert start_evt["session_id"] == "sess_1"
        assert start_evt["model"] == "llama"
        
        end_evt = json.loads(lines[1])
        assert end_evt["event"] == "session_end"
        assert end_evt["status"] == "completed"

    # Verify LOG text
    with open(logger.session_text, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "session_start session_id=sess_1" in log_content
        assert "session_end session_id=sess_1" in log_content

def test_audit_logger_tool_call(tmp_path):
    logger = AuditLogger(str(tmp_path), enabled=True, fmt="both")
    
    logger.tool_call(
        session_id="sess_1",
        tool_name="read_file",
        tool_args="path=test.md",
        started_ts=100.0,
        ended_ts=101.5,
        success=True,
        validation="VALID",
        observation_preview="file content"
    )
    
    with open(logger.tools_log, "r", encoding="utf-8") as f:
        evt = json.loads(f.read())
        assert evt["event"] == "tool_call"
        assert evt["tool"] == "read_file"
        assert evt["duration_ms"] == 1500
        assert evt["success"] is True

    with open(logger.tools_text, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "tool=read_file" in log_content
        assert "duration_ms=1500" in log_content

def test_audit_logger_error(tmp_path):
    logger = AuditLogger(str(tmp_path), enabled=True, fmt="both")
    logger.error("sess_1", "runtime", "something failed")
    
    with open(logger.errors_log, "r", encoding="utf-8") as f:
        evt = json.loads(f.read())
        assert evt["event"] == "error"
        assert evt["message"] == "something failed"

def test_audit_logger_path_seen(tmp_path):
    logger = AuditLogger(str(tmp_path), enabled=True, fmt="both")
    
    # Ignore empty
    logger.path_seen("sess_1", "test_tool", "")
    assert not os.path.exists(logger.paths_log)
    
    # Path seen
    logger.path_seen("sess_1", "test_tool", "/a/b/c")
    with open(logger.paths_log, "r", encoding="utf-8") as f:
        evt = json.loads(f.read())
        assert evt["path"] == "/a/b/c"
    
    # Duplicate path seen should be ignored
    logger.path_seen("sess_1", "test_tool", "/a/b/c")
    with open(logger.paths_log, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1

def test_paths_from_event(tmp_path):
    logger = AuditLogger(str(tmp_path), enabled=True, fmt="both")
    
    # Create dummy files for existence checks
    ws = tmp_path / "workspace"
    ws.mkdir()
    f1 = ws / "test1.md"
    f1.write_text("dummy")
    
    logger.paths_from_event(
        session_id="sess_1",
        tool="test",
        tool_args='{"path": "test1.md"}',
        observation="Read test1.md successfully",
        base_dir=str(tmp_path),
        workspace_dir=str(ws)
    )
    
    # test1.md should be resolved
    with open(logger.paths_log, "r", encoding="utf-8") as f:
        evt = json.loads(f.read())
        assert evt["event"] == "path_seen"
        assert "test1.md" in evt["path"]
        assert evt["kind"] == "resolved"

def test_disabled_logger(tmp_path):
    logger = AuditLogger(str(tmp_path), enabled=False)
    logger.session_start("s", "p", "m", "w")
    assert not os.path.exists(logger.session_log)
    logger.path_seen("s", "t", "p")
    assert not os.path.exists(logger.paths_log)
