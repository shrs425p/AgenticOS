import pytest
import os
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
