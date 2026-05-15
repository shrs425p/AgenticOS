import pytest
import os
from pathlib import Path

from tools.filesystem.mutations import MutationsMixin
from tools.filesystem.bulk import BulkMixin

class MockMutationsTools(MutationsMixin, BulkMixin):
    def __init__(self, workspace: Path):
        self.workspace = workspace
        
    def _resolve(self, path: str) -> Path:
        p = (self.workspace / path).resolve()
        if not str(p).startswith(str(self.workspace)):
            raise ValueError("Path traversal denied")
        return p
        
    def _deny_file_modify(self):
        pass
        
    def _deny_file_delete(self):
        pass
        
    def _deny_internal_writes(self, p):
        pass

def test_delete_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello")
    
    tool = MockMutationsTools(tmp_path)
    res = tool.delete_file("test.txt")
    
    assert not f.exists()
    assert "Deleted file" in res

def test_delete_dir(tmp_path):
    d = tmp_path / "my_dir"
    d.mkdir()
    f = d / "test.txt"
    f.write_text("hello")
    
    tool = MockMutationsTools(tmp_path)
    res = tool.delete_dir("my_dir")
    
    assert not d.exists()
    assert "Deleted directory" in res

def test_copy_file(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("copy me")
    
    tool = MockMutationsTools(tmp_path)
    res = tool.copy_file("src.txt", "dst.txt")
    
    assert (tmp_path / "dst.txt").exists()
    assert (tmp_path / "dst.txt").read_text() == "copy me"
    assert "Copied" in res

def test_move_file(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("move me")
    
    tool = MockMutationsTools(tmp_path)
    res = tool.move_file("src.txt", "dst.txt")
    
    assert not src.exists()
    assert (tmp_path / "dst.txt").exists()
    assert (tmp_path / "dst.txt").read_text() == "move me"
    assert "Moved" in res

def test_create_dir(tmp_path):
    tool = MockMutationsTools(tmp_path)
    res = tool.create_dir("new_dir")
    
    assert (tmp_path / "new_dir").exists()
    assert (tmp_path / "new_dir").is_dir()
    assert "Created directory" in res

def test_touch(tmp_path):
    tool = MockMutationsTools(tmp_path)
    res = tool.touch("touched.txt")
    
    assert (tmp_path / "touched.txt").exists()
    assert "Touched" in res
