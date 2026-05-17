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
    assert guard.check_path(str(ws / "test.txt"), "read")[0]
    assert guard.check_path(str(ws / "test.txt"), "write")[0]
    
    # Relative paths resolve to workspace
    assert guard.check_path("test2.txt", "write")[0]

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
    assert not allowed
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
    assert guard.check_path(str(outside_dir / "file.txt"), "read")[0]
    
    # Write outside workspace requires hitm
    allowed, msg = guard.check_path(str(outside_dir / "file.txt"), "write")
    assert not allowed
    assert "HITM_REQUIRED" in msg

def test_guardrails_disabled(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    cfg = {
        "security": {
            "enable_zone_guard": False
        },
        "agent": {
            "workspace": str(ws)
        }
    }
    guard = PathGuard(cfg)
    # Everything should be allowed
    assert guard.check_path("any_path", "write")[0]

def test_guardrails_no_hitm_required(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    cfg = {
        "security": {
            "require_hitm_outside_workspace": False
        },
        "agent": {
            "workspace": str(ws)
        }
    }
    guard = PathGuard(cfg)
    assert guard.check_path(str(tmp_path / "outside.txt"), "write")[0]

def test_guardrails_ask_human(tmp_path):
    cfg = {
        "agent": {
            "workspace": str(tmp_path)
        }
    }
    
    # 1. Custom on_confirm handler
    def handler(path, op):
        return True
    guard = PathGuard(cfg, on_confirm=handler)
    assert guard.ask_human("path", "read") is True
    
    # 2. CLI fallback y
    guard_cli = PathGuard(cfg)
    from unittest.mock import patch
    with patch("builtins.input", return_value="y"):
        assert guard_cli.ask_human("path", "read") is True
        
    # 3. CLI fallback n
    with patch("builtins.input", return_value="n"):
        assert guard_cli.ask_human("path", "read") is False

