"""URL presets for generating many useful open/search tools.

These presets are registered as individual tools at runtime to avoid writing
hundreds of nearly-identical functions.
"""

from __future__ import annotations

import os
import yaml

def load_url_presets(cfg: dict | None = None) -> list[dict]:
    """Load URL presets dynamically.

    Precedence:
    1) tools.url_presets_path (YAML file) if set and readable
    2) config/url_presets.yaml (default YAML file)
    3) tools.url_presets (inline list) if provided
    4) empty list (fallback)
    """
    cfg = cfg or {}
    tools_cfg = cfg.get("tools", {}) if isinstance(cfg, dict) else {}
    
    # 1. Custom path from config
    path = (tools_cfg.get("url_presets_path") or "").strip()
    
    # 2. Default config path
    if not path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "config", "url_presets.yaml")
        
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

    # 3. Inline presets from config
    inline = tools_cfg.get("url_presets")
    if isinstance(inline, list) and inline:
        return inline

    return []
