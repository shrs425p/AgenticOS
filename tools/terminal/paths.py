from __future__ import annotations

import os
import shutil
from pathlib import Path


class PathsMixin:
    def which(self, name: str) -> str:
        p = shutil.which(name)
        return p or ""

    def special_paths(self) -> str:
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

    def locate_path(self, name: str, roots: str | list = "") -> str:
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
