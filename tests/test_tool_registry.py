import pytest
from core.tool_registry import ToolRegistry, tool

class DummyPlugin:
    @tool(name="dummy_tool", desc="A dummy tool for testing", category="Dummy")
    def dummy_tool(self, x: int) -> str:
        return f"Dummy {x}"

def test_tool_registration():
    registry = ToolRegistry(cfg={"rules": {}})
    registry._register_subsystem(DummyPlugin())
    
    assert "dummy_tool" in registry.registry
    
    fn = registry.registry["dummy_tool"]["fn"]
    assert registry.registry["dummy_tool"]["desc"] == "A dummy tool for testing"
    assert registry.registry["dummy_tool"]["category"] == "Dummy"
    assert fn(x=5) == "Dummy 5"

def test_tool_descriptions():
    registry = ToolRegistry(cfg={"rules": {}})
    registry.registry.clear()
    registry._register_subsystem(DummyPlugin())
    
    desc = registry.tool_descriptions()
    assert "[DUMMY]:" in desc
    assert "dummy_tool: A dummy tool for testing" in desc
