import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime import Agent, load_config


def test_tool_priority():
    cfg = load_config()
    cfg["agent"]["enable_cov"] = True

    agent = Agent(cfg)

    system = agent.build_system()

    assert "file_info:" in system
    assert "list_dir:" in system
    assert "read_file:" in system
    assert system.find("file_info:") < system.find("create_plugin:")


if __name__ == "__main__":
    try:
        test_tool_priority()
    except Exception as e:
        print(f"Error: {e}")
