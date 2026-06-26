"""Module for runner.py"""

from __future__ import annotations

import os
import shlex
import subprocess


from pathlib import Path
from typing import Optional


from kernel.base import tool


class RunnerMixin:
    def _shell_args(self, command: str) -> dict:
        if self.system == "Windows":
            return {"shell": True}
        return {"shell": True, "executable": "/cli/bash"}

    def _quote_arg(self, value: str) -> str:
        if self.system == "Windows":
            return subprocess.list2cmdline([value])
        return shlex.quote(value)

    def _attempt_self_healing(
        self,
        command: str,
        timeout: int,
        cwd: Optional[str],
        input_data: Optional[str],
        env_extra: Optional[dict],
    ) -> Optional[str]:
        """Attempt to self-provision a missing command and rerun.

        Args:
            command: The command line string.
            timeout: Timeout in seconds.
            cwd: Working directory.
            input_data: Stdin input.
            env_extra: Extra environment variables.

        Returns:
            The output of the rerun command if self-healing succeeded,
            otherwise None.
        """
        cmd_name = ""
        try:
            parts = shlex.split(command)
            if parts:
                cmd_name = parts[0]
        except Exception:
            cmd_name = command.split()[0] if command.split() else ""
        cmd_name = os.path.basename(cmd_name).replace('"', "").replace("'", "")

        if cmd_name:
            try:
                from kernel.provision import self_provision_command

                if self_provision_command(cmd_name):
                    return self._run(
                        command,
                        timeout=timeout,
                        cwd=cwd,
                        input_data=input_data,
                        env_extra=env_extra,
                        _is_retry=True,
                    )
            except Exception:
                pass
        return None

    def _run(
        self,
        command: str,
        timeout: int = 60,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None,
        env_extra: Optional[dict] = None,
        _is_retry: bool = False,
    ) -> str:
        env = {**os.environ, **self._env_overrides}
        if env_extra:
            env.update(env_extra)

        # Force UTF-8 I/O for Python and subprocesses
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("PYTHONUTF8", "1")

        blocked_reason = self._blocked_command_reason(command)
        if blocked_reason:
            if not blocked_reason.startswith("Command blocked by safety rules:"):
                blocked_reason = f"Command blocked by safety rules: {blocked_reason}"
            return f"Error: {blocked_reason}"

        # Dynamic PATH refreshing prior to execution
        try:
            from kernel.provision import refresh_path

            refresh_path()
        except ImportError:
            pass

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=cwd,
                input=input_data,
                env=env,
                **self._shell_args(command),
            )

            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            code = result.returncode

            # Self-healing on command-not-found exit codes
            if code in (9009, 127) and not _is_retry:
                healed = self._attempt_self_healing(
                    command,
                    timeout=timeout,
                    cwd=cwd,
                    input_data=input_data,
                    env_extra=env_extra,
                )
                if healed is not None:
                    return healed

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
            if not _is_retry:
                healed = self._attempt_self_healing(
                    command,
                    timeout=timeout,
                    cwd=cwd,
                    input_data=input_data,
                    env_extra=env_extra,
                )
                if healed is not None:
                    return healed
            return f"Error: Command not found: {e}"
        except Exception as e:
            return f"Error running command: {type(e).__name__}: {e}"

    @tool(
        name="runcommand", desc="Run shell command. Args: command", category="Terminal"
    )
    def runcommand(self, command: str, timeout: int = 30) -> str:
        """Run a shell command on the host system.

        Args:
            command: The command line string to execute.
            timeout: Timeout in seconds for command execution. Defaults to 30.

        Returns:
            The comclied stdout and stderr of the command, or an error message.
        """
        return self._run(command, timeout=timeout)

    @tool(
        name="runpowershell",
        desc="Run PowerShell command. Args: command",
        category="Terminal",
    )
    def runpowershell(self, command: str, timeout: int = 60) -> str:
        """Run a command inside a PowerShell process.

        On non-Windows systems, this falls back to standard execution.

        Args:
            command: The command line string to execute.
            timeout: Timeout in seconds for command execution. Defaults to 60.

        Returns:
            The comclied stdout and stderr of the command, or an error message.
        """
        if self.system != "Windows":
            return self._run(command, timeout=timeout)
        return self._run(
            f"powershell -NoProfile -Command {self._quote_arg(command)}",
            timeout=timeout,
        )

    # Map of common non-ASCII typographic characters the model may inject into code
    _CODE_CHAR_MAP = {
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "-",  # bullet point
        "\u00a0": " ",  # non-breaking space
        "\u2012": "-",  # figure dash
        "\u2015": "-",  # horizontal bar
        "\u2212": "-",  # minus sign
    }

    # Line continuation characters by shell script suffix.
    # Used to reconstruct multi-line commands before safety validation.
    _CONTINUATION_CHARS = {
        ".sh": "\\",
        ".bash": "\\",
        ".zsh": "\\",
        ".ps1": "`",
        ".cmd": "^",
        ".bat": "^",
    }

    def _sanitize_code(self, code: str) -> str:
        """Replace typographic Unicode characters with ASCII equivalents
        to prevent SyntaxError when the model injects fancy punctuation."""
        for char, replacement in self._CODE_CHAR_MAP.items():
            code = code.replace(char, replacement)
        return code

    @tool(
        name="runpython",
        desc="Run Python code string. Args: code",
        category="Terminal",
    )
    def runpython(self, code: str) -> str:
        """Execute a Python code block and capture the output.

        Typographic Unicode characters are automatically sanitized.

        Args:
            code: The Python source code string to execute.

        Returns:
            The output of the python process or an error message.
        """
        return self._run("python -", timeout=60, input_data=self._sanitize_code(code))

    def _validate_script_content(self, p: Path) -> str:
        """Scan interior lines of a shell script for blocked commands.

        Reads the script file, strips comments and blank lines, merges
        line continuations, and validates each reconstructed command
        through ``_blocked_command_reason``.

        Args:
            p: Resolved Path to the script file.

        Returns:
            An empty string if the script is safe, or a normalized error
            string if any line is blocked.
        """
        suffix = p.suffix.lower()
        continuation_char = self._CONTINUATION_CHARS.get(suffix)
        if continuation_char is None:
            # Not a shell script we scan (e.g. .py) — skip.
            return ""

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error: Command blocked by safety rules: unable to read script for validation: {e}"

        lines = content.splitlines()
        current_line: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Filter full-line comments based on script type.
            is_comment = False
            if suffix in (".sh", ".bash", ".zsh", ".ps1"):
                if stripped.startswith("#"):
                    is_comment = True
            elif suffix in (".bat", ".cmd"):
                up = stripped.upper()
                if up.startswith("REM ") or up == "REM" or stripped.startswith("::"):
                    is_comment = True

            if is_comment:
                continue

            # Accumulate or finalize multi-line commands.
            if stripped.endswith(continuation_char):
                current_line.append(stripped[: -len(continuation_char)].strip())
                continue

            current_line.append(stripped)
            full_command = " ".join(current_line).strip()
            current_line = []

            if full_command:
                reason = self._blocked_command_reason(full_command)
                if reason:
                    if not reason.startswith("Command blocked by safety rules:"):
                        reason = f"Command blocked by safety rules: {reason}"
                    return f"Error: {reason}"

        # Handle trailing continuation (script ends on a continued line).
        if current_line:
            full_command = " ".join(current_line).strip()
            if full_command:
                reason = self._blocked_command_reason(full_command)
                if reason:
                    if not reason.startswith("Command blocked by safety rules:"):
                        reason = f"Command blocked by safety rules: {reason}"
                    return f"Error: {reason}"

        return ""

    @tool(
        name="runscript",
        desc="Run a script file. Args: path, interpreter (optional)",
        category="Terminal",
    )
    def runscript(self, path: str, interpreter: str = "") -> str:
        """Run a script file with optional interpreter override.

        Shell scripts (.sh, .bash, .ps1, .bat, .cmd) are scanned
        line-by-line for blocked commands before execution.  Python
        scripts (.py) skip interior scanning.

        Args:
            path: Path to the script file.
            interpreter: Optional interpreter override string.

        Returns:
            Command output or a normalized safety error string.
        """
        p = Path(path).resolve()
        if not p.exists():
            return f"Error: Script not found: {path}"

        # Deep content validation for shell scripts.
        script_error = self._validate_script_content(p)
        if script_error:
            return script_error

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
