"""Module for mutations.py"""
from __future__ import annotations


from core.tool_base import tool
class MutationsMixin:
    @tool(name="delete_file", desc="Delete a file. Args: path", category="Files")
    def delete_file(self, path: str) -> str:
        import os

        p = self._resolve(path)
        self._deny_file_delete()
        self._deny_internal_writes(p)
        try:
            if not p.exists():
                return "File not found."
            os.remove(p)
            return f"Deleted file: {path}"
        except Exception as e:
            return f"Error deleting file: {e}"

    @tool(name="delete_dir", desc="Delete directory recursively. Args: path", category="Files")
    def delete_dir(self, path: str) -> str:
        import shutil

        p = self._resolve(path)
        self._deny_file_delete()
        self._deny_internal_writes(p)
        try:
            if not p.exists():
                return "Directory not found."
            shutil.rmtree(p)
            return f"Deleted directory: {path}"
        except Exception as e:
            return f"Error deleting directory: {e}"

    @tool(name="copy_file", desc="Copy file. Args: src, dst", category="Files")
    def copy_file(self, src: str, dst: str) -> str:
        import shutil

        s = self._resolve(src)
        d = self._resolve(dst)
        self._deny_file_modify()
        self._deny_internal_writes(d)
        try:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            return f"Copied {src} -> {dst}"
        except Exception as e:
            return f"Error copying file: {e}"

    @tool(name="move_file", desc="Move/rename file. Args: src, dst", category="Files")
    def move_file(self, src: str, dst: str) -> str:
        import shutil

        s = self._resolve(src)
        d = self._resolve(dst)
        self._deny_file_modify()
        self._deny_internal_writes(d)
        try:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(s), str(d))
            return f"Moved {src} -> {dst}"
        except Exception as e:
            return f"Error moving file: {e}"

    @tool(name="create_dir", desc="Create directory. Args: path", category="Files")
    def create_dir(self, path: str) -> str:
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return f"Created directory: {path}"
        except Exception as e:
            return f"Error creating directory: {e}"

    @tool(name="touch", desc="Create empty file or update timestamps. Args: path", category="Files")
    def touch(self, path: str) -> str:
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
            os_utime = getattr(__import__("os"), "utime")
            os_utime(p, None)
            return f"Touched: {path}"
        except Exception as e:
            return f"Error touching: {e}"
