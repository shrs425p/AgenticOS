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


def test_guardrails_invalid_path(tmp_path):
    from core.guardrails import PathGuard
    ws = tmp_path / "workspace"
    ws.mkdir()
    cfg = {"agent": {"workspace": str(ws)}}
    guard = PathGuard(cfg)

    # Passing an invalid path representation (e.g. integer)
    # to hit the exception block in check_path
    allowed, msg = guard.check_path(123, "read")
    assert not allowed
    assert "Invalid path" in msg

def test_guardrails_ask_human_exceptions(tmp_path):
    from core.guardrails import PathGuard
    cfg = {"agent": {"workspace": str(tmp_path)}}
    guard = PathGuard(cfg)
    from unittest.mock import patch

    with patch("builtins.input", side_effect=KeyboardInterrupt):
        assert guard.ask_human("path", "write") is False

    with patch("builtins.input", side_effect=EOFError):
        assert guard.ask_human("path", "write") is False

def test_guardrails_workspace_exception_mock(tmp_path):
    from core.guardrails import PathGuard
    ws = tmp_path / "workspace"
    ws.mkdir()
    guard = PathGuard({"agent": {"workspace": str(ws)}})

    from unittest.mock import MagicMock
    mock_root = MagicMock()
    mock_root.__eq__.side_effect = Exception("Mocked Exception")
    guard.workspace_root = mock_root

    assert guard.check_path("test.txt", "read")[0] is True

def test_guardrails_blocked_exception_mock(tmp_path):
    from core.guardrails import PathGuard
    ws = tmp_path / "workspace"
    ws.mkdir()
    guard = PathGuard({"agent": {"workspace": str(ws)}})

    from unittest.mock import MagicMock
    mock_blocked = MagicMock()
    mock_blocked.__eq__.side_effect = Exception("Mocked Exception")
    guard.blocked_paths = [mock_blocked]

    assert guard.check_path("test.txt", "read")[0] is True

def test_guardrails_workspace_green_zone_exception(tmp_path):
    from core.guardrails import PathGuard
    ws = tmp_path / "workspace"
    ws.mkdir()
    guard = PathGuard({"agent": {"workspace": str(ws)}})

    from unittest.mock import MagicMock
    import pathlib

    class ThrowingPath(type(pathlib.Path())):
        def __eq__(self, other):
            raise Exception("Force exception in green zone")

        @property
        def parents(self):
            raise Exception("Force exception in green zone")

    try:
        # Construct the throwing path by overriding the target
        ThrowingPath("some/path")
    except Exception:
        pass

    from unittest.mock import patch
    with patch("core.guardrails.Path") as mock_path:
        mock_instance = MagicMock()
        mock_instance.resolve.return_value = mock_instance
        mock_instance.is_absolute.return_value = True

        mock_instance.__eq__.side_effect = Exception("Mocked Eq")
        type(mock_instance).parents = property(lambda self: (_ for _ in ()).throw(Exception("Mocked Parents")))

        mock_path.return_value = mock_instance

        # It should fall back to YELLOW zone
        assert guard.check_path("test", "read")[0] is True
