import os
from core.runtime_config import load_config
from core.tool_registry import ToolRegistry

def test_manual_evolution():
    print("--- [SIMULATION] Manual Evolution Test ---")
    cfg = load_config()
    registry = ToolRegistry(cfg)
    
    plugin_code = """from core.tool_registry import tool
@tool(name="test_evolve", desc="Test tool")
def test_evolve():
    return "Evolved!"
"""
    
    print("Calling create_plugin...")
    res = registry.call('create_plugin', {
        'name': 'test_evolve', 
        'code': plugin_code, 
        'description': 'Test plugin creation'
    })
    print(f"Result: {res}")
    
    plugin_path = os.path.join("tools", "plugins", "test_evolve.py")
    if os.path.exists(plugin_path):
        print(f"SUCCESS: {plugin_path} was created.")
        # Cleanup
        os.remove(plugin_path)
        print("Cleanup done.")
    else:
        print(f"FAILURE: {plugin_path} was NOT created.")

if __name__ == "__main__":
    test_manual_evolution()
