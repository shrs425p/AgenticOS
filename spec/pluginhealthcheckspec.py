"""Tests for the plugin health check tool."""

import pytest
from pathlib import Path
from ops.addons.health import pluginhealthcheck

@pytest.fixture
def mock_plugins_dir(tmp_path, monkeypatch):
    """Fixture to create a mock plugins directory and point the tool to it."""
    plugins_dir = tmp_path / "ops" / "plugins"
    plugins_dir.mkdir(parents=True)

    # Also need a mock daily logs dir so we don't write to the real workspace
    daily_logs_dir = tmp_path / "workspace" / "daily_logs"
    daily_logs_dir.mkdir(parents=True)

    # We must patch Path to intercept the specific paths
    original_path = Path

    class MockPath(type(Path())):
        def __new__(cls, *args, **kwargs):
            if args and args[0] == "ops/addons":
                return original_path(str(plugins_dir))
            elif args and args[0] == "workspace/daily_logs":
                return original_path(str(daily_logs_dir))
            return original_path(*args, **kwargs)

    monkeypatch.setattr("ops.addons.health.Path", MockPath)

    return plugins_dir

def test_pluginhealthcheck_valid(mock_plugins_dir):
    """Test with a valid plugin."""
    plugin_file = mock_plugins_dir / "valid_plugin.py"
    plugin_file.write_text('"""Docstring."""\n\ndef my_tool():\n    pass')

    results = pluginhealthcheck()
    assert results == {"valid_plugin.py": "ok"}

def test_pluginhealthcheck_syntax_error(mock_plugins_dir):
    """Test with a plugin that has a syntax error."""
    plugin_file = mock_plugins_dir / "syntax_error_plugin.py"
    plugin_file.write_text('"""Docstring."""\n\ndef my_tool() # missing colon\n    pass')

    results = pluginhealthcheck()
    assert results == {"syntax_error_plugin.py": "syntax_error"}

def test_pluginhealthcheck_missing_description(mock_plugins_dir):
    """Test with a plugin missing a module docstring."""
    plugin_file = mock_plugins_dir / "missing_desc_plugin.py"
    plugin_file.write_text('def my_tool():\n    pass')

    results = pluginhealthcheck()
    assert results == {"missing_desc_plugin.py": "missing_description"}

def test_pluginhealthcheck_no_callable(mock_plugins_dir):
    """Test with a plugin that has no callable."""
    plugin_file = mock_plugins_dir / "no_callable_plugin.py"
    plugin_file.write_text('"""Docstring."""\n\nx = 1')

    results = pluginhealthcheck()
    assert results == {"no_callable_plugin.py": "no_callable"}

def test_pluginhealthcheck_empty_dir(mock_plugins_dir):
    """Test with an empty directory."""
    results = pluginhealthcheck()
    assert results == {}

def test_pluginhealthcheck_skip_init(mock_plugins_dir):
    """Test that __init__.py is skipped."""
    init_file = mock_plugins_dir / "__init__.py"
    init_file.write_text('"""Docstring."""\n\ndef my_tool():\n    pass')
    plugin_file = mock_plugins_dir / "valid_plugin.py"
    plugin_file.write_text('"""Docstring."""\n\ndef my_tool():\n    pass')

    results = pluginhealthcheck()
    assert "__init__.py" not in results
    assert results == {"valid_plugin.py": "ok"}
