import pytest
from pathlib import Path

from tools.filesystem.read_write import ReadWriteMixin
from tools.filesystem.edit import EditMixin

class MockFileSystemTools(ReadWriteMixin, EditMixin):
    def __init__(self, workspace: Path):
        self.workspace = workspace
        
    def _resolve(self, path: str) -> Path:
        # Simple resolution for testing
        p = (self.workspace / path).resolve()
        if not str(p).startswith(str(self.workspace)):
            raise ValueError("Path traversal denied")
        return p
        
    def _deny_file_modify(self):
        pass
        
    def _deny_internal_writes(self, p):
        pass

def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line 1\nline 2\nline 3\n")
    
    tool = MockFileSystemTools(tmp_path)
    res = tool.read_file("test.txt")
    assert "line 1" in res
    assert "line 3" in res

def test_write_file(tmp_path):
    tool = MockFileSystemTools(tmp_path)
    res = tool.write_file("new_file.txt", "hello world")
    
    assert "Wrote" in res or "Created" in res or "Saved" in res or res.startswith("Wrote") or "new_file.txt" in res
    assert (tmp_path / "new_file.txt").read_text() == "hello world"

def test_append_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello\n")
    
    tool = MockFileSystemTools(tmp_path)
    res = tool.append_file("test.txt", "world")
    
    assert "world" in (tmp_path / "test.txt").read_text()

def test_edit_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello old_text world")
    
    tool = MockFileSystemTools(tmp_path)
    res = tool.edit_file("test.txt", "old_text", "new_text")
    
    assert "new_text" in (tmp_path / "test.txt").read_text()
    assert "old_text" not in (tmp_path / "test.txt").read_text()

def test_edit_line(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line 1\nline 2\nline 3\n")
    
    tool = MockFileSystemTools(tmp_path)
    res = tool.edit_line("test.txt", "2", "new line 2")
    
    lines = (tmp_path / "test.txt").read_text().splitlines()
    assert lines[1] == "new line 2"

def test_insert_line(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line 1\nline 2\n")
    
    tool = MockFileSystemTools(tmp_path)
    res = tool.insert_line("test.txt", "2", "inserted line")
    
    lines = (tmp_path / "test.txt").read_text().splitlines()
    assert lines[1] == "inserted line"
    assert len(lines) == 3
