from pathlib import Path

from tools.filesystem.info import InfoMixin
from tools.filesystem.listing import ListingMixin
from tools.filesystem.cwd import CwdMixin

class MockInfoTools(InfoMixin, ListingMixin, CwdMixin):
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._cwd = str(workspace)
        
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

def test_cwd_tools(tmp_path):
    tool = MockInfoTools(tmp_path)
    
    # Check get_cwd
    res = tool.get_cwd()
    assert str(tmp_path) in res
    
    # Check set_cwd
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    res2 = tool.set_cwd("subdir")
    
    assert "cwd:" in res2
    assert tool._cwd == str(sub_dir)

def test_file_info(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello info")
    
    tool = MockInfoTools(tmp_path)
    res = tool.file_info("test.txt")
    
    assert "size:" in res
    assert "10" in res # "hello info" is 10 bytes
    assert "is_dir: False" in res

def test_list_directory(tmp_path):
    d = tmp_path / "mydir"
    d.mkdir()
    (d / "file1.txt").write_text("1")
    (d / "file2.txt").write_text("2")
    
    tool = MockInfoTools(tmp_path)
    res = tool.list_dir("mydir")
    
    assert "file1.txt" in res
    assert "file2.txt" in res
    assert "FILE" in res
