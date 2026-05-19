"""Module for paths.py"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


from core.tool_base import tool
class PathsMixin:
    @tool(name="which", desc="Find executable path. Args: name", category="Terminal")
    def which(self, name: str) -> str:
        """which function."""
        p = shutil.which(name)
        return p or ""

    @tool(name="special_paths", desc="List common user/system paths.", category="Terminal")
    def special_paths(self) -> str:
        """special_paths function."""
        keys = [
            "USERPROFILE",
            "HOMEDRIVE",
            "HOMEPATH",
            "TEMP",
            "TMP",
            "APPDATA",
            "LOCALAPPDATA",
        ]
        lines = [f"{k}={os.environ.get(k, '')}" for k in keys]
        lines.append(f"cwd={os.getcwd()}")
        return "\n".join(lines)

    @tool(name="locate_path", desc="Search common locations for a file or directory. Args: name, roots (optional)", category="Terminal")
    def locate_path(self, name: str, roots: str | list = "") -> str:
        """locate_path function."""
        target = (name or "").strip()
        if not target:
            return "Error: name required."
        if isinstance(roots, list):
            root_list = [str(r).strip() for r in roots if str(r).strip()]
        else:
            root_list = [r.strip() for r in (roots or "").split("|") if r.strip()]
        if not root_list:
            root_list = [os.getcwd(), os.environ.get("USERPROFILE", os.getcwd())]
        hits = []
        for root in root_list:
            base = Path(root).expanduser()
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if p.name.lower() == target.lower():
                    hits.append(str(p))
                if len(hits) >= 50:
                    break
        return "\n".join(hits) if hits else "No matches."
