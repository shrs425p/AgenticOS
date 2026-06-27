import os
import time
import pytest
from unittest.mock import MagicMock
from kernel.cli import Agent

@pytest.fixture
def e2e_cfg(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "tasks").mkdir()
    cfg = {
        "agent": {
            "provider": "ollama",
            "workspace": str(workspace),
            "max_iterations": 10,
            "verbose_thinking": True,
            "auto_confirm": True,
            "hot_reload": False,
            "enable_cov": False,
            "stream": True,
            "fallback_providers": []
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "default_model": "test-model",
            "timeout": 30.0,
            "temperature": 0.7
        },
        "memory": {
            "sqlite_db_path": str(workspace / "db.sqlite3")
        },
        "heuristics": {
            "session_id_format": "%Y%m%d_%H%M%S",
            "direct_response_max_chars": 6000,
            "direct_response_max_words": 900,
            "hot_reload_throttle": 0.0,
            "max_dots_in_response": 50
        },
        "performance": {
            "max_context_messages": 40
        },
        "autonomy": {
            "autopilot": True,
            "task_tracking": True
        },
        "logging": {
            "audit_enabled": False
        },
        "prompts": {
            "nudges": {
                "repetition": "Alternative strategy nudge",
                "empty_response": "Empty response nudge",
                "format_error": "Format error nudge"
            }
        }
    }
    return cfg

def test_e2e_multi_step_workflow(e2e_cfg):
    """End-to-end integration test running a multi-step filesystem workflow."""
    agent = Agent(e2e_cfg)
    
    test_filepath = os.path.join(agent.workspace, "e2e_file.json")
    escaped_path = test_filepath.replace("\\", "\\\\")
    
    responses = [
        # Step 1: Write JSON
        f'THOUGHT: Writing initial content.\nACTION: {{"tool": "writejson", "args": {{"path": "{escaped_path}", "data": "{{\\"content\\": \\"E2E Integration Test Content\\"}}"}}}}',
        # Step 2: Read JSON
        f'THOUGHT: Reading file to verify.\nACTION: {{"tool": "readjson", "args": {{"path": "{escaped_path}"}}}}',
        # Step 3: Finish
        'FINAL ANSWER: Workflow completed successfully. Files are verified.'
    ]
    
    agent.client.chat = MagicMock(side_effect=responses)
    
    start_time = time.time()
    agent.run("Start the filesystem test workflow.")
    end_time = time.time()
        
    execution_time = end_time - start_time
    
    # Assertions
    # 1. The test file was actually written to disk
    assert os.path.exists(test_filepath), "File should be created on disk"
    with open(test_filepath, "r") as f:
        content = f.read()
    assert "E2E Integration Test Content" in content
    
    # 2. Performance regression time limit check:
    # E2E simulated loop should finish quickly (e.g., under 5.0 seconds)
    assert execution_time < 5.0, f"Performance regression: E2E execution took {execution_time:.2f}s (exceeded 5.0s limit)"
