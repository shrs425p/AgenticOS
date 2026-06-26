"""Module for paths.py"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


from kernel.base import tool
class PathsMixin:
    @tool(name="which", desc="Find executable path. Args: name", category="Terminal")
    def which(self, name: str) -> str:
        """which function."""
        p = shutil.which(name)
        return p or ""

    @tool(name="specialpaths", desc="List common user/system paths.", category="Terminal")
    def specialpaths(self) -> str:
        """specialpaths function."""
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

    @tool(name="locatepath", desc="Search common locations for a file or directory. Args: name, roots (optional)", category="Terminal")
    def locatepath(self, name: str, roots: str | list = "") -> str:
        """locatepath function."""
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
            stack = [str(base)]
            done = False
            while stack and not done:
                curr = stack.pop()
                try:
                    with os.scandir(curr) as it:
                        for entry in it:
                            try:
                                is_reparse = False
                                if entry.is_symlink():
                                    is_reparse = True
                                else:
                                    stat_val = entry.stat(follow_symlinks=False)
                                    if hasattr(stat_val, 'st_file_attributes') and (stat_val.st_file_attributes & 0x400):
                                        is_reparse = True
                                if is_reparse:
                                    continue

                                if entry.name.lower() == target.lower():
                                    hits.append(entry.path)
                                    if len(hits) >= 50:
                                        done = True
                                        break
                                
                                if entry.is_dir():
                                    stack.append(entry.path)
                            except Exception:
                                pass
                except Exception:
                    pass
            if len(hits) >= 50:
                break
        return "\n".join(hits) if hits else "No matches."
