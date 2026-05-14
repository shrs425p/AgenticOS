import os
import sys

import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime_config import load_config


def test_layered_config_loads_advanced_sections():
    cfg = load_config()

    assert cfg["prompts"]["system_prompt"]
    assert "rules" in cfg
    assert "tools" in cfg
    assert "memory" in cfg


def test_root_config_overrides_layered_files(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "providers.yaml").write_text(
        yaml.safe_dump({"agent": {"provider": "ollama", "stream": False}}),
        encoding="utf-8",
    )
    root_config = tmp_path / "config.yaml"
    root_config.write_text(
        yaml.safe_dump({"agent": {"provider": "nvidia"}}),
        encoding="utf-8",
    )

    cfg = load_config(str(root_config))

    assert cfg["agent"]["provider"] == "nvidia"
    assert cfg["agent"]["stream"] is False
