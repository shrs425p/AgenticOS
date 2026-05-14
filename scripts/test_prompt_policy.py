import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime_config import load_config


def test_prompt_discourages_tool_name_leakage_in_capability_answers():
    prompt = load_config()["prompts"]["system_prompt"]

    assert "Capability descriptions:" in prompt
    assert "INTERNAL_NAMES_PRIVATE_BY_DEFAULT" in prompt
    assert "plain language" in prompt
