"""Module for search.py"""
from __future__ import annotations

import fnmatch


from core.tool_base import tool
class SearchMixin:
    @tool(name="search_files", desc="Search files by name pattern. Args: path, pattern", category="Files")
    def search_files(self, path: str, pattern: str) -> str:
        root = self._resolve(path)
        try:
            if not root.exists():
                return "Path not found."
            matches = []
            for p in root.rglob("*"):
                if p.is_file() and fnmatch.fnmatch(p.name, pattern):
                    matches.append(str(p))
            return "\n".join(matches[:500]) if matches else "No matches."
        except Exception as e:
            return f"Error: {e}"

    @tool(name="grep_file", desc="Search text in file. Args: path, query", category="Files")
    def grep_file(self, path: str, query: str, case_sensitive: str = "true") -> str:
        p = self._resolve(path)
        try:
            cs = str(case_sensitive).lower() == "true"
            text = p.read_text(encoding="utf-8", errors="replace").splitlines()
            out = []
            for i, line in enumerate(text, 1):
                hay = line if cs else line.lower()
                needle = query if cs else query.lower()
                if needle in hay:
                    out.append(f"{i}: {line}")
            return "\n".join(out[:300]) if out else "No matches."
        except Exception as e:
            return f"Error: {e}"

    @tool(name="grep_dir", desc="Grep across directory. Args: path, query, pattern", category="Files")
    def grep_dir(self, path: str, query: str, pattern: str = "*") -> str:
        root = self._resolve(path)
        try:
            if (
                self._is_drive_root(root)
                and pattern == "*"
                and not self.rules.get("allow_full_drive_grep", True)
            ):
                return (
                    "Full-drive recursive grep is disabled by config "
                    "(performance.allow_full_drive_grep=false)."
                )

            matches = []
            for p in root.rglob(pattern):
                if not p.is_file():
                    continue
                hit = self.grep_file(str(p), query)
                if hit and hit != "No matches." and not hit.startswith("Error:"):
                    matches.append(f"\n== {p} ==\n{hit}")
            return "\n".join(matches[:50]) if matches else "No matches."
        except Exception as e:
            return f"Error: {e}"
