"""Module for cwd.py"""
from __future__ import annotations

import os


from kernel.base import tool
class CwdMixin:
    @tool(name="getcwd", desc="Get current working directory.", category="Files")
    def getcwd(self) -> str:
        """getcwd function."""
        try:
            if hasattr(self, "_cwd"):
                return self._cwd
            return os.getcwd()
        except Exception as e:
            return f"Error: {e}"

    @tool(name="setcwd", desc="Change current working directory. Args: path", category="Files")
    def setcwd(self, path: str) -> str:
        """setcwd function."""
        try:
            p = self._resolve(path)
            if hasattr(self, "_cwd"):
                self._cwd = str(p)
            else:
                os.chdir(p)
            return f"cwd: {self.getcwd()}"
        except Exception as e:
            return f"Error: {e}"
