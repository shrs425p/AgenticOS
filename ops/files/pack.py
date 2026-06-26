"""Module for archive.py"""
from __future__ import annotations

import zipfile
from pathlib import Path


from kernel.base import tool
class ArchiveMixin:
    @tool(name="zipfiles", desc="Zip files/dirs. Args: output_path, *sources", category="Files")
    def zipfiles(self, output_path: str, *sources) -> str:
        """zipfiles function."""
        out = self._resolve(output_path)
        self._deny_file_modify()
        self._deny_internal_writes(out)
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for src in sources:
                    p = self._resolve(str(src))
                    if not p.exists():
                        continue
                    if p.is_dir():
                        import os
                        stack = [str(p)]
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
                                                child_path = Path(entry.path)
                                                try:
                                                    arcname = str(child_path.resolve().relative_to(self.base_dir.resolve()))
                                                    zf.write(child_path, arcname=arcname)
                                                except Exception:
                                                    pass
                                            elif entry.is_dir():
                                                stack.append(entry.path)
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                    else:
                        zf.write(p, arcname=str(p.resolve().relative_to(self.base_dir.resolve())))
            return f"Created zip: {out}"
        except Exception as e:
            return f"Zip error: {e}"

    @tool(name="unzipfile", desc="Unzip archive. Args: path, dest", category="Files")
    def unzipfile(self, path: str, dest: str = ".") -> str:
        """unzipfile function."""
        p = self._resolve(path)
        d = self._resolve(dest)
        self._deny_file_modify()
        self._deny_internal_writes(d)
        try:
            d.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(p, "r") as zf:
                zf.extractall(d)
            return f"Extracted to: {d}"
        except Exception as e:
            return f"Unzip error: {e}"
