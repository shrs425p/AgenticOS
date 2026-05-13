from __future__ import annotations


class DevToolsMixin:
    def pip_install(self, package: str) -> str:
        return self._run(f"pip install {package}", timeout=600)

    def pip_list(self) -> str:
        return self._run("pip list", timeout=120)

    def npm_install(self, package: str, global_flag: str = "false") -> str:
        g = str(global_flag).lower() == "true"
        cmd = f"npm install {'-g ' if g else ''}{package}".strip()
        return self._run(cmd, timeout=600)

    def git(self, *args) -> str:
        joined = " ".join(str(a) for a in args if a is not None)
        return self._run(f"git {joined}".strip(), timeout=120)

    def git_status(self, path: str = ".") -> str:
        return self._run(f"git -C {self._quote_arg(path)} status", timeout=60)

    def git_log(self, path: str = ".", n: str = "10") -> str:
        try:
            num = int(n)
        except Exception:
            num = 10
        return self._run(
            f"git -C {self._quote_arg(path)} log -n {num} --oneline", timeout=60
        )
