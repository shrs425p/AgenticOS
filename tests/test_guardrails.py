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


# ── Blue Zone (read_only) tests ────────────────────────────────────────────────

def test_blue_zone_blocks_workspace_write(tmp_path):
    """read_only=True blocks writes even inside the workspace."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    cfg = {
        "security": {"read_only_mode": True},
        "agent": {"workspace": str(ws)},
    }
    guard = PathGuard(cfg)
    assert guard.read_only is True

    allowed, msg = guard.check_path(str(ws / "file.txt"), "write")
    assert not allowed
    assert "READ_ONLY_MODE" in msg


def test_blue_zone_allows_workspace_read(tmp_path):
    """read_only=True must NOT block reads inside workspace."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    cfg = {
        "security": {"read_only_mode": True},
        "agent": {"workspace": str(ws)},
    }
    guard = PathGuard(cfg)

    allowed, _ = guard.check_path(str(ws / "file.txt"), "read")
    assert allowed


def test_blue_zone_allows_outside_read(tmp_path):
    """read_only=True must NOT block reads outside workspace."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    cfg = {
        "security": {"read_only_mode": True},
        "agent": {"workspace": str(ws)},
    }
    guard = PathGuard(cfg)

    allowed, _ = guard.check_path(str(outside / "notes.txt"), "read")
    assert allowed


def test_blue_zone_blocks_outside_write(tmp_path):
    """read_only=True blocks writes outside workspace too."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    cfg = {
        "security": {"read_only_mode": True, "require_hitm_outside_workspace": False},
        "agent": {"workspace": str(ws)},
    }
    guard = PathGuard(cfg)

    allowed, msg = guard.check_path(str(outside / "notes.txt"), "write")
    assert not allowed
    assert "READ_ONLY_MODE" in msg


def test_blue_zone_blocks_delete_operation(tmp_path):
    """read_only=True treats 'delete' as a write op and blocks it."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    cfg = {
        "security": {"read_only_mode": True},
        "agent": {"workspace": str(ws)},
    }
    guard = PathGuard(cfg)

    allowed, msg = guard.check_path(str(ws / "file.txt"), "delete")
    assert not allowed
    assert "READ_ONLY_MODE" in msg


def test_blue_zone_disabled_by_default(tmp_path):
    """read_only defaults to False when not set in config."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    cfg = {"agent": {"workspace": str(ws)}}
    guard = PathGuard(cfg)

    assert guard.read_only is False
    # Workspace writes should still be allowed
    allowed, _ = guard.check_path(str(ws / "file.txt"), "write")
    assert allowed


def test_blue_zone_blocked_paths_still_enforced(tmp_path):
    """read_only mode must still respect blocked_paths for reads."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    cfg = {
        "security": {
            "read_only_mode": True,
            "blocked_paths": [str(blocked)],
        },
        "agent": {"workspace": str(ws)},
    }
    guard = PathGuard(cfg)

    # Blocked path read should still be denied (blocked_paths checked before read_only)
    allowed, msg = guard.check_path(str(blocked / "secret.txt"), "read")
    assert not allowed
    assert "SECURITY POLICY" in msg


def test_guardrails_sensitive_shields(tmp_path):
    """PathGuard strictly shields sensitive credential/config files and tamper-proofs audit logs."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    cfg = {"agent": {"workspace": str(ws)}}
    guard = PathGuard(cfg)

    # 1. Credentials file (.env) shielded completely
    allowed, msg = guard.check_path(str(ws / ".env"), "read")
    assert not allowed
    assert "strictly blocked" in msg

    allowed, msg = guard.check_path(str(ws / "subfolder" / ".env"), "write")
    assert not allowed
    assert "strictly blocked" in msg

    # 2. Git internal data (.git) shielded completely
    allowed, msg = guard.check_path(str(ws / ".git" / "config"), "read")
    assert not allowed
    assert "strictly blocked" in msg

    # 3. Config files (config.yaml, config/*) read allowed, but modify/delete strictly blocked
    allowed, _ = guard.check_path(str(ws / "config.yaml"), "read")
    assert allowed

    allowed, msg = guard.check_path(str(ws / "config.yaml"), "write")
    assert not allowed
    assert "strictly blocked" in msg

    allowed, _ = guard.check_path(str(ws / "config" / "policy.yaml"), "read")
    assert allowed

    allowed, msg = guard.check_path(str(ws / "config" / "policy.yaml"), "delete")
    assert not allowed
    assert "strictly blocked" in msg

    # 4. Audit logs (data/logs/*, logs/*) read allowed, but modify/delete strictly blocked
    allowed, _ = guard.check_path(str(ws / "data" / "logs" / "agenticos.log"), "read")
    assert allowed

    allowed, msg = guard.check_path(str(ws / "data" / "logs" / "agenticos.log"), "write")
    assert not allowed
    assert "tamper-proof" in msg


def test_symlink_depth_real(tmp_path):
    import os
    ws = tmp_path / "workspace"
    ws.mkdir()
    
    # Create a chain of symlinks: link1 -> link2 -> link3 -> link4 -> link5 -> link6 -> target.txt
    target = ws / "target.txt"
    target.write_text("hello")
    
    try:
        # Try to create symlinks
        os.symlink("target.txt", str(ws / "link6"))
        os.symlink("link6", str(ws / "link5"))
        os.symlink("link5", str(ws / "link4"))
        os.symlink("link4", str(ws / "link3"))
        os.symlink("link3", str(ws / "link2"))
        os.symlink("link2", str(ws / "link1"))
    except OSError:
        # If symlinks cannot be created (e.g. on Windows without developer mode/admin),
        # skip the real filesystem test and we will rely on mock test.
        import pytest
        pytest.skip("System does not support symlink creation")
        
    cfg = {
        "security": {
            "enable_zone_guard": True,
        },
        "agent": {
            "workspace": str(ws)
        }
    }
    guard = PathGuard(cfg)
    
    # Resolving link2 has depth 5 (link2 -> link3 -> link4 -> link5 -> link6 -> target.txt), allowed
    allowed, _ = guard.check_path(str(ws / "link2"), "read")
    assert allowed
    
    # Resolving link1 has depth 6, blocked
    allowed, msg = guard.check_path(str(ws / "link1"), "read")
    assert not allowed
    assert "Symlink traversal depth exceeded limit of 5" in msg


def test_symlink_depth_mocked(monkeypatch):
    import pathlib
    import os
    
    links = {
        "link1": "link2",
        "link2": "link3",
        "link3": "link4",
        "link4": "link5",
        "link5": "link6",
        "link6": "target.txt",
    }
    
    def mock_is_symlink(self):
        return self.name in links
        
    def mock_readlink(path_str):
        name = pathlib.Path(path_str).name
        if name in links:
            return links[name]
        raise OSError("Not a symlink")
        
    monkeypatch.setattr(pathlib.Path, "is_symlink", mock_is_symlink)
    monkeypatch.setattr(os, "readlink", mock_readlink)
    monkeypatch.setattr(pathlib.Path, "resolve", lambda self, *args, **kwargs: self)
    
    cfg = {
        "security": {
            "enable_zone_guard": True,
        },
        "agent": {
            "workspace": "workspace"
        }
    }
    guard = PathGuard(cfg)
    
    # link2 has depth 5, allowed
    allowed, msg = guard.check_path("workspace/link2", "read")
    assert allowed, f"Disallowed reason: {msg}"
    
    # link1 has depth 6, blocked
    allowed, msg = guard.check_path("workspace/link1", "read")
    assert not allowed
    assert "Symlink traversal depth exceeded limit of 5" in msg

