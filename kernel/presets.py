"""URL presets for generating many useful open/search ops.

These presets are registered as individual ops at runtime to avoid writing
hundreds of nearly-identical functions.
"""

from __future__ import annotations

import os
import yaml

def load_url_presets(cfg: dict | None = None) -> list[dict]:
    """Load URL presets dynamically.

    Precedence:
    1) ops.url_presets_path (YAML file) if set and readable
    2) cfg/presets.yaml (default YAML file)
    3) ops.url_presets (inline list) if provided
    4) empty list (fallback)
    """
    cfg = cfg or {}
    ops_cfg = cfg.get("ops", {}) if isinstance(cfg, dict) else {}
    
    # 1. Custom path from cfg
    path = (ops_cfg.get("url_presets_path") or "").strip()
    
    # 2. Default cfg path
    if not path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "cfg", "presets.yaml")
        
    if path:
        try:
            if not os.path.isabs(path):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                path = os.path.join(base_dir, path)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
                # Support either {"presets":[...]} or direct list in the file.
                if isinstance(data, dict) and isinstance(data.get("presets"), list):
                    return data["presets"]
                if isinstance(data, list):
                    return data
        except Exception:
            pass

    # 3. Inline presets from cfg
    inline = ops_cfg.get("url_presets")
    if isinstance(inline, list) and inline:
        return inline

    return []
