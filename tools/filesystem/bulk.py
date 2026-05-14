from __future__ import annotations

import fnmatch


class BulkMixin:
    def find_large_files(self, path: str, min_mb: str = "10") -> str:
        root = self._resolve(path)
        try:
            if (
                self._is_drive_root(root)
                and not self.rules.get("allow_full_drive_python_scans", True)
            ):
                return (
                    "Full-drive Python scans are disabled by config "
                    "(performance.allow_full_drive_python_scans=false)."
                )

            threshold = int(min_mb) * 1024 * 1024
            hits = []
            for p in root.rglob("*"):
                if not p.is_file():
                    continue
                try:
                    size = p.stat().st_size
                    if size >= threshold:
                        hits.append((size, str(p)))
                except PermissionError:
                    continue
            hits.sort(reverse=True)
            lines = [f"{self._size_human(sz)}  {fp}" for sz, fp in hits[:200]]
            return "\n".join(lines) if lines else "No large files found."
        except Exception as e:
            return f"Error: {e}"

    def replace_in_dir(
        self, path: str, pattern: str, old_text: str, new_text: str
    ) -> str:
        root = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(root)
        try:
            changed = 0
            for p in root.rglob("*"):
                if not p.is_file():
                    continue
                if pattern and not fnmatch.fnmatch(p.name, pattern):
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                if old_text in text:
                    p.write_text(text.replace(old_text, new_text), encoding="utf-8")
                    changed += 1
            return f"Updated {changed} file(s)."
        except Exception as e:
            return f"Error: {e}"
