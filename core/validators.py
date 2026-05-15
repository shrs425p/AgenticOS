"""Post-tool validation helpers.

Goal: reduce "tool said OK, but nothing happened" failures by checking reality
after common actions and returning a short validation note.
"""

from __future__ import annotations

from pathlib import Path


import os

def _normalize_path(value: str) -> str:
    if not isinstance(value, str):
        return str(value)
    return os.path.normpath(value)


def _resolve_path(path_str: str, workspace_root: Path) -> Path:
    p = Path(_normalize_path(path_str))
    if not p.is_absolute():
        if p.parts and p.parts[0] == workspace_root.name:
            return (workspace_root / Path(*p.parts[1:])).resolve()
        return (workspace_root / p).resolve()
    return p.resolve()


def validate_tool(tool_name: str, args, result: str, *, workspace_root: Path) -> str:
    name = (tool_name or "").strip()
    if not name:
        return ""

    # Filesystem validations
    if name in {
        "write_file",
        "append_file",
        "touch",
        "write_json",
        "write_csv",
    }:
        path = _arg_get(args, "path", index=0)
        if not path:
            return ""
        p = _resolve_path(path, workspace_root)
        return (
            "VALIDATION: file exists"
            if p.exists()
            else f"VALIDATION: file missing ({p})"
        )

    if name in {"create_dir"}:
        path = _arg_get(args, "path", index=0)
        if not path:
            return ""
        p = _resolve_path(path, workspace_root)
        return (
            "VALIDATION: dir exists" if p.is_dir() else f"VALIDATION: dir missing ({p})"
        )

    if name in {"delete_file"}:
        path = _arg_get(args, "path", index=0)
        if not path:
            return ""
        p = _resolve_path(path, workspace_root)
        return (
            "VALIDATION: file deleted"
            if not p.exists()
            else f"VALIDATION: file still exists ({p})"
        )

    if name in {"delete_dir"}:
        path = _arg_get(args, "path", index=0)
        if not path:
            return ""
        p = _resolve_path(path, workspace_root)
        return (
            "VALIDATION: dir deleted"
            if not p.exists()
            else f"VALIDATION: dir still exists ({p})"
        )

    if name in {"copy_file", "move_file"}:
        dst = _arg_get(args, "dst", index=1)
        if not dst:
            return ""
        p = _resolve_path(dst, workspace_root)
        return (
            "VALIDATION: destination exists"
            if p.exists()
            else f"VALIDATION: destination missing ({p})"
        )

    if name in {"download_file"}:
        dest = _arg_get(args, "dest_path", index=1)
        if not dest:
            return ""
        p = _resolve_path(dest, workspace_root)
        return (
            "VALIDATION: download exists"
            if p.exists()
            else f"VALIDATION: download missing ({p})"
        )

    # Terminal validations (best-effort)
    if name in {"run_command", "run_powershell", "run_script"}:
        # If the tool output includes an exit marker, surface it as validation.
        r = (result or "").lower()
        if "[exit:" in r or "exit code" in r:
            return "VALIDATION: command returned exit status (see output)"
        return ""

    # App/URL openers: cannot reliably validate without deeper OS hooks.
    if name in {"open_url"}:
        return ""

    return ""


def _arg_get(args, key: str, *, index: int | None = None) -> str:
    """Pull an argument from dict-args, or fall back to a list index for legacy actions."""
    if isinstance(args, dict):
        v = args.get(key)
        return str(v) if v is not None else ""
    if isinstance(args, list) and index is not None and 0 <= index < len(args):
        v = args[index]
        return str(v) if v is not None else ""
    return ""
