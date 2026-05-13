from __future__ import annotations

import os


class CwdMixin:
    def get_cwd(self) -> str:
        try:
            return os.getcwd()
        except Exception as e:
            return f"Error: {e}"

    def set_cwd(self, path: str) -> str:
        try:
            os.chdir(self._resolve(path))
            return f"cwd: {os.getcwd()}"
        except Exception as e:
            return f"Error: {e}"
