"""Module for git_manager.py"""
from __future__ import annotations

import os
import subprocess
from core.tool_registry import tool

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

@tool(
    name="git_status",
    desc="Get git status of the current repository.",
    category="Git"
)
def git_status() -> str:
    """Gets the status of the git repository (staged, unstaged, untracked files)."""
    return _run_git(["status", "-s"])

@tool(
    name="git_diff",
    desc="Get current unstaged changes (or staged if staged=True). Args: staged (bool, optional)",
    category="Git"
)
def git_diff(staged: bool = False) -> str:
    """Shows changes in the working directory or staged index."""
    args = ["diff", "--cached"] if staged else ["diff"]
    return _run_git(args)

@tool(
    name="git_add",
    desc="Stage file changes. Args: files (list of file paths or patterns).",
    category="Git"
)
def git_add(files: list[str]) -> str:
    """Adds file contents to the staging index (git add)."""
    if not files:
        return "Error: no files specified to add."
    if isinstance(files, str):
        files = [files]
    return _run_git(["add"] + files)

@tool(
    name="git_commit",
    desc="Commit staged changes. Args: message (commit message).",
    category="Git"
)
def git_commit(message: str) -> str:
    """Commits staged changes to the repository history (git commit)."""
    msg = (message or "").strip()
    if not msg:
        return "Error: commit message cannot be empty."
    return _run_git(["commit", "-m", msg])

@tool(
    name="git_log",
    desc="Show recent commit logs. Args: limit (max commits to show, default 10).",
    category="Git"
)
def git_log(limit: int = 10) -> str:
    """Displays commit history (git log)."""
    try:
        lim = int(limit)
    except Exception:
        lim = 10
    return _run_git(["log", "-n", str(lim), "--oneline"])
