from pathlib import Path

from ops.files.stat import InfoMixin
from ops.files.place import CwdMixin

class MockInfoTools(InfoMixin, CwdMixin):
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

def test_cwd_ops(tmp_path):
    tool = MockInfoTools(tmp_path)
    
    # Check getcwd
    res = tool.getcwd()
    assert str(tmp_path) in res
    
    # Check setcwd
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    res2 = tool.setcwd("subdir")
    
    assert "cwd:" in res2
    assert tool._cwd == str(sub_dir)

def test_cwd_real_and_exceptions(tmp_path):
    real_tool = MockCwdToolsReal()
    
    # Test real getcwd and setcwd using mocked os functions
    from unittest.mock import patch
    with patch("os.getcwd", return_value="/mocked/cwd"), \
         patch("os.chdir") as mock_chdir:
             assert real_tool.getcwd() == "/mocked/cwd"
             
             # Call setcwd without _cwd attribute
             res = real_tool.setcwd("/new/dir")
             assert "cwd:" in res
             mock_chdir.assert_called_with(Path("/new/dir").resolve())
             
    # Test exceptions in getcwd and setcwd
    with patch("os.getcwd", side_effect=OSError("getcwd failed")):
        assert "Error: getcwd failed" in real_tool.getcwd()
        
    with patch("os.chdir", side_effect=OSError("chdir failed")):
        assert "Error: chdir failed" in real_tool.setcwd("/some/dir")


def test_fileinfo(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello info")
    
    tool = MockInfoTools(tmp_path)
    res = tool.fileinfo("test.txt")
    
    assert "size:" in res
    assert "10" in res # "hello info" is 10 bytes
    assert "is_dir: False" in res



def test_fileexists(tmp_path):
    tool = MockInfoTools(tmp_path)
    assert tool.fileexists("test.txt") == "False"
    
    f = tmp_path / "test.txt"
    f.write_text("exists")
    assert tool.fileexists("test.txt") == "True"
    
    # Path traversal / invalid path returns False
    assert tool.fileexists("../outside") == "false"

def test_filehash(tmp_path):
    tool = MockInfoTools(tmp_path)
    f = tmp_path / "test.txt"
    f.write_text("hashme")
    
    h256 = tool.filehash("test.txt")
    assert len(h256) == 64  # sha256 hex length
    
    h_md5 = tool.filehash("test.txt", "md5")
    assert len(h_md5) == 32  # md5 hex length
    
    # Error case (file doesn't exist)
    assert "Error:" in tool.filehash("nonexistent.txt")

def test_fileinfo_error(tmp_path):
    tool = MockInfoTools(tmp_path)
    assert tool.fileinfo("nonexistent.txt") == "Path not found."
    
    # Exception handling inside fileinfo
    # We pass a path that exists but cause stat() to throw an exception
    f = tmp_path / "error_file.txt"
    f.write_text("trigger error")
    
    # Mock stat of Path to raise an OSError
    from unittest.mock import patch
    with patch.object(Path, "stat", side_effect=OSError("disk failure")):
        assert "Error: disk failure" in tool.fileinfo("error_file.txt")


