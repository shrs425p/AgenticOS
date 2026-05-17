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

class MockCwdToolsReal(CwdMixin):
    def _resolve(self, path: str) -> Path:
        return Path(path).resolve()

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

def test_cwd_real_and_exceptions(tmp_path):
    real_tool = MockCwdToolsReal()
    
    # Test real get_cwd and set_cwd using mocked os functions
    from unittest.mock import patch
    with patch("os.getcwd", return_value="/mocked/cwd"), \
         patch("os.chdir") as mock_chdir:
             assert real_tool.get_cwd() == "/mocked/cwd"
             
             # Call set_cwd without _cwd attribute
             res = real_tool.set_cwd("/new/dir")
             assert "cwd:" in res
             mock_chdir.assert_called_with(Path("/new/dir").resolve())
             
    # Test exceptions in get_cwd and set_cwd
    with patch("os.getcwd", side_effect=OSError("getcwd failed")):
        assert "Error: getcwd failed" in real_tool.get_cwd()
        
    with patch("os.chdir", side_effect=OSError("chdir failed")):
        assert "Error: chdir failed" in real_tool.set_cwd("/some/dir")


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

def test_file_exists(tmp_path):
    tool = MockInfoTools(tmp_path)
    assert tool.file_exists("test.txt") == "False"
    
    f = tmp_path / "test.txt"
    f.write_text("exists")
    assert tool.file_exists("test.txt") == "True"
    
    # Path traversal / invalid path returns False
    assert tool.file_exists("../outside") == "false"

def test_file_hash(tmp_path):
    tool = MockInfoTools(tmp_path)
    f = tmp_path / "test.txt"
    f.write_text("hashme")
    
    h256 = tool.file_hash("test.txt")
    assert len(h256) == 64  # sha256 hex length
    
    h_md5 = tool.file_hash("test.txt", "md5")
    assert len(h_md5) == 32  # md5 hex length
    
    # Error case (file doesn't exist)
    assert "Error:" in tool.file_hash("nonexistent.txt")

def test_file_info_error(tmp_path):
    tool = MockInfoTools(tmp_path)
    assert tool.file_info("nonexistent.txt") == "Path not found."
    
    # Exception handling inside file_info
    # We pass a path that exists but cause stat() to throw an exception
    f = tmp_path / "error_file.txt"
    f.write_text("trigger error")
    
    # Mock stat of Path to raise an OSError
    from unittest.mock import patch
    with patch.object(Path, "stat", side_effect=OSError("disk failure")):
        assert "Error: disk failure" in tool.file_info("error_file.txt")


