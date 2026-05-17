import os
from tools.terminal.env import EnvMixin

class MockEnvTools(EnvMixin):
    def __init__(self):
        self._env_overrides = {}

def test_get_env():
    tool = MockEnvTools()
    os.environ["TEST_MY_KEY"] = "my_value"
    try:
        assert tool.get_env("TEST_MY_KEY") == "my_value"
        assert tool.get_env("NONEXISTENT_KEY") == ""
    finally:
        os.environ.pop("TEST_MY_KEY", None)

def test_set_and_unset_env():
    tool = MockEnvTools()
    assert tool.set_env("MY_VAR", "123") == "Set MY_VAR"
    assert tool._env_overrides["MY_VAR"] == "123"
    
    assert tool.unset_env("MY_VAR") == "Unset MY_VAR"
    assert "MY_VAR" not in tool._env_overrides

def test_list_env():
    tool = MockEnvTools()
    os.environ["TEST_ENV_ALPHA"] = "alpha"
    os.environ["TEST_ENV_BETA"] = "beta"
    try:
        # All containing TEST_ENV_
        res = tool.list_env("TEST_ENV_")
        assert "TEST_ENV_ALPHA=alpha" in res
        assert "TEST_ENV_BETA=beta" in res
        
        # Filtering that matches none
        res_none = tool.list_env("TEST_ENV_NONEXISTENT")
        assert res_none == "(none)"
        
        # Filtering specific one
        res_specific = tool.list_env("TEST_ENV_ALPHA")
        assert "TEST_ENV_ALPHA=alpha" in res_specific
        assert "TEST_ENV_BETA" not in res_specific
    finally:
        os.environ.pop("TEST_ENV_ALPHA", None)
        os.environ.pop("TEST_ENV_BETA", None)
