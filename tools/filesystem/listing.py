from __future__ import annotations

from pathlib import Path


from core.tool_base import tool
class ListingMixin:
    @tool(name="list_dir", desc="List directory contents. Args: path (optional)", category="Files")
    def list_dir(self, path: str = ".") -> str:
        p = self._resolve(path)
        try:
            if not p.exists():
                return "Directory not found."
            if not p.is_dir():
                return "Not a directory."
            items = []
            for item in sorted(
                p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            ):
                kind = "DIR " if item.is_dir() else "FILE"
                items.append(f"{kind} {item.name}")
            return "\n".join(items) if items else "(empty)"
        except Exception as e:
            return f"Error listing dir: {e}"

    @tool(name="tree", desc="Show directory tree. Args: path, max_depth (optional)", category="Files")
    def tree(self, path: str = ".", max_depth: str = "3") -> str:
        root = self._resolve(path)
        try:
            depth_limit = max(0, int(max_depth))
        except Exception:
            depth_limit = 3

        if not root.exists():
            return "Path not found."
        if root.is_file():
            return str(root.name)

        lines = [str(root.name)]

        def walk(directory: Path, prefix: str, current_depth: int):
            if current_depth >= depth_limit:
                return
            children = sorted(
                directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            )
            for i, child in enumerate(children):
                last = i == len(children) - 1
                branch = "└── " if last else "├── "
                lines.append(prefix + branch + child.name)
                if child.is_dir():
                    extension = "    " if last else "│   "
                    walk(child, prefix + extension, current_depth + 1)

        walk(root, "", 0)
        return "\n".join(lines)
