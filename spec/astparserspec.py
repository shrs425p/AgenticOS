"""Unit spec for the AST parser plugin."""

import os
import json
import pytest
import tempfile
import shutil

from ops.addons.ast import (
    astparsefile,
    astmapdirectory
)


@pytest.fixture
def temp_python_file():
    """Fixture to create a temporary Python file with nested structures."""
    fd, path = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    
    code = '''
"""Module docstring"""

def simple_function(x: int) -> int:
    """Returns x."""
    return x
    
class Animal:
    """Base animal class."""
    def __init__(self, name: str):
        self.name = name
        
    def speak(self):
        """Make a sound."""
        pass
        
    class NestedClass:
        """A nested class."""
        async def async_method(self) -> bool:
            return True
'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
        
    yield path
    
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def temp_python_project():
    """Fixture to create a temporary directory with multiple Python files."""
    temp_dir = tempfile.mkdtemp()
    
    # Create main.py
    with open(os.path.join(temp_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write('def main():\n    pass')
        
    # Create subfolder and util.py
    os.makedirs(os.path.join(temp_dir, "utils"))
    with open(os.path.join(temp_dir, "utils", "math.py"), "w", encoding="utf-8") as f:
        f.write('class MathUtil:\n    def add(a, b):\n        return a + b')
        
    # Create ignored node_modules folder
    os.makedirs(os.path.join(temp_dir, "node_modules"))
    with open(os.path.join(temp_dir, "node_modules", "ignore.py"), "w", encoding="utf-8") as f:
        f.write('def ignore_me():\n    pass')
        
    yield temp_dir
    
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_astparsefile(temp_python_file):
    result = astparsefile(temp_python_file)
    
    assert "Error" not in result
    data = json.loads(result)
    
    assert data["file"] == os.path.basename(temp_python_file)
    
    structure = data["structure"]
    
    # Check simple function
    assert structure[0]["name"] == "simple_function"
    assert "x: int" in structure[0]["args"][0]
    assert structure[0]["returns"] == "int"
    assert structure[0]["docstring"] == "Returns x."
    
    # Check class
    assert structure[1]["type"] == "class"
    assert structure[1]["name"] == "Animal"
    assert structure[1]["docstring"] == "Base animal class."
    
    # Check methods inside class
    methods = structure[1]["methods"]
    assert len(methods) == 3 # __init__, speak, NestedClass
    
    assert methods[0]["name"] == "__init__"
    assert methods[1]["name"] == "speak"
    
    # Check nested class
    nested_class = methods[2]
    assert nested_class["type"] == "class"
    assert nested_class["name"] == "NestedClass"
    
    # Check async method inside nested class
    nested_methods = nested_class["methods"]
    assert nested_methods[0]["type"] == "async_method"
    assert nested_methods[0]["name"] == "async_method"


def test_astparsefile_not_python():
    result = astparsefile("nonexistent.txt")
    assert "Error: File not found at nonexistent.txt" in result

def test_astparsefile_non_py_exists(temp_python_file):
    # Rename to .txt temporarily
    txt_path = temp_python_file.replace(".py", ".txt")
    import shutil
    shutil.copy(temp_python_file, txt_path)
    try:
        result = astparsefile(txt_path)
        assert "Error: File" in result and "is not a Python (.py) file." in result
    finally:
        if os.path.exists(txt_path):
            os.remove(txt_path)


def test_astmapdirectory(temp_python_project):
    result = astmapdirectory(temp_python_project)
    
    assert "Error" not in result
    data = json.loads(result)
    
    # Check files are correctly mapped
    assert "main.py" in data
    assert os.path.join("utils", "math.py") in data
    
    # Check node_modules was ignored
    assert os.path.join("node_modules", "ignore.py") not in data
    
    # Check structure of utils/math.py
    math_struct = data[os.path.join("utils", "math.py")]
    assert math_struct[0]["type"] == "class"
    assert math_struct[0]["name"] == "MathUtil"
    assert math_struct[0]["methods"][0]["name"] == "add"
