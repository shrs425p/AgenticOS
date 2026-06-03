"""Module for bulk.py"""
from __future__ import annotations

import fnmatch


from core.tool_base import tool
class BulkMixin:
    @tool(name="find_large_files", desc="Find large files. Args: path, min_mb (optional)", category="Files")
    def find_large_files(self, path: str, min_mb: str = "10") -> str:
        """find_large_files function."""
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
            
            import os
            
            stack = [str(root)]
            while stack:
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

                                if entry.is_file():
                                    try:
                                        stat_val = entry.stat()
                                        size = stat_val.st_size
                                        if size >= threshold:
                                            hits.append((size, entry.path))
                                    except PermissionError:
                                        continue
                                elif entry.is_dir():
                                    stack.append(entry.path)
                            except Exception:
                                pass
                except Exception as e:
                    if curr == str(root):
                        raise
                    else:
                        pass

            hits.sort(reverse=True)
            lines = [f"{self._size_human(sz)}  {fp}" for sz, fp in hits[:200]]
            return "\n".join(lines) if lines else "No large files found."
        except Exception as e:
            return f"Error: {e}"

    def replace_in_dir(
        self, path: str, pattern: str, old_text: str, new_text: str
    ) -> str:
        """replace_in_dir function."""
        root = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(root)
        try:
            changed = 0
            
            import os
            from pathlib import Path
            
            stack = [str(root)]
            while stack:
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

                                if entry.is_file():
                                    if pattern and not fnmatch.fnmatch(entry.name, pattern):
                                        continue
                                    try:
                                        p_obj = Path(entry.path)
                                        text = p_obj.read_text(encoding="utf-8", errors="replace")
                                    except Exception:
                                        continue
                                    if old_text in text:
                                        p_obj.write_text(text.replace(old_text, new_text), encoding="utf-8")
                                        changed += 1
                                elif entry.is_dir():
                                    stack.append(entry.path)
                            except Exception:
                                pass
                except Exception as e:
                    if curr == str(root):
                        raise
                    else:
                        pass
            return f"Updated {changed} file(s)."
        except Exception as e:
            return f"Error: {e}"
