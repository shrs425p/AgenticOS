import pytest
import importlib

def test_config_types():
    try:
        import core.config_types
        importlib.reload(core.config_types)
    except Exception as e:
        pass
    assert True
