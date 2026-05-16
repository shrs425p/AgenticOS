"""Tests for the plugin health check tool."""

import pytest
from pathlib import Path
from tools.plugins.plugin_health_check import plugin_health_check

@pytest.fixture
def mock_plugins_dir(tmp_path, monkeypatch):
    """Fixture to create a mock plugins directory and point the tool to it."""
    plugins_dir = tmp_path / "tools" / "plugins"
    plugins_dir.mkdir(parents=True)

    # Also need a mock daily logs dir so we don't write to the real workspace
    daily_logs_dir = tmp_path / "workspace" / "daily_logs"
    daily_logs_dir.mkdir(parents=True)

    # We must patch Path to intercept the specific paths
    original_path = Path

    class MockPath(type(Path())):
        def __new__(cls, *args, **kwargs):
            if args and args[0] == "tools/plugins":
                return original_path(str(plugins_dir))
            elif args and args[0] == "workspace/daily_logs":
                return original_path(str(daily_logs_dir))
            return original_path(*args, **kwargs)

    monkeypatch.setattr("tools.plugins.plugin_health_check.Path", MockPath)

    return plugins_dir

def test_plugin_health_check_valid(mock_plugins_dir):
    """Test with a valid plugin."""
    plugin_file = mock_plugins_dir / "valid_plugin.py"
    plugin_file.write_text('"""Docstring."""\n\ndef my_tool():\n    pass')

    results = plugin_health_check()
    assert results == {"valid_plugin.py": "ok"}

def test_plugin_health_check_syntax_error(mock_plugins_dir):
    """Test with a plugin that has a syntax error."""
    plugin_file = mock_plugins_dir / "syntax_error_plugin.py"
    plugin_file.write_text('"""Docstring."""\n\ndef my_tool() # missing colon\n    pass')

    results = plugin_health_check()
    assert results == {"syntax_error_plugin.py": "syntax_error"}

def test_plugin_health_check_missing_description(mock_plugins_dir):
    """Test with a plugin missing a module docstring."""
    plugin_file = mock_plugins_dir / "missing_desc_plugin.py"
    plugin_file.write_text('def my_tool():\n    pass')

    results = plugin_health_check()
    assert results == {"missing_desc_plugin.py": "missing_description"}

def test_plugin_health_check_no_callable(mock_plugins_dir):
    """Test with a plugin that has no callable."""
    plugin_file = mock_plugins_dir / "no_callable_plugin.py"
    plugin_file.write_text('"""Docstring."""\n\nx = 1')

    results = plugin_health_check()
    assert results == {"no_callable_plugin.py": "no_callable"}

def test_plugin_health_check_empty_dir(mock_plugins_dir):
    """Test with an empty directory."""
    results = plugin_health_check()
    assert results == {}

def test_plugin_health_check_skip_init(mock_plugins_dir):
    """Test that __init__.py is skipped."""
    init_file = mock_plugins_dir / "__init__.py"
    init_file.write_text('"""Docstring."""\n\ndef my_tool():\n    pass')
    plugin_file = mock_plugins_dir / "valid_plugin.py"
    plugin_file.write_text('"""Docstring."""\n\ndef my_tool():\n    pass')

    results = plugin_health_check()
    assert "__init__.py" not in results
    assert results == {"valid_plugin.py": "ok"}
