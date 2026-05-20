from unittest.mock import MagicMock
from core.runtime import CLI

def test_tasks_command():
    cli = CLI.__new__(CLI)
    cli.cfg = {
        "agent": {"provider": "ollama", "workspace": "workspace", "verbose_thinking": False},
        "prompts": {},
    }
    cli.running = True
    cli.verbose = False
    
    # Mock task tracker
    cli.task_tracker = MagicMock()
    
    # 1. Test empty tasks list
    cli.task_tracker.tasks = []
    cli.task_tracker.current = None
    cli.handle_command("/tasks")
    cli.handle_command("/tasks current")
    
    # 2. Test with tasks
    mock_task = {
        "status": "running",
        "goal": "Test goal that is very long to see if truncation works properly when it exceeds fifty five characters",
        "iteration": 2,
        "current_step": "Step 2",
        "plan": ["Step 1", "Step 2", "Step 3"],
        "last_action": "test_tool | arg1",
        "last_observation": "Test observation"
    }
    cli.task_tracker.tasks = [mock_task]
    cli.task_tracker.current = mock_task
    
    # This should print the list format without error
    cli.handle_command("/tasks")
    cli.handle_command("/tasks list")
    
    # This should print the active task details without error
    cli.handle_command("/tasks current")
    cli.handle_command("/tasks show")
    
    # Test completed status badge
    mock_task["status"] = "completed"
    cli.handle_command("/tasks current")
    
    # Test failed status badge
    mock_task["status"] = "failed"
    cli.handle_command("/tasks list")

    # Test unknown argument
    cli.handle_command("/tasks unknown_arg")
