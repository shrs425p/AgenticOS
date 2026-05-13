import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.tool_registry import ToolRegistry
from core.runtime_config import load_config

def test_tool_descriptions_grouping():
    cfg = load_config()
    registry = ToolRegistry(cfg)
    
    descriptions = registry.tool_descriptions()
    
    print("\n--- Tool Descriptions Grouping ---")
    # Print the first few hundred characters to see the headers
    print(descriptions[:1000])
    
    # Check for headers
    if "[FILES]:" in descriptions and "[TERMINAL]:" in descriptions:
        print("\nPASS: Tool descriptions are grouped by category.")
    else:
        print("\nFAIL: Tool descriptions are NOT grouped correctly.")

if __name__ == "__main__":
    try:
        test_tool_descriptions_grouping()
    except Exception as e:
        print(f"Error: {e}")
