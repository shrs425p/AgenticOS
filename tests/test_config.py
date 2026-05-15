import os
from unittest import mock
import pytest

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
