"""
AgenticOs — Meta-Evolution Plugin
Allows the agent to autonomously generate and install new capabilities.
"""

import os
from core.tool_registry import tool

@tool(
    name="create_plugin",
    desc="Autonomously create a new Python tool plugin. Args: name (lowercase), code (Python string), description (str). The code MUST use the @tool decorator.",
    category="meta",
    version="1.0.0",
    author="AgenticOs Engine"
)
def create_plugin(name: str, code: str, description: str = "") -> str:
    """
    Writes a new .py file to tools/plugins/ to expand agent capabilities.
    """
    if not name.endswith(".py"):
        filename = f"{name}.py"
    else:
        filename = name
        
    plugin_dir = os.path.join(os.path.dirname(__file__))
    file_path = os.path.join(plugin_dir, filename)
    
    # Basic Validation
    if "@tool" not in code:
        return "Error: The plugin code must include the '@tool' decorator from 'core.tool_registry'."
    
    if "def " not in code:
        return "Error: No function definition found in code."

    try:
        # Check if file exists
        if os.path.exists(file_path):
            return f"Error: Plugin '{filename}' already exists. Use a different name or edit the file manually."

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        return f"SUCCESS: Plugin '{filename}' created in tools/plugins/. Hot-reloader will register it in a few seconds. You can then call the new tool."
    except Exception as e:
        return f"Error creating plugin: {e}"
