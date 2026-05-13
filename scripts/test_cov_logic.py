import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime import Agent

def test_cov_sequential_support():
    # Complete mock config
    cfg = {
        "agent": {
            "provider": "nvidia",
            "model": "openai/gpt-oss-120b",
            "workspace": "workspace",
            "max_iterations": 10,
            "verbose_thinking": True,
            "enable_cov": True,
            "cov_model": None
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "default_model": "qwen2.5-coder:7b",
            "timeout": 300,
            "temperature": 0.8,
            "num_ctx": 32768,
            "num_predict": 16384
        },
        "cloud": {
            "nvidia": {
                "base_url": "https://integrate.api.nvidia.com/v1",
                "model": "openai/gpt-oss-120b",
                "temperature": 1.0,
                "top_p": 1.0,
                "max_tokens": 8192,
                "timeout": 300
            }
        },
        "memory": {"backend": "json"},
        "logging": {"audit_enabled": False},
        "rules": {},
        "prompts": {"system_prompt": "You are an assistant."}
    }
    
    # Initialize Agent
    agent = Agent(cfg)
    
    # Define a scenario: Sequential searches for competitors
    tool_name = "web_search"
    args = {"query": "AutoGPT GitHub repository"}
    context = "GOAL: Research top 5 competitors. So far, I have found none. I need to search for each one individually."
    
    print("\nTesting CoV Sequential Action Support...")
    verified, reason = agent.verify_action(tool_name, args, context)
    
    print(f"Verified: {verified}")
    print(f"Reason: {reason}")
    
    if verified and reason.upper() == "OK":
        print("PASS: CoV allowed sequential search.")
    else:
        print(f"FAIL: CoV rejected sequential search or returned non-OK. Reason: {reason}")

if __name__ == "__main__":
    try:
        test_cov_sequential_support()
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
