from pathlib import Path
from tools.filesystem.bulk import BulkMixin

class DummyBulkTool(BulkMixin):
    def __init__(self, workspace):
        self.workspace = workspace
        self.rules = {}
    def _resolve(self, path):
        p = Path(self.workspace) / path
        return p.resolve()
    def _is_drive_root(self, path):
        return False
    def _size_human(self, size):
        return f"{size}B"
    def _deny_file_modify(self):
        pass
    def _deny_internal_writes(self, path):
        pass


def test_find_large_files(tmp_path):
    tool = DummyBulkTool(str(tmp_path))

    # Create test files
    small_file = tmp_path / "small.txt"
    small_file.write_text("a" * 10)

    large_file = tmp_path / "large.txt"
    large_file.write_text("a" * 1024 * 1024 * 2) # 2MB

    # find large files min 1MB
    res = tool.find_large_files(".", "1")
    assert str(large_file) in res
    assert str(small_file) not in res

    # Empty dir or no files matching
    res = tool.find_large_files(".", "10")
    assert "No large files found." in res

    # Check drive root bypass config
    tool._is_drive_root = lambda x: True
    tool.rules = {"allow_full_drive_python_scans": False}
    res = tool.find_large_files(".", "1")
    assert "Full-drive Python scans are disabled" in res


def test_replace_in_dir(tmp_path):
    tool = DummyBulkTool(str(tmp_path))

    file1 = tmp_path / "file1.txt"
    file1.write_text("hello world")

    file2 = tmp_path / "file2.log"
    file2.write_text("hello log")

    # Replace in matching files
    res = tool.replace_in_dir(".", "*.txt", "hello", "goodbye")
    assert res == "Updated 1 file(s)."
    assert file1.read_text() == "goodbye world"
    assert file2.read_text() == "hello log"

    # Replace in all files
    res = tool.replace_in_dir(".", "", "goodbye", "hello")
    assert res == "Updated 1 file(s)."

    # No match
    res = tool.replace_in_dir(".", "*.txt", "missing", "found")
    assert res == "Updated 0 file(s)."

    # Handle unreadable files gracefully using mock
    import unittest.mock
    with unittest.mock.patch("pathlib.Path.read_text", side_effect=Exception("mocked unreadable")):
        res = tool.replace_in_dir(".", "*.txt", "hello", "goodbye")
        assert "Updated 0 file(s)." in res
