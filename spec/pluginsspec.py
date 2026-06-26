import os
import tempfile
import time
from unittest import mock

from ops.addons.disk import fastdiskaudit

def test_fastdiskaudit_functional():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a "Users" subdirectory to test default behaviour
        users_dir = os.path.join(tmpdir, "Users")
        os.makedirs(users_dir, exist_ok=True)
        
        # 1. Create a large file (sparse file, 105 MB)
        large_file = os.path.join(users_dir, "large_file.cli")
        with open(large_file, "wb") as f:
            f.seek(105 * 1024 * 1024 - 1)
            f.write(b"\0")
            
        # 2. Create duplicate files
        subdir1 = os.path.join(users_dir, "dir1")
        subdir2 = os.path.join(users_dir, "dir2")
        os.makedirs(subdir1, exist_ok=True)
        os.makedirs(subdir2, exist_ok=True)
        
        dup1 = os.path.join(subdir1, "duplicate.txt")
        dup2 = os.path.join(subdir2, "duplicate.txt")
        with open(dup1, "w") as f:
            f.write("hello")
        with open(dup2, "w") as f:
            f.write("hello")
            
        # 3. Create an old file (accessed 200 days ago)
        old_file = os.path.join(users_dir, "old_file.txt")
        with open(old_file, "w") as f:
            f.write("old content")
        cutoff_time = time.time() - (200 * 24 * 60 * 60)
        os.utime(old_file, (cutoff_time, cutoff_time))
        
        # Test large mode
        res_large = fastdiskaudit(path=tmpdir, top_n=5, min_mb=100, mode="large")
        assert "TOP 5 LARGEST FILES" in res_large
        assert "large_file.cli" in res_large
        
        # Test duplicates mode
        res_dupes = fastdiskaudit(path=tmpdir, mode="duplicates")
        assert "DUPLICATE FILENAMES" in res_dupes
        assert "duplicate.txt" in res_dupes
        assert "2" in res_dupes
        
        # Test old mode
        res_old = fastdiskaudit(path=tmpdir, mode="old")
        assert "FILES NOT ACCESSED IN 180+" in res_old
        assert "old_file.txt" in res_old
        
        # Test default path (None) defaulting to root by mocking os.path.abspath
        with mock.patch("os.path.abspath", return_value=tmpdir):
            res_all = fastdiskaudit(path=None, mode="all")
            assert "TOP 20 LARGEST FILES" in res_all
            assert "DUPLICATE FILENAMES" in res_all
            assert "FILES NOT ACCESSED IN 180+" in res_all
            assert "large_file.cli" in res_all
            assert "duplicate.txt" in res_all
            assert "old_file.txt" in res_all
