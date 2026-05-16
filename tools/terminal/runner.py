"""Module for runner.py"""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional


from core.tool_base import tool
class RunnerMixin:
    def _shell_args(self, command: str) -> dict:
        if self.system == "Windows":
            return {"shell": True}
        return {"shell": True, "executable": "/bin/bash"}

    def _quote_arg(self, value: str) -> str:
        if self.system == "Windows":
            return subprocess.list2cmdline([value])
        return shlex.quote(value)

    def _run(
        self,
        command: str,
        timeout: int = 60,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None,
        env_extra: Optional[dict] = None,
    ) -> str:
        env = {**os.environ, **self._env_overrides}
        if env_extra:
            env.update(env_extra)

        blocked_reason = self._blocked_command_reason(command)
        if blocked_reason:
            return f"Error: {blocked_reason}"

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                input=input_data,
                env=env,
                **self._shell_args(command),
            )  # nosec B602 B603

            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            code = result.returncode

            parts = []
            if out:
                parts.append(out)
            if err:
                parts.append(f"[stderr]\n{err}")
            if not parts:
                parts.append(f"(exit code: {code})")
            else:
                parts.append(f"\n[exit: {code}]")
            return "\n".join(parts)
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout}s"
        except FileNotFoundError as e:
            return f"Error: Command not found: {e}"
        except Exception as e:
            return f"Error running command: {type(e).__name__}: {e}"

    @tool(name="run_command", desc="Run shell command. Args: command", category="Terminal")
    def run_command(self, command: str, timeout: int = 30) -> str:
        return self._run(command, timeout=timeout)

    @tool(name="run_powershell", desc="Run PowerShell command. Args: command", category="Terminal")
    def run_powershell(self, command: str, timeout: int = 60) -> str:
        if self.system != "Windows":
            return self._run(command, timeout=timeout)
        return self._run(
            f"powershell -NoProfile -Command {self._quote_arg(command)}",
            timeout=timeout,
        )

    # Map of common non-ASCII typographic characters the model may inject into code
    _CODE_CHAR_MAP = {
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2026": "...", # ellipsis
        "\u2022": "-",   # bullet point
        "\u00a0": " ",   # non-breaking space
        "\u2012": "-",   # figure dash
        "\u2015": "-",   # horizontal bar
        "\u2212": "-",   # minus sign
    }

    def _sanitize_code(self, code: str) -> str:
        """Replace typographic Unicode characters with ASCII equivalents
        to prevent SyntaxError when the model injects fancy punctuation."""
        for char, replacement in self._CODE_CHAR_MAP.items():
            code = code.replace(char, replacement)
        return code

    @tool(name="run_python", desc="Run Python code string. Args: code", category="Terminal")
    def run_python(self, code: str) -> str:
        return self._run("python -", timeout=60, input_data=self._sanitize_code(code))

    @tool(name="run_script", desc="Run a script file. Args: path, interpreter (optional)", category="Terminal")
    def run_script(self, path: str, interpreter: str = "") -> str:
        p = Path(path).resolve()
        if not p.exists():
            return f"Error: Script not found: {path}"

        interp = (interpreter or "").strip()
        if not interp:
            suffix = p.suffix.lower()
            interp_map = {
                ".py": "python",
                ".sh": "bash",
                ".bash": "bash",
                ".zsh": "zsh",
                ".ps1": "powershell -NoProfile -ExecutionPolicy Bypass -File",
                ".cmd": "cmd /c",
                ".bat": "cmd /c",
            }
            interp = interp_map.get(suffix, "")
        cmd = f"{interp} {self._quote_arg(str(p))}".strip() if interp else str(p)
        return self._run(cmd, timeout=300)
