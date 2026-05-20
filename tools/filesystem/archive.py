"""Module for archive.py"""
from __future__ import annotations

import zipfile


from core.tool_base import tool
class ArchiveMixin:
    @tool(name="zip_files", desc="Zip files/dirs. Args: output_path, *sources", category="Files")
    def zip_files(self, output_path: str, *sources) -> str:
        """zip_files function."""
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
                        for child in p.rglob("*"):
                            if child.is_file():
                                zf.write(
                                    child, arcname=str(child.relative_to(self.base_dir))
                                )
                    else:
                        zf.write(p, arcname=str(p.relative_to(self.base_dir)))
            return f"Created zip: {out}"
        except Exception as e:
            return f"Zip error: {e}"

    @tool(name="unzip_file", desc="Unzip archive. Args: path, dest", category="Files")
    def unzip_file(self, path: str, dest: str = ".") -> str:
        """unzip_file function."""
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
