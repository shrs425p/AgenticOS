import pytest
from pathlib import Path
from core.guardrails import PathGuard

def test_guardrails_workspace_access(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    
    cfg = {
        "security": {
            "enable_zone_guard": True,
        },
        "agent": {
            "workspace": str(ws)
        }
    }
    
    guard = PathGuard(cfg)
    
    # Inside workspace is allowed for read and write
    assert guard.check_path(str(ws / "test.txt"), "read")[0] == True
    assert guard.check_path(str(ws / "test.txt"), "write")[0] == True
    
    # Relative paths resolve to workspace
    assert guard.check_path("test2.txt", "write")[0] == True

def test_guardrails_blocked_paths(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    
    blocked_dir = tmp_path / "blocked"
    blocked_dir.mkdir()
    
    cfg = {
        "security": {
            "blocked_paths": [str(blocked_dir)]
        },
        "agent": {
            "workspace": str(ws)
        }
    }
    
    guard = PathGuard(cfg)
    
    # Blocked paths should fail
    allowed, msg = guard.check_path(str(blocked_dir / "secret.txt"), "read")
    assert allowed == False
    assert "blocked" in msg

def test_guardrails_outside_workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    
    cfg = {
        "security": {
            "require_hitm_outside_workspace": True
        },
        "agent": {
            "workspace": str(ws)
        }
    }
    
    guard = PathGuard(cfg)
    
    # Read outside workspace is allowed
    assert guard.check_path(str(outside_dir / "file.txt"), "read")[0] == True
    
    # Write outside workspace requires hitm
    allowed, msg = guard.check_path(str(outside_dir / "file.txt"), "write")
    assert allowed == False
    assert "HITM_REQUIRED" in msg
