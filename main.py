"""Project entry point for AgenticOs.

This file runs *before* the rest of the runtime imports so we can set
environment variables that control where cache files get written.
"""

from __future__ import annotations

import os


def _load_cache_root() -> str:
    """Best-effort load cache root from config.yaml without importing core.*."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "config.yaml")

    # Keep startup resilient: if YAML is broken, just fall back to defaults.
    try:
        import yaml  # type: ignore

        with open(cfg_path, "r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle) or {}
    except Exception:
        cfg = {}

    cache_cfg = (cfg.get("cache") or {}) if isinstance(cfg, dict) else {}
    root = (cache_cfg.get("root_dir") or "data/cache").strip()
    if not os.path.isabs(root):
        root = os.path.join(base_dir, root)
    return os.path.abspath(root)


def _apply_cache_env() -> None:
    """Route common tool caches into a single folder."""
    cache_root = _load_cache_root()
    os.makedirs(cache_root, exist_ok=True)

    # Python bytecode cache routing:
    # - Newer Python honors PYTHONPYCACHEPREFIX (routes __pycache__ content).
    # - Keep it separate from other caches.
    pycache = os.path.join(cache_root, "pycache")
    os.makedirs(pycache, exist_ok=True)
    os.environ.setdefault("PYTHONPYCACHEPREFIX", pycache)

    # Ruff cache (otherwise it creates .ruff_cache in the repo).
    ruff_cache = os.path.join(cache_root, "ruff")
    os.makedirs(ruff_cache, exist_ok=True)
    os.environ.setdefault("RUFF_CACHE_DIR", ruff_cache)

    # pip download/build cache (if you run pip install while developing).
    pip_cache = os.path.join(cache_root, "pip")
    os.makedirs(pip_cache, exist_ok=True)
    os.environ.setdefault("PIP_CACHE_DIR", pip_cache)

    # pytest cache (otherwise .pytest_cache in the repo). Only applied if user
    # hasn't set a cache dir already.
    pytest_cache = os.path.join(cache_root, "pytest")
    os.makedirs(pytest_cache, exist_ok=True)
    addopts = os.environ.get("PYTEST_ADDOPTS", "")
    if "--cache-dir" not in addopts:
        addopts = (addopts + " " if addopts else "") + f'--cache-dir="{pytest_cache}"'
        os.environ["PYTEST_ADDOPTS"] = addopts


def main() -> None:
    _apply_cache_env()

    from core.runtime import main as _runtime_main

    _runtime_main()


if __name__ == "__main__":
    main()
