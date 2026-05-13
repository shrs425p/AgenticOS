from __future__ import annotations

import difflib


class DiffStatsMixin:
    def diff_files(self, path1: str, path2: str) -> str:
        p1 = self._resolve(path1)
        p2 = self._resolve(path2)
        try:
            a = p1.read_text(encoding="utf-8", errors="replace").splitlines()
            b = p2.read_text(encoding="utf-8", errors="replace").splitlines()
            diff = difflib.unified_diff(
                a, b, fromfile=str(p1), tofile=str(p2), lineterm=""
            )
            out = "\n".join(list(diff)[:2000])
            return out if out else "(no differences)"
        except Exception as e:
            return f"Diff error: {e}"

    def count_lines(self, path: str) -> str:
        p = self._resolve(path)
        try:
            return str(
                len(p.read_text(encoding="utf-8", errors="replace").splitlines())
            )
        except Exception as e:
            return f"Error: {e}"

    def word_count(self, path: str) -> str:
        p = self._resolve(path)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            words = len(text.split())
            lines = len(text.splitlines())
            chars = len(text)
            return f"words: {words}\nlines: {lines}\nchars: {chars}"
        except Exception as e:
            return f"Error: {e}"
