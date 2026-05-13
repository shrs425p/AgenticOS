import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime import Agent, load_config

def test_tool_priority():
    cfg = load_config()
    # Ensure evolution is on but priority is high
    cfg["agent"]["enable_cov"] = True
    
    agent = Agent(cfg)
    
    # Task: Get the size of a file in the workspace
    # It should use 'file_info' or 'list_dir'
    user_input = "Tell me the size of the file 'competitor_analysis.md' in the workspace."
    
    print("\nTesting Tool Priority...")
    # We won't actually run the full loop because it might take too long.
    # We just want to see the first ACTION.
    
    system = agent.build_system()
    messages = [{"role": "user", "content": user_input}]
    
    # Simulate one turn
    response = agent.client.chat(messages, system=system)
    print(f"\nAgent Response:\n{response}")
    
    # Verification: Check if it used 'create_plugin' or 'run_python' for a custom script
    if "create_plugin" in response or ("run_python" in response and "os.path.getsize" in response):
         print("\nFAIL: Agent attempted to evolve/script for a simple task.")
    else:
         print("\nPASS: Agent appears to be using existing tools (or at least not over-evolving).")

if __name__ == "__main__":
    try:
        test_tool_priority()
    except Exception as e:
        print(f"Error: {e}")
