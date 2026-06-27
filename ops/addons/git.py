"""Module for git_manager.py"""
from __future__ import annotations

import subprocess
from kernel.registry import tool

def _run_git(args: list[str]) -> str:
    """Helper to run git command in the current working directory."""
    try:
        # Check if git is available
        res = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False
        )
        if res.returncode != 0:
            err = res.stderr.strip()
            return f"Git error (exit code {res.returncode}): {err}"
        return res.stdout.strip() or "Success (no output)"
    except FileNotFoundError:
        return "Error: 'git' command not found. Please install git and make sure it is in your system PATH."
    except Exception as e:
        return f"Error executing git command: {e}"

def gitstatus() -> str:
    """Gets the status of the git repository (staged, unstaged, untracked files)."""
    return _run_git(["status", "-s"])

def gitdiff(staged: bool = False) -> str:
    """Shows changes in the working directory or staged index."""
    args = ["diff", "--cached"] if staged else ["diff"]
    return _run_git(args)

def gitadd(files: list[str]) -> str:
    """Adds file contents to the staging index (git add)."""
    if not files:
        return "Error: no files specified to add."
    if isinstance(files, str):
        files = [files]
    return _run_git(["add"] + files)

def gitcommit(message: str) -> str:
    """Commits staged changes to the repository history (git commit)."""
    msg = (message or "").strip()
    if not msg:
        return "Error: commit message cannot be empty."
    return _run_git(["commit", "-m", msg])

def gitlog(limit: int = 10) -> str:
    """Displays commit history (git log)."""
    try:
        lim = int(limit)
    except Exception:
        lim = 10
    return _run_git(["log", "-n", str(lim), "--oneline"])

@tool(
    name="git_control",
    desc="Manage git repository. Args: action (Literal['status', 'diff', 'add', 'commit', 'log']), staged (bool, optional, for diff), files (list of strings, optional, for add), message (str, optional, for commit), limit (int, optional, for log)",
    category="Git"
)
def git_control(action: str, staged: bool = False, files: list[str] | None = None, message: str = "", limit: int = 10) -> str:
    """Manage the Git repository using consolidated actions."""
    act = str(action).strip().lower()
    if act == "status":
        return gitstatus()
    elif act == "diff":
        return gitdiff(staged=staged)
    elif act == "add":
        if not files:
            return "Error: 'files' argument is required for 'add'."
        return gitadd(files)
    elif act == "commit":
        if not message:
            return "Error: 'message' argument is required for 'commit'."
        return gitcommit(message)
    elif act == "log":
        return gitlog(limit=limit)
    else:
        return f"Error: Unknown git action: {action}. Valid options: status, diff, add, commit, log"
