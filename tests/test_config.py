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
        load_config("caching_test.yaml", force_reload=True)
        assert call_count == 2


def test_deep_merge():
    from core.runtime_config import _deep_merge
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 4, "e": 5}, "f": 6}

    result = _deep_merge(base, override)

    assert result["a"] == 1
    assert result["b"]["c"] == 4
    assert result["b"]["d"] == 3
    assert result["b"]["e"] == 5
    assert result["f"] == 6

    # Test with empty override
    assert _deep_merge({"a": 1}, None) == {"a": 1}

def test_read_yaml_file():
    from core.runtime_config import _read_yaml_file
    import pytest

    with mock.patch("builtins.open", mock.mock_open(read_data="key: value")):
        assert _read_yaml_file("test.yaml") == {"key": "value"}

    with mock.patch("builtins.open", mock.mock_open(read_data="string_value")):
        with pytest.raises(ValueError, match="Configuration file must contain a mapping"):
            _read_yaml_file("test.yaml")

@mock.patch("core.runtime_config._read_yaml_file")
@mock.patch("os.path.isdir")
@mock.patch("os.path.exists")
def test_load_layered_config_layers(mock_exists, mock_isdir, mock_read_yaml):
    from core.runtime_config import _load_layered_config

    mock_isdir.return_value = True
    # simulate some layers exist, some don't
    def mock_exists_side_effect(path):
        if "providers.yaml" in path:
            return True
        if "policy.yaml" in path:
            return True
        return False
    mock_exists.side_effect = mock_exists_side_effect

    def mock_read_yaml_side_effect(path):
        if "providers.yaml" in path:
            return {"provider_key": "provider_val"}
        if "policy.yaml" in path:
            return {"policy_key": "policy_val", "shared_key": "policy_wins"}
        if "test_root.yaml" in path:
            return {"root_key": "root_val", "shared_key": "root_wins"}
        return {}
    mock_read_yaml.side_effect = mock_read_yaml_side_effect

    merged, raw = _load_layered_config("test_root.yaml")

    # Assert merged contains keys from layers and root
    assert merged["provider_key"] == "provider_val"
    assert merged["policy_key"] == "policy_val"
    assert merged["root_key"] == "root_val"

    # Assert root overrides layers
    assert merged["shared_key"] == "root_wins"

    # Assert raw only has root stuff
    assert raw == {"root_key": "root_val", "shared_key": "root_wins"}

@mock.patch("os.path.exists")
def test_load_config_file_not_found(mock_exists):
    from core.runtime_config import load_config
    import pytest
    import sys

    # We must patch sys.modules to remove test modules so it doesn't bypass caching/reloading logic
    fake_modules = sys.modules.copy()
    fake_modules.pop("pytest", None)
    fake_modules.pop("unittest", None)

    mock_exists.return_value = False
    with mock.patch("sys.modules", fake_modules):
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config("missing.yaml", force_reload=True)

@mock.patch("core.runtime_config._load_layered_config")
@mock.patch("os.path.exists")
def test_load_config_empty(mock_exists, mock_load_layered):
    from core.runtime_config import load_config
    import pytest
    import sys

    fake_modules = sys.modules.copy()
    fake_modules.pop("pytest", None)
    fake_modules.pop("unittest", None)

    mock_exists.return_value = True
    # Return empty merged cfg
    mock_load_layered.return_value = ({}, {})

    with mock.patch("sys.modules", fake_modules):
        with pytest.raises(ValueError, match="Configuration file is empty or invalid"):
            load_config("empty.yaml", force_reload=True)

@mock.patch("core.runtime_config._load_layered_config")
@mock.patch("os.path.exists")
def test_load_config_path_resolutions(mock_exists, mock_load_layered):
    from core.runtime_config import load_config
    import sys

    fake_modules = sys.modules.copy()
    fake_modules.pop("pytest", None)
    fake_modules.pop("unittest", None)

    mock_exists.return_value = True

    mock_cfg = {
        "logging": {"file": "custom_log.log"},
        "memory": {"sqlite_db_path": "custom_db.sqlite"},
        "security": {"internal_data_dir": "custom_data_dir"}
    }
    mock_load_layered.return_value = (mock_cfg, {})

    with mock.patch("sys.modules", fake_modules):
        cfg = load_config("test.yaml", force_reload=True)

    assert os.path.isabs(cfg["logging"]["file"])
    assert cfg["logging"]["file"].endswith("custom_log.log")

    assert os.path.isabs(cfg["memory"]["sqlite_db_path"])
    assert cfg["memory"]["sqlite_db_path"].endswith("custom_db.sqlite")

    assert os.path.isabs(cfg["security"]["internal_data_dir"])
    assert cfg["security"]["internal_data_dir"].endswith("custom_data_dir")

@mock.patch("core.runtime_config._load_layered_config")
@mock.patch("os.path.exists")
def test_load_config_power_mode(mock_exists, mock_load_layered):
    from core.runtime_config import load_config
    import sys

    fake_modules = sys.modules.copy()
    fake_modules.pop("pytest", None)
    fake_modules.pop("unittest", None)

    mock_exists.return_value = True

    mock_cfg = {
        "autonomy": {"power_mode": True}
    }
    mock_load_layered.return_value = (mock_cfg, {})

    with mock.patch("sys.modules", fake_modules):
        cfg = load_config("test.yaml", force_reload=True)

    assert cfg["rules"]["allow_system_changes"] is True
    assert cfg["rules"]["allow_registry_edit"] is True
    assert cfg["rules"]["allow_service_control"] is True

    assert cfg["security"]["validate_commands"] is False

    assert cfg["rules"]["require_confirm_destructive"] is False
    assert cfg["agent"]["auto_confirm"] is True
    assert cfg["autonomy"]["autopilot"] is True
    assert cfg["autonomy"]["minimal_clarifications"] is True
    assert cfg["autonomy"]["enforce_progress"] is True

@mock.patch("core.runtime_config._load_layered_config")
@mock.patch("os.path.exists")
def test_load_config_numeric_normalization(mock_exists, mock_load_layered):
    from core.runtime_config import load_config
    import sys

    fake_modules = sys.modules.copy()
    fake_modules.pop("pytest", None)
    fake_modules.pop("unittest", None)

    mock_exists.return_value = True

    mock_cfg = {
        "cloud": {"nvidia": {"max_tokens": "100", "timeout": "30"}}
    }
    mock_load_layered.return_value = (mock_cfg, {})

    with mock.patch("sys.modules", fake_modules):
        cfg = load_config("test.yaml", force_reload=True)

    assert cfg["cloud"]["nvidia"]["max_tokens"] == 100
    assert cfg["cloud"]["nvidia"]["timeout"] == 30

@mock.patch("core.runtime_config._load_layered_config")
@mock.patch("os.path.exists")
def test_load_config_numeric_normalization_warning(mock_exists, mock_load_layered):
    from core.runtime_config import load_config
    import pytest
    import sys

    fake_modules = sys.modules.copy()
    fake_modules.pop("pytest", None)
    fake_modules.pop("unittest", None)

    mock_exists.return_value = True

    mock_cfg = {
        "cloud": {"nvidia": {"max_tokens": "invalid"}}
    }
    mock_load_layered.return_value = (mock_cfg, {})

    with mock.patch("sys.modules", fake_modules):
        with pytest.warns(UserWarning, match="Invalid numeric value in cloud.nvidia config"):
            cfg = load_config("test.yaml", force_reload=True)

    assert cfg["cloud"]["nvidia"]["max_tokens"] == "invalid"
