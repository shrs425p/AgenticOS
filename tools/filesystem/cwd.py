"""Module for cwd.py"""
from __future__ import annotations

import os


from core.tool_base import tool
class CwdMixin:
    @tool(name="get_cwd", desc="Get current working directory.", category="Files")
    def get_cwd(self) -> str:
        """get_cwd function."""
        try:
            if hasattr(self, "_cwd"):
                return self._cwd
            return os.getcwd()
        except Exception as e:
            return f"Error: {e}"

    @tool(name="set_cwd", desc="Change current working directory. Args: path", category="Files")
    def set_cwd(self, path: str) -> str:
        """set_cwd function."""
        try:
            p = self._resolve(path)
            if hasattr(self, "_cwd"):
                self._cwd = str(p)
            else:
                os.chdir(p)
            return f"cwd: {self.get_cwd()}"
        except Exception as e:
            return f"Error: {e}"
