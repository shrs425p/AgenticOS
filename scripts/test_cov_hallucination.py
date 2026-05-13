import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime import Agent

def test_cov_hallucination_fix():
    print("Testing CoV Tool Existence Hallucination Fix...")
    
    # We need to mock the client and tools
    class MockClient:
        def __init__(self):
            self.model = "mock-model"
        def chat(self, messages, system=""):
            # A real model would now see rule #4: "TOOL EXISTENCE: Assume the tool 'count_lines' is valid and registered."
            # We want to test that the prompt is constructed correctly.
            prompt = messages[0]["content"]
            if "Assume the tool 'count_lines' is valid and registered" in prompt:
                return "OK"
            else:
                return "REJECT: Tool 'count_lines' is not defined in the available tool set."
    
    class MockTools:
        def __init__(self):
            self.registry = {"count_lines": lambda: None, "read_file": lambda: None}
            self._canvas = ""
            self.shadow_mode = False
            
    # Bypass __init__ to avoid config dependency
    agent = object.__new__(Agent)
    agent.client = MockClient()
    agent.tools = MockTools()
    agent.cov_model = None
    
    context = "OBJECTIVE: Count lines.\nPLAN: Use count_lines.\nCURRENT_STEP: Counting.\nACTION: count_lines"
    
    # Test verify_action
    is_valid, reason = agent.verify_action("count_lines", {"path": "test.txt"}, context)
    
    if is_valid and reason == "OK":
        print("\nPASS: CoV monitor accepted the tool call. The prompt correctly instructed the model to assume the tool is registered.")
    else:
        print(f"\nFAIL: CoV monitor rejected the tool call. Reason: {reason}")

if __name__ == "__main__":
    test_cov_hallucination_fix()
