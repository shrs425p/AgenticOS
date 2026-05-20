"""Module for info.py"""
from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime


from core.tool_base import tool, _size_human
class InfoMixin:
    @tool(name="file_info", desc="Get metadata of file. Args: path", category="Files")
    def file_info(self, path: str) -> str:
        """file_info function."""
        p = self._resolve(path)
        try:
            if not p.exists():
                return "Path not found."
            stat = p.stat()
            mime, _ = mimetypes.guess_type(str(p))
            info = {
                "path": str(p),
                "is_dir": p.is_dir(),
                "size": stat.st_size,
                "size_human": _size_human(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(
                    sep=" ", timespec="seconds"
                ),
                "mime": mime or "",
            }
            return "\n".join(f"{k}: {v}" for k, v in info.items())
        except Exception as e:
            return f"Error: {e}"

    @tool(name="file_exists", desc="Check if path exists. Args: path", category="Files")
    def file_exists(self, path: str) -> str:
        """file_exists function."""
        try:
            return str(self._resolve(path).exists())
        except Exception:
            return "false"

    @tool(name="file_hash", desc="Compute file hash. Args: path, algorithm (optional)", category="Files")
    def file_hash(self, path: str, algorithm: str = "sha256") -> str:
        """file_hash function."""
        p = self._resolve(path)
        try:
            h = hashlib.new((algorithm or "sha256").lower())
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            return f"Error: {e}"
