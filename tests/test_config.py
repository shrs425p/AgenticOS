import os
from unittest import mock

from core.runtime_config import load_config, resolve_local_path, default_structure

def test_resolve_local_path():
    path = resolve_local_path("test_dir")
    assert os.path.isabs(path)
    assert path.endswith("test_dir")

@mock.patch("core.runtime_config._read_yaml_file")
@mock.patch("os.path.isdir")
@mock.patch("os.path.exists")
def test_load_config_defaults(mock_exists, mock_isdir, mock_read_yaml):
    # Setup mocks so it looks like no config files exist except a mock root config
    mock_isdir.return_value = False
    mock_exists.return_value = True
    
    # Return basic dict for root config to avoid ValueError
    mock_read_yaml.return_value = {"agent": {}}
    
    cfg = load_config("mock_config.yaml")
    
    # Assert defaults are hydrated
    for key in default_structure:
        assert key in cfg
    
    assert "endpoints" in cfg
    assert "windows_paths" in cfg
    assert "policy" in cfg
    assert "redaction_patterns" in cfg["policy"]


@mock.patch("core.runtime_config._read_yaml_file")
@mock.patch("os.path.isdir")
@mock.patch("os.path.exists")
def test_load_config_caching_behavior(mock_exists, mock_isdir, mock_read_yaml):
    mock_isdir.return_value = False
    mock_exists.return_value = True
    
    call_count = 0
    def mock_read(path):
        nonlocal call_count
        call_count += 1
        return {"agent": {"workspace": "workspace"}}
        
    mock_read_yaml.side_effect = mock_read
    
    import sys
    fake_modules = sys.modules.copy()
    fake_modules.pop("pytest", None)
    fake_modules.pop("unittest", None)
    
    with mock.patch("sys.modules", fake_modules):
        from core.runtime_config import _CONFIG_CACHE
        _CONFIG_CACHE.clear()
        
        # 1. First load from disk
        cfg1 = load_config("caching_test.yaml")
        assert call_count == 1
        
        # 2. Second load from cache (count remains 1)
        cfg2 = load_config("caching_test.yaml")
        assert call_count == 1
        
        # Verify deepcopy isolation
        old_workspace = cfg1["agent"]["workspace"]
        cfg2["agent"]["workspace"] = "mutated_workspace"
        assert cfg1["agent"]["workspace"] == old_workspace
        
        # 3. Forced reload loads from disk again (count increases)
        cfg3 = load_config("caching_test.yaml", force_reload=True)
        assert call_count == 2

