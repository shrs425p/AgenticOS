import os
import sys
from copy import deepcopy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime_config import load_config
from core.tool_registry import ToolRegistry


def _registry_with(**rule_overrides):
    cfg = deepcopy(load_config())
    cfg.setdefault("rules", {}).update(rule_overrides)
    cfg.setdefault("agent", {})["workspace"] = os.path.join(
        os.path.dirname(__file__), "..", "workspace"
    )
    return ToolRegistry(cfg)


def test_file_modify_policy_is_config_driven():
    registry = _registry_with(allow_file_modify=False)

    result = registry.call("write_file", {"path": "policy_test.txt", "content": "x"})

    assert "Permission denied" in result
    assert "disabled by config" in result


def test_file_delete_policy_is_config_driven():
    registry = _registry_with(allow_file_delete=False)

    result = registry.call("delete_file", {"path": "policy_test.txt"})

    assert "Permission denied" in result
    assert "disabled by config" in result


def test_web_search_policy_is_config_driven():
    registry = _registry_with(allow_web_search=False)

    result = registry.call("web_search", {"query": "AgenticOS"})

    assert "web search is disabled by config" in result


def test_network_policy_is_config_driven():
    registry = _registry_with(allow_network_access=False)

    result = registry.call("fetch_url", {"url": "https://example.com"})

    assert "network access is disabled by config" in result
