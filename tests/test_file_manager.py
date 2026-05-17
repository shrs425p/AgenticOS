import pytest
from pathlib import Path
from tools.filesystem import FileManager

def test_file_manager_init(tmp_path):
    # Default init
    fm = FileManager(base_dir=str(tmp_path / "workspace"))
    assert fm.base_dir == (tmp_path / "workspace").resolve()
    assert fm._internal_data_dir is None

    # Init with internal data dir rule
    rules = {
        "internal_data_dir": str(tmp_path / "internal")
    }
    fm2 = FileManager(rules=rules, base_dir=str(tmp_path / "workspace"))
    assert fm2._internal_data_dir == (tmp_path / "internal").resolve()

def test_deny_internal_writes(tmp_path):
    internal_dir = tmp_path / "internal"
    internal_dir.mkdir()
    
    rules = {
        "internal_data_dir": str(internal_dir),
        "protect_internal_data": True,
        "allow_internal_data_write": False
    }
    fm = FileManager(rules=rules, base_dir=str(tmp_path / "workspace"))
    
    # Try writing to a path inside internal dir
    protected_file = internal_dir / "secret.txt"
    
    with pytest.raises(PermissionError) as excinfo:
        fm._deny_internal_writes(protected_file)
    assert "Internal data dir is protected" in str(excinfo.value)
    
    # Disable protect_internal_data -> should not raise
    fm.rules["protect_internal_data"] = False
    fm._deny_internal_writes(protected_file)
    
    # Enable protect but allow write -> should not raise
    fm.rules["protect_internal_data"] = True
    fm.rules["allow_internal_data_write"] = True
    fm._deny_internal_writes(protected_file)

def test_deny_file_modify_and_delete(tmp_path):
    rules = {
        "allow_file_modify": False,
        "allow_file_delete": False
    }
    fm = FileManager(rules=rules, base_dir=str(tmp_path / "workspace"))
    
    with pytest.raises(PermissionError) as excinfo:
        fm._deny_file_modify()
    assert "File modification is disabled" in str(excinfo.value)
    
    with pytest.raises(PermissionError) as excinfo:
        fm._deny_file_delete()
    assert "File deletion is disabled" in str(excinfo.value)

def test_is_drive_root(tmp_path):
    fm = FileManager(base_dir=str(tmp_path))
    # A generic temporary path shouldn't be drive root
    assert not fm._is_drive_root(tmp_path)
    # Check anchor root
    root = Path(tmp_path.anchor)
    assert fm._is_drive_root(root)

def test_deny_reserved_path(tmp_path):
    rules = {
        "allow_reserved_path_patterns": False,
        "reserved_path_patterns": [".git", "passwd"]
    }
    fm = FileManager(rules=rules, base_dir=str(tmp_path / "workspace"))
    
    with pytest.raises(PermissionError) as excinfo:
        fm._deny_reserved_path(Path("/etc/passwd"))
    assert "matches reserved pattern" in str(excinfo.value)
    
    # Non-reserved should pass
    fm._deny_reserved_path(Path("/etc/hosts"))

def test_resolve_path(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    rules = {
        "restrict_paths": True,
        "allow_reserved_path_patterns": True
    }
    fm = FileManager(rules=rules, base_dir=str(workspace))
    
    # 1. Non-absolute path rebased in workspace
    resolved = fm._resolve("test.txt")
    assert resolved == (workspace / "test.txt").resolve()
    
    # 2. Path starting with workspace name rebased properly
    resolved = fm._resolve("workspace/sub/test.txt")
    assert resolved == (workspace / "sub" / "test.txt").resolve()
    
    # 3. Absolute path outside rebased to base_dir / p.name when restrict_paths is True
    resolved = fm._resolve(str(tmp_path / "outside.txt"))
    assert resolved == (workspace / "outside.txt").resolve()
    
    # 4. Absolute path respected when restrict_paths is False
    fm.rules["restrict_paths"] = False
    resolved = fm._resolve(str(tmp_path / "outside.txt"))
    assert resolved == (tmp_path / "outside.txt").resolve()

def test_file_manager_exceptions(tmp_path):
    from unittest.mock import patch
    
    # 1. Test init exception for internal_data_dir resolve
    orig_resolve = Path.resolve
    def resolve_side_effect_init(self_path, *args, **kwargs):
        if "some_dir" in str(self_path):
            raise Exception("resolve error")
        return orig_resolve(self_path, *args, **kwargs)
        
    with patch.object(Path, "resolve", side_effect=resolve_side_effect_init, autospec=True):
        fm = FileManager(rules={"internal_data_dir": "some_dir"}, base_dir=str(tmp_path))
        assert fm._internal_data_dir is None
        
    # 2. Test exception in _deny_internal_writes try block
    fm = FileManager(
        rules={
            "internal_data_dir": str(tmp_path / "internal"),
            "protect_internal_data": True
        },
        base_dir=str(tmp_path / "workspace")
    )
    
    def resolve_side_effect_deny(self_path, *args, **kwargs):
        if "secret.txt" in str(self_path):
            raise ValueError("resolve error")
        return orig_resolve(self_path, *args, **kwargs)
        
    with patch.object(Path, "resolve", side_effect=resolve_side_effect_deny, autospec=True):
        # should return/pass silently on generic exception
        fm._deny_internal_writes(tmp_path / "internal" / "secret.txt")
        
    # 3. Test exception in _resolve when restrict_paths is True
    fm_restrict = FileManager(rules={"restrict_paths": True}, base_dir=str(tmp_path / "workspace"))
    
    class BrokenString:
        def __str__(self):
            raise TypeError("broken str")
            
    mock_resolved = BrokenString()
    
    # Construct a truly absolute path dynamically
    abs_path_str = str(tmp_path.resolve().anchor).replace("\\", "/") + "abs/path.txt"
    
    def resolve_side_effect_restrict(self_path, *args, **kwargs):
        if str(self_path).replace("\\", "/").endswith("abs/path.txt"):
            return mock_resolved
        return orig_resolve(self_path, *args, **kwargs)
        
    with patch.object(Path, "resolve", side_effect=resolve_side_effect_restrict, autospec=True):
        # resolved will fallback to base_dir / p.name
        resolved = fm_restrict._resolve(abs_path_str)
        assert resolved == (tmp_path / "workspace" / "path.txt").resolve()






