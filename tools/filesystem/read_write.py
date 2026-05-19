"""Module for read_write.py"""
from __future__ import annotations


from core.tool_base import tool
class ReadWriteMixin:
    @tool(name="read_file", desc="Read file. Args: path, start_line (optional), num_lines (optional)", category="Files")
    def read_file(self, path: str, start_line: int = 0, num_lines: int = 0) -> str:
        """read_file function."""
        p = self._resolve(path)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                if start_line == 0 and num_lines == 0:
                    return f.read()
                lines = f.readlines()
                if num_lines == 0:
                    return "".join(lines[start_line:])
                return "".join(lines[start_line : start_line + num_lines])
        except Exception as e:
            return f"Error reading file: {e}"

    @tool(name="write_file", desc="Write/overwrite a file. Args: path, content", category="Files")
    def write_file(self, path: str, content: str) -> str:
        """write_file function."""
        import os

        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            dirname = os.path.dirname(p)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    @tool(name="append_file", desc="Append to a file. Args: path, content", category="Files")
    def append_file(self, path: str, content: str, encoding: str = "utf-8") -> str:
        """append_file function."""
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding=encoding) as f:
                f.write(content)
            return f"Appended {len(content)} chars to {path}"
        except Exception as e:
            return f"Error appending: {e}"

    def read_head(self, path: str, n: str = "10") -> str:
        """read_head function."""
        try:
            count = max(0, int(n))
            return self.read_file(path, 0, count)
        except Exception as e:
            return f"Error: {e}"

    def read_tail(self, path: str, n: str = "10") -> str:
        """read_tail function."""
        p = self._resolve(path)
        try:
            count = max(0, int(n))
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return "".join(lines[-count:])
        except Exception as e:
            return f"Error: {e}"
