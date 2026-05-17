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
    tool.append_file("test.txt", "world")
    
    assert "world" in (tmp_path / "test.txt").read_text()

def test_edit_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello old_text world")
    
    tool = MockFileSystemTools(tmp_path)
    tool.edit_file("test.txt", "old_text", "new_text")
    
    assert "new_text" in (tmp_path / "test.txt").read_text()
    assert "old_text" not in (tmp_path / "test.txt").read_text()

def test_edit_line(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line 1\nline 2\nline 3\n")
    
    tool = MockFileSystemTools(tmp_path)
    tool.edit_line("test.txt", "2", "new line 2")
    
    lines = (tmp_path / "test.txt").read_text().splitlines()
    assert lines[1] == "new line 2"

def test_insert_line(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line 1\nline 2\n")
    
    tool = MockFileSystemTools(tmp_path)
    tool.insert_line("test.txt", "2", "inserted line")
    
    lines = (tmp_path / "test.txt").read_text().splitlines()
    assert lines[1] == "inserted line"
    assert len(lines) == 3

def test_read_file_paging(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("1\n2\n3\n4\n5\n")
    
    tool = MockFileSystemTools(tmp_path)
    
    # start_line non-zero, num_lines zero
    res1 = tool.read_file("test.txt", start_line=2)
    assert res1 == "3\n4\n5\n"
    
    # start_line non-zero, num_lines non-zero
    res2 = tool.read_file("test.txt", start_line=1, num_lines=2)
    assert res2 == "2\n3\n"

def test_read_head_and_tail(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n")
    
    tool = MockFileSystemTools(tmp_path)
    
    # Default head
    res_head = tool.read_head("test.txt")
    assert res_head == "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n"
    
    # Custom head count
    res_head_custom = tool.read_head("test.txt", "3")
    assert res_head_custom == "1\n2\n3\n"
    
    # Default tail
    res_tail = tool.read_tail("test.txt")
    assert res_tail == "2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n"
    
    # Custom tail count
    res_tail_custom = tool.read_tail("test.txt", "2")
    assert res_tail_custom == "10\n11\n"

def test_read_write_errors(tmp_path):
    tool = MockFileSystemTools(tmp_path)
    
    # 1. Read file error (nonexistent file)
    assert "Error reading file:" in tool.read_file("nonexistent.txt")
    
    # 2. Write file error (invalid path / directory permissions)
    # We pass an empty path or directory path to write
    assert "Error writing file:" in tool.write_file("", "content")
    
    # 3. Append file error
    assert "Error appending:" in tool.append_file("", "content")
    
    # 4. Read head error (invalid count format)
    assert "Error:" in tool.read_head("nonexistent.txt", "invalid")
    
    # 5. Read tail error (nonexistent file)
    assert "Error:" in tool.read_tail("nonexistent.txt")

