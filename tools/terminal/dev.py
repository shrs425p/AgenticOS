"""Module for dev.py"""
from __future__ import annotations


from core.tool_base import tool
class DevToolsMixin:
    @tool(name="pip_install", desc="Install Python package. Args: package", category="Terminal")
    def pip_install(self, package: str) -> str:
        return self._run(f"pip install {package}", timeout=600)

    @tool(name="pip_list", desc="List installed packages.", category="Terminal")
    def pip_list(self) -> str:
        return self._run("pip list", timeout=120)

    @tool(name="npm_install", desc="Install npm package. Args: package, global_flag (optional)", category="Terminal")
    def npm_install(self, package: str, global_flag: str = "false") -> str:
        g = str(global_flag).lower() == "true"
        cmd = f"npm install {'-g ' if g else ''}{package}".strip()
        return self._run(cmd, timeout=600)

    @tool(name="git", desc="Run git command. Args: *args", category="Terminal")
    def git(self, *args) -> str:
        joined = " ".join(str(a) for a in args if a is not None)
        return self._run(f"git {joined}".strip(), timeout=120)

    @tool(name="git_status", desc="Git status. Args: path (optional)", category="Terminal")
    def git_status(self, path: str = ".") -> str:
        return self._run(f"git -C {self._quote_arg(path)} status", timeout=60)

    @tool(name="git_log", desc="Git log. Args: path, n (optional)", category="Terminal")
    def git_log(self, path: str = ".", n: str = "10") -> str:
        try:
            num = int(n)
        except Exception:
            num = 10
        return self._run(
            f"git -C {self._quote_arg(path)} log -n {num} --oneline", timeout=60
        )
