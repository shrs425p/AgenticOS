from pathlib import Path

from tools.filesystem.search import SearchMixin

class MockSearchTools(SearchMixin):
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._cwd = str(workspace)
        self.rules = {}
        
    def _is_drive_root(self, path):
        return False
        
    def _resolve(self, path: str) -> Path:
        if not path or path == ".":
            return Path(self._cwd)
        p = (Path(self._cwd) / path).resolve()
        if not str(p).startswith(str(self.workspace)):
            raise ValueError("Path traversal denied")
        return p
        
    def _deny_system_read(self, p):
        pass
        
    def _deny_internal_writes(self, p):
        pass

def test_search_dir(tmp_path):
    d = tmp_path / "search_target"
    d.mkdir()
    (d / "file1.txt").write_text("this has the magical word")
    (d / "file2.txt").write_text("this has nothing")
    
    tool = MockSearchTools(tmp_path)
    tool.rules = {"allow_full_drive_grep": True}
    res = tool.grep_dir("search_target", "magical")
    
    assert "file1.txt" in res
    assert "file2.txt" not in res

def test_search_files(tmp_path):
    d = tmp_path / "my_search"
    d.mkdir()
    (d / "test_a.txt").write_text("")
    (d / "test_b.log").write_text("")
    
    tool = MockSearchTools(tmp_path)
    
    # Successful match
    res = tool.search_files("my_search", "*.txt")
    assert "test_a.txt" in res
    assert "test_b.log" not in res
    
    # No matches
    assert tool.search_files("my_search", "*.pdf") == "No matches."
    
    # Path not found
    assert tool.search_files("nonexistent", "*") == "Path not found."

def test_grep_file_options_and_errors(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Line One\nline two\n")
    
    tool = MockSearchTools(tmp_path)
    
    # Case sensitive (default) matches "Line" but not "line"
    res1 = tool.grep_file("test.txt", "Line")
    assert "1: Line One" in res1
    assert "2: line two" not in res1
    
    # Case insensitive
    res2 = tool.grep_file("test.txt", "line", case_sensitive="false")
    assert "1: Line One" in res2
    assert "2: line two" in res2
    
    # No match
    assert tool.grep_file("test.txt", "three") == "No matches."
    
    # Error case
    assert "Error:" in tool.grep_file("nonexistent.txt", "query")

def test_grep_dir_rules_and_errors(tmp_path):
    tool = MockSearchTools(tmp_path)
    
    # Mock drive root and check recursive check
    tool._is_drive_root = lambda path: True
    tool.rules = {"allow_full_drive_grep": False}
    
    res = tool.grep_dir(".", "query")
    assert "disabled by config" in res
    
    # Exception handling
    # We trigger an exception by having rglob raise an OSError
    tool.rules = {"allow_full_drive_grep": True}
    from unittest.mock import patch
    with patch.object(Path, "rglob", side_effect=OSError("permission denied")):
        assert "Error: permission denied" in tool.grep_dir(".", "query")



