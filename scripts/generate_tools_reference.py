"""Generate a markdown reference of all registered tools + descriptions.

Usage:
  python scripts/generate_tools_reference.py

Output:
  docs/tools_reference.md
"""

from __future__ import annotations

import os
from datetime import datetime

from core.runtime_config import BASE_DIR, load_config
from core.tool_registry import ToolRegistry


def main() -> int:
    cfg = load_config()
    tr = ToolRegistry(cfg)

    tools = sorted(tr.registry.items(), key=lambda kv: kv[0].lower())
    out_dir = os.path.join(BASE_DIR, "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "tools_reference.md")

    lines: list[str] = []
    lines.append("# Tools Reference")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total tools: {len(tools)}")
    lines.append("")
    lines.append(
        "This file is generated from the runtime ToolRegistry (authoritative)."
    )
    lines.append("")
    lines.append("| Tool | Description |")
    lines.append("| --- | --- |")
    for name, info in tools:
        desc = str((info or {}).get("desc", "")).strip().replace("\n", " ")
        # Keep markdown table safe.
        desc = desc.replace("|", "\\|")
        lines.append(f"| `{name}` | {desc} |")
    lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
