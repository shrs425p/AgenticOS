"""
AgenticOs — filesystem tools
Complete file-system operations: create, read, write, edit, delete, copy, move, search, grep, archive,
JSON/CSV helpers, diff, and stats.
"""

from __future__ import annotations

from pathlib import Path

from tools.filesystem.archive import ArchiveMixin
from tools.filesystem.bulk import BulkMixin
from tools.filesystem.cwd import CwdMixin
from tools.filesystem.diff_stats import DiffStatsMixin
from tools.filesystem.edit import EditMixin
from tools.filesystem.info import InfoMixin
from tools.filesystem.listing import ListingMixin
from tools.filesystem.mutations import MutationsMixin
from tools.filesystem.read_write import ReadWriteMixin
from tools.filesystem.search import SearchMixin
from tools.filesystem.structured import StructuredMixin


class FileManager(
    ReadWriteMixin,
    EditMixin,
    MutationsMixin,
    ListingMixin,
    InfoMixin,
    SearchMixin,
    ArchiveMixin,
    StructuredMixin,
    DiffStatsMixin,
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

    def _resolve(self, path: str) -> Path:
        """Resolve a path with optional workspace restriction.

        When `security.restrict_paths` is true (default in hardened setups), absolute paths outside
        the workspace are rebased into the workspace root by filename. When false, absolute paths
        are respected.
        """
        p = Path(path)
        if "AgentioOS.backup" in str(p):
            raise PermissionError("Access to AgentioOS.backup is strictly forbidden.")

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

    def _size_human(self, n: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} PB"
