import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime_config import load_config


def test_thinking_models_clear_reasoning_by_default():
    cfg = load_config()

    assert cfg["agent"]["verbose_thinking"] is False
    assert cfg["model_thinking"]["enabled"] is True
    assert cfg["model_thinking"]["clear_thinking"] is True
