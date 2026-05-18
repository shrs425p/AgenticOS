"""Project entry point for AgenticOs.

This file runs *before* the rest of the runtime imports so we can set
environment variables that control where cache files get written.
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # Fallback: manually load .env into os.environ if python-dotenv isn't available.
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())
        except OSError:
            pass


def _load_cache_root() -> str:
    """Best-effort load cache root from config.yaml without importing core.*."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "config.yaml")

    cfg = {}
    try:
        import yaml  # type: ignore

        try:
            with open(cfg_path, "r", encoding="utf-8") as handle:
                cfg = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError) as e:
            from core.logger import get_logger
            get_logger("startup").warning(
                "Failed to parse config.yaml, falling back to cache defaults: %s", e
            )
    except ImportError:
        pass

    cache_cfg = (cfg.get("cache") or {}) if isinstance(cfg, dict) else {}
    root = (cache_cfg.get("root_dir") or "data/cache").strip()
    if not os.path.isabs(root):
        root = os.path.join(base_dir, root)
    return os.path.abspath(root)


def _apply_cache_env() -> None:
    """Route common tool caches into a single folder."""
    cache_root = _load_cache_root()
    try:
        os.makedirs(cache_root, exist_ok=True)
    except OSError:
        pass

    # Python bytecode cache routing:
    # - Newer Python honors PYTHONPYCACHEPREFIX (routes __pycache__ content).
    # - Keep it separate from other caches.
    pycache = os.path.join(cache_root, "pycache")
    try:
        os.makedirs(pycache, exist_ok=True)
    except OSError:
        pass
    os.environ.setdefault("PYTHONPYCACHEPREFIX", pycache)

    # Ruff cache (otherwise it creates .ruff_cache in the repo).
    ruff_cache = os.path.join(cache_root, "ruff")
    try:
        os.makedirs(ruff_cache, exist_ok=True)
    except OSError:
        pass
    os.environ.setdefault("RUFF_CACHE_DIR", ruff_cache)

    # pip download/build cache (if you run pip install while developing).
    pip_cache = os.path.join(cache_root, "pip")
    try:
        os.makedirs(pip_cache, exist_ok=True)
    except OSError:
        pass
    os.environ.setdefault("PIP_CACHE_DIR", pip_cache)

    # pytest cache (otherwise .pytest_cache in the repo). Only applied if user
    # hasn't set a cache dir already.
    pytest_cache = os.path.join(cache_root, "pytest")
    try:
        os.makedirs(pytest_cache, exist_ok=True)
    except OSError:
        pass
    addopts = os.environ.get("PYTEST_ADDOPTS", "")
    if "--cache-dir" not in addopts:
        addopts = (addopts + " " if addopts else "") + f'--cache-dir="{pytest_cache}"'
        os.environ["PYTEST_ADDOPTS"] = addopts


def main() -> None:
    _apply_cache_env()

    # Early configuration validation check
    try:
        from core.runtime_config import load_config
        from core.config_validator import warn_config_issues

        cfg = load_config()
        result = warn_config_issues(cfg)
        if result.has_errors:
            print("  [ERROR] Critical configuration errors detected! Aborting startup.")
            import sys

            sys.exit(1)
    except Exception as e:
        from core.logger import get_logger

        get_logger("startup").warning("Early config validation bypassed/skipped: %s", e)

    import sys

    # Ensure stdout/stderr handle UTF-8 correctly, especially on Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if "--dream" in sys.argv:
        import logging

        logging.basicConfig(level=logging.INFO, format="%(message)s")
        logger = logging.getLogger("dream_cycle")

        # Run the Self-Improvement "Dreaming" cycle and exit
        import yaml

        base_dir = os.path.dirname(os.path.abspath(__file__))
        cfg_path = os.path.join(base_dir, "config.yaml")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            cfg = {}

        workspace = cfg.get("agent", {}).get("workspace", "workspace")
        if not os.path.isabs(workspace):
            workspace = os.path.join(base_dir, workspace)

        from core.self_improvement import run_dream_cycle

        # Try to get an LLM client for high-quality reflections
        llm = None
        try:
            from core.runtime_config import load_config as _load_config_internal

            full_cfg = _load_config_internal()
            provider = full_cfg.get("agent", {}).get("provider", "ollama").lower()
            if provider == "gemini":
                from core.model_clients import GeminiClient

                llm = GeminiClient(full_cfg)
            elif provider == "ollama":
                from core.model_clients import OllamaClient

                llm = OllamaClient(full_cfg)
        except Exception:
            pass

        logger.info("\n  AgenticOS Dream Cycle")
        logger.info("  Analyzing past performance...\n")
        result = run_dream_cycle(workspace, llm_client=llm, force=True)
        logger.info(f"  {result}\n")
        return

    from core.runtime import main as _runtime_main

    _runtime_main()


if __name__ == "__main__":
    main()
