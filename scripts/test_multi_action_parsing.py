import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime_ui import parse_actions

def test_single_action_enforcement():
    # Simulated response with two ACTION blocks
    multi_action_text = """
    OBJECTIVE: Fetch Bitcoin price and write to file.
    PLAN: 1. Fetch price. 2. Write file.
    
    ACTION: {"tool": "web_search", "args": {"query": "bitcoin price"}}
    
    ACTION: {"tool": "write_file", "args": {"path": "price.txt", "content": "100k"}}
    """
    
    print("\nTesting Single Action Enforcement...")
    actions = parse_actions(multi_action_text)
    
    print(f"Found {len(actions)} actions.")
    for i, (tool, args) in enumerate(actions):
        print(f"  {i+1}: {tool}({args})")
        
    if len(actions) == 1:
        print("\nPASS: Parser correctly enforced single action.")
        if actions[0][0] == "web_search":
            print("PASS: First action was preserved.")
        else:
            print(f"FAIL: Wrong action preserved: {actions[0][0]}")
    else:
        print(f"\nFAIL: Parser returned {len(actions)} actions instead of 1.")

if __name__ == "__main__":
    test_single_action_enforcement()
