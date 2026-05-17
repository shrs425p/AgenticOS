import os
import shutil
import pytest
from pathlib import Path
from tools.terminal.paths import PathsMixin

class MockPathsTools(PathsMixin):
    pass

def test_which():
    tool = MockPathsTools()
    # Check that python/pytest can be found
    executable = "python" if os.name == "nt" else "sh"
    res = tool.which(executable)
    assert res != ""
    assert Path(res).exists()
    
    # Check invalid executable
    assert tool.which("nonexistent_executable_12345") == ""

def test_special_paths():
    tool = MockPathsTools()
    res = tool.special_paths()
    assert "cwd=" in res
    assert "TEMP=" in res or "TMP=" in res

def test_locate_path(tmp_path):
    tool = MockPathsTools()
    
    # Empty name check
    assert tool.locate_path("") == "Error: name required."
    
    # Create mock target files
    sub1 = tmp_path / "sub1"
    sub1.mkdir()
    target1 = sub1 / "target.txt"
    target1.write_text("found 1")
    
    sub2 = tmp_path / "sub2"
    sub2.mkdir()
    target2 = sub2 / "target.txt"
    target2.write_text("found 2")
    
    # 1. Search with single root
    res_single = tool.locate_path("target.txt", str(sub1))
    assert str(target1) in res_single
    assert str(target2) not in res_single
    
    # 2. Search with pipe-separated roots
    res_pipe = tool.locate_path("target.txt", f"{str(sub1)}|{str(sub2)}")
    assert str(target1) in res_pipe
    assert str(target2) in res_pipe
    
    # 3. Search with list roots
    res_list = tool.locate_path("target.txt", [str(sub1), str(sub2)])
    assert str(target1) in res_list
    assert str(target2) in res_list
    
    # 4. Search with non-existent root
    res_missing = tool.locate_path("target.txt", str(tmp_path / "missing"))
    assert res_missing == "No matches."
    
    # 5. Default roots if none provided (uses cwd)
    old_cwd = os.getcwd()
    os.chdir(str(sub1))
    try:
        res_default = tool.locate_path("target.txt")
        assert str(target1) in res_default
    finally:
        os.chdir(old_cwd)
