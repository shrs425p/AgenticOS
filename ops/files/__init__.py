"""
AgenticOs — filesystem ops
File-system operations: info, archive, structured data, bulk ops, and CWD.
"""

from __future__ import annotations

from pathlib import Path

from ops.files.pack import ArchiveMixin
from ops.files.scan import BulkMixin
from ops.files.place import CwdMixin
from ops.files.stat import InfoMixin
from ops.files.format import StructuredMixin


class FileManager(
    InfoMixin,
    ArchiveMixin,
    StructuredMixin,
    BulkMixin,
    CwdMixin,
):
    def __init__(self, rules: dict | None = None, base_dir: str = "workspace"):
        self.rules = rules or {}
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        internal = self.rules.get("internal_data_dir") or ""
        try:
            self._internal_data_dir = Path(internal).resolve() if internal else None
        except Exception:
            self._internal_data_dir = None

    def _deny_internal_writes(self, path: Path):
        if not self.rules.get("protect_internal_data", False):
            return
        if self.rules.get("allow_internal_data_write", False):
            return
        if not self._internal_data_dir:
            return
        try:
            rp = path.resolve()
            base = self._internal_data_dir.resolve()
            if str(rp).lower().startswith(str(base).lower()):
                raise PermissionError(f"Internal data dir is protected: {base}")
        except PermissionError:
            raise
        except Exception:
            return

    def _deny_file_modify(self) -> None:
        if not self.rules.get("allow_file_modify", True):
            raise PermissionError("File modification is disabled by cfg.")

    def _deny_file_delete(self) -> None:
        if not self.rules.get("allow_file_delete", True):
            raise PermissionError("File deletion is disabled by cfg.")

    def _is_drive_root(self, path: Path) -> bool:
        resolved = path.resolve()
        return bool(resolved.anchor) and resolved == Path(resolved.anchor)

    def _deny_reserved_path(self, path: Path) -> None:
        if self.rules.get("allow_reserved_path_patterns", True):
            return
        patterns = self.rules.get("reserved_path_patterns", []) or []
        path_text = str(path)
        for pattern in patterns:
            if pattern and pattern in path_text:
                raise PermissionError(
                    f"Path matches reserved pattern from cfg: {pattern}"
                )

    def _resolve(self, path: str) -> Path:
        """Resolve a path with optional workspace restriction.

        When `security.restrict_paths` is true (default in hardened setups), absolute paths outside
        the workspace are rebased into the workspace root by filename. When false, absolute paths
        are respected.
        """
        p = Path(path)
        self._deny_reserved_path(p)

        if not p.is_absolute():
            if p.parts and p.parts[0] == self.base_dir.name:
                return (self.base_dir / Path(*p.parts[1:])).resolve()
            return (self.base_dir / p).resolve()

        resolved = p.resolve()
        base_resolved = self.base_dir.resolve()

        # If path restriction is disabled, allow absolute paths as-is.
        if not self.rules.get("restrict_paths", False):
            return resolved

        try:
            if not str(resolved).lower().startswith(str(base_resolved).lower()):
                return (base_resolved / p.name).resolve()
        except Exception:
            return (base_resolved / p.name).resolve()
        return resolved

