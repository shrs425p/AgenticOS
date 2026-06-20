import os
import sys
import tempfile
import io
from unittest import mock
import pytest

from tools.plugin_validator import validate_plugins

def test_missing_plugin_dir():
    with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        with pytest.raises(SystemExit) as excinfo:
            validate_plugins("/non/existent/path/for/test/12345")

        assert excinfo.value.code == 1
        assert "does not exist" in mock_stdout.getvalue()

def test_valid_plugin():
    valid_content = """
def my_tool() -> str:
    return "ok"

my_tool._is_tool = True
my_tool._tool_name = "my_tool"
my_tool._tool_desc = "A valid tool"
"""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "my_tool.py")
        with open(file_path, "w") as f:
            f.write(valid_content)

        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as excinfo:
                validate_plugins(temp_dir)

            assert excinfo.value.code == 0
            assert "All plugins validated successfully." in mock_stdout.getvalue()

def test_missing_name():
    content = """
def my_tool() -> str:
    return "ok"

my_tool._is_tool = True
my_tool._tool_desc = "A valid tool"
"""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "my_tool.py")
        with open(file_path, "w") as f:
            f.write(content)

        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as excinfo:
                validate_plugins(temp_dir)

            assert excinfo.value.code == 1
            assert "Missing '_tool_name'" in mock_stdout.getvalue()

def test_missing_desc():
    content = """
def my_tool() -> str:
    return "ok"

my_tool._is_tool = True
my_tool._tool_name = "my_tool"
"""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "my_tool.py")
        with open(file_path, "w") as f:
            f.write(content)

        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as excinfo:
                validate_plugins(temp_dir)

            assert excinfo.value.code == 1
            assert "Missing '_tool_desc'" in mock_stdout.getvalue()

def test_missing_return_type():
    content = """
def my_tool():
    return "ok"

my_tool._is_tool = True
my_tool._tool_name = "my_tool"
my_tool._tool_desc = "A valid tool"
"""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "my_tool.py")
        with open(file_path, "w") as f:
            f.write(content)

        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as excinfo:
                validate_plugins(temp_dir)

            assert excinfo.value.code == 1
            assert "Missing return type annotation" in mock_stdout.getvalue()

def test_no_tool_functions():
    content = """
def normal_func():
    pass
"""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "my_tool.py")
        with open(file_path, "w") as f:
            f.write(content)

        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as excinfo:
                validate_plugins(temp_dir)

            assert excinfo.value.code == 1
            assert "No @tool functions found" in mock_stdout.getvalue()

def test_non_callable_tool_ignored():
    content = """
my_var = "not a callable"
class NotCallable:
    pass
obj = NotCallable()
obj._is_tool = True
obj._tool_name = "my_tool"
obj._tool_desc = "desc"
"""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "my_tool.py")
        with open(file_path, "w") as f:
            f.write(content)

        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as excinfo:
                validate_plugins(temp_dir)

            assert excinfo.value.code == 1
            assert "No @tool functions found" in mock_stdout.getvalue()
