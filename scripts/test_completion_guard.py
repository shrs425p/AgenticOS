import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime import Agent, load_config

def test_completion_guard():
    cfg = load_config()
    agent = Agent(cfg)
    
    # Task: Write a long story and finish immediately without saving.
    # We use a very long prompt to ensure the response is likely > 1000 chars.
    user_input = "Write a very detailed, 2000-character story about a robotic cat. When you are done, say FINAL ANSWER immediately. Do NOT use the write_file tool."
    
    print("\nTesting Completion Guardrail...")
    
    agent.build_system()
    
    # We will simulate one turn of the agent loop manually to see if it triggers the guardrail in runtime.py
    # Actually, the logic is IN Agent.run, so we should run a mini-loop.
    
    # Since we can't easily run the full loop with mocks here without calling the real API,
    # we'll just verify the logic by injecting a fake response into the Agent's message history
    # and seeing if the 'continue' logic triggers.
    
    # Wait, the easiest way is to mock the client to return a long "FINAL ANSWER" response.
    class MockClient:
        def __init__(self, response):
            self.response = response
            self.model = "mock-model"
            self.provider = "ollama"
        def chat(self, messages, system=""):
            return self.response
        def list_models(self):
            return ["mock-model"]
    
    long_response = "OBJECTIVE: Write a story.\n\n" + "Meow! " * 300 + "\n\nFINAL ANSWER: Here is your story."
    
    # We'll run a manual simulation of the loop check
    import core.runtime
    warnings = []
    core.runtime.print_warning = lambda msg: warnings.append(msg)
    
    responses = [long_response]
    class IterClient:
        def __init__(self, resps):
            self.resps = resps
            self.idx = 0
            self.model = "mock-model"
            self.provider = "ollama"
        def chat(self, msgs, system=""):
            r = self.resps[self.idx]
            self.idx = (self.idx + 1) % len(self.resps)
            return r
        def list_models(self):
            return ["mock-model"]

    agent.client = IterClient(responses)
    
    # We'll run the agent with a max of 2 iterations
    agent.max_iter = 2
    try:
        agent.run(user_input)
    except Exception as e:
        print(f"Run ended (expected for mock): {e}")

    if any("Persistence Guardrail" in w for w in warnings):
        print("\nPASS: Completion guardrail triggered on hallucinated success.")
    else:
        print("\nFAIL: Completion guardrail did NOT trigger.")

if __name__ == "__main__":
    try:
        test_completion_guard()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
