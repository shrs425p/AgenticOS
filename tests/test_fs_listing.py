from pathlib import Path
from tools.filesystem.listing import ListingMixin

class MockListingTools(ListingMixin):
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)

    def _resolve(self, path: str) -> Path:
        return (self.base_dir / path).resolve()

def test_list_dir(tmp_path):
    tool = MockListingTools(tmp_path)
    
    # 1. Directory not found
    assert tool.list_dir("nonexistent") == "Directory not found."
    
    # 2. Not a directory
    f = tmp_path / "file.txt"
    f.touch()
    assert tool.list_dir("file.txt") == "Not a directory."
    
    # 3. Empty directory
    d = tmp_path / "empty_dir"
    d.mkdir()
    assert tool.list_dir("empty_dir") == "(empty)"
    
    # 4. Non-empty directory (sorted, with files and folders)
    f2 = d / "a_file.txt"
    f2.touch()
    d2 = d / "b_dir"
    d2.mkdir()
    
    res = tool.list_dir("empty_dir")
    assert "DIR  b_dir" in res
    assert "FILE a_file.txt" in res
    # DIR should come before FILE due to key lambda x: (not x.is_dir(), x.name.lower())
    lines = res.split("\n")
    assert "DIR " in lines[0]
    assert "FILE" in lines[1]

def test_list_dir_exception(tmp_path):
    tool = MockListingTools(tmp_path)
    
    # Mock iterdir to raise Exception
    from unittest.mock import patch
    with patch.object(Path, "iterdir", side_effect=OSError("permission denied")):
        assert "Error listing dir" in tool.list_dir(".")

def test_tree(tmp_path):
    tool = MockListingTools(tmp_path)
    
    # 1. Tree on nonexistent path
    assert tool.tree("nonexistent") == "Path not found."
    
    # 2. Tree on file
    f = tmp_path / "file.txt"
    f.touch()
    assert tool.tree("file.txt") == "file.txt"
    
    # 3. Tree on complex structure
    src = tmp_path / "src"
    src.mkdir()
    f_src = src / "main.py"
    f_src.touch()
    
    sub = src / "sub"
    sub.mkdir()
    f_sub = sub / "utils.py"
    f_sub.touch()
    
    res = tool.tree("src")
    assert "src" in res
    assert "main.py" in res
    assert "sub" in res
    assert "utils.py" in res
    
    # 4. Tree with depth limit
    res_depth = tool.tree("src", max_depth="1")
    assert "sub" in res_depth
    assert "utils.py" not in res_depth
    
    # 5. Invalid max_depth handling (should fallback to default depth limit 3)
    res_invalid = tool.tree("src", max_depth="invalid")
    assert "utils.py" in res_invalid
