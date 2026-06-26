from pathlib import Path
from ops.files.pack import ArchiveMixin

class MockArchiveTools(ArchiveMixin):
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.rules = {}

    def _resolve(self, path: str) -> Path:
        return (self.base_dir / path).resolve()

    def _deny_file_modify(self):
        pass

    def _deny_internal_writes(self, p):
        pass

def test_zip_and_unzip(tmp_path):
    tool = MockArchiveTools(tmp_path)
    
    # Create files to zip
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    f1 = src_dir / "f1.txt"
    f1.write_text("hello archive")
    
    sub_dir = src_dir / "subdir"
    sub_dir.mkdir()
    f2 = sub_dir / "f2.txt"
    f2.write_text("hello subdir")
    
    zip_out = tmp_path / "out.zip"
    
    # 1. Test zipfiles
    res = tool.zipfiles(str(zip_out), str(f1), str(sub_dir), "nonexistent.txt")
    assert "Created zip:" in res
    assert zip_out.exists()
    
    # 2. Test unzipfile
    dest_dir = tmp_path / "dest"
    res2 = tool.unzipfile(str(zip_out), str(dest_dir))
    assert "Extracted to:" in res2
    
    # Verify extracted contents
    # Since we zipped with arcname relative to base_dir (tmp_path), we expect the relative structure
    extracted_f1 = dest_dir / f1.relative_to(tmp_path)
    extracted_f2 = dest_dir / f2.relative_to(tmp_path)
    
    assert extracted_f1.exists()
    assert extracted_f1.read_text() == "hello archive"
    assert extracted_f2.exists()
    assert extracted_f2.read_text() == "hello subdir"

def test_archive_exceptions(tmp_path):
    tool = MockArchiveTools(tmp_path)
    
    # Test zip exception (e.g. invalid zip path or permission issue)
    # We can trigger it by attempting to zip to a directory path
    res = tool.zipfiles(str(tmp_path), "nonexistent.txt")
    assert "Zip error" in res
    
    # Test unzip exception
    res2 = tool.unzipfile("nonexistent.zip", str(tmp_path / "dest"))
    assert "Unzip error" in res2
