import os
import json
import pytest
from kernel.tasks import TaskTracker

@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "tasks").mkdir()
    return tmp_path

def test_set_goal(workspace):
    tracker = TaskTracker(workspace=str(workspace), session_id="test1")
    tracker.start("Write a test", "mock_provider", "mock_model")
    
    assert tracker.current is not None
    assert tracker.current["objective"] == "Write a test"
    assert tracker.current["status"] == "running"
    
    assert os.path.exists(tracker.active_json)
    assert os.path.exists(tracker.active_md)

def test_complete_task(workspace):
    tracker = TaskTracker(workspace=str(workspace), session_id="test2")
    tracker.start("Write a test", "mock_provider", "mock_model")
    tracker.complete("Test passed final answer")
    
    assert tracker.current["status"] == "completed"
    assert tracker.current["final_answer"] == "Test passed final answer"

def test_fail_task(workspace):
    tracker = TaskTracker(workspace=str(workspace), session_id="test3")
    tracker.start("Write a test", "mock_provider", "mock_model")
    tracker.fail("Test failed observation")
    
    assert tracker.current["status"] == "failed"
    assert tracker.current["last_observation"] == "Test failed observation"

def test_update_from_response(workspace):
    tracker = TaskTracker(workspace=str(workspace), session_id="test4")
    tracker.start("Main Task", "mock_provider", "mock_model")
    
    response = "OBJECTIVE: Solve the issue\nTASK: Run test\nCURRENT_STEP: Execute command\nPLAN:\n1. Step A\n2. Step B"
    tracker.update_from_response(response, iteration=1)
    
    assert tracker.current["iteration"] == 1
    assert tracker.current["last_response"] == response
    assert tracker.current["objective"] == "Solve the issue"
    assert tracker.current["task"] == "Run test"
    assert tracker.current["current_step"] == "Execute command"
    assert tracker.current["plan"] == ["Step A", "Step B"]

def test_load_active_session(workspace):
    active_json = os.path.join(workspace, "tasks", "active_task_test_load.json")
    tasks_data = [
        {"task_id": "123", "goal": "Old goal", "status": "running", "plan": []}
    ]
    with open(active_json, "w", encoding="utf-8") as f:
        json.dump(tasks_data, f)
        
    tracker = TaskTracker(workspace=str(workspace), session_id="test_load")
    assert len(tracker.tasks) == 1
    assert tracker.current["goal"] == "Old goal"

def test_record_action_observation_stall(workspace):
    tracker = TaskTracker(workspace=str(workspace), session_id="test_record")
    
    # Try recording when no current task exists
    tracker.record_action("my_tool", ["arg1"])
    tracker.record_observation("hello")
    tracker.note_stall("stalled")
    
    tracker.start("Test Goal", "provider", "model")
    tracker.record_action("my_tool", ["arg1", "arg2"])
    assert tracker.current["last_action"] == "my_tool | arg1 | arg2"
    
    tracker.record_observation("observed value")
    assert tracker.current["last_observation"] == "observed value"
    
    tracker.note_stall("stuck")
    assert tracker.current["stall_count"] == 1
    assert tracker.current["last_observation"] == "stuck"

def test_planner_hint(workspace):
    cfg = {"prompts": {"planner_hints": {"standard": "custom hint"}}}
    tracker = TaskTracker(workspace=str(workspace), session_id="test_hint", cfg=cfg)
    assert tracker.planner_hint() == ""  # No current task
    
    tracker.start("Test Goal", "provider", "model")
    assert tracker.planner_hint() == "custom hint"

def test_status_badge(workspace):
    tracker = TaskTracker(workspace=str(workspace), session_id="test_badge")
    assert tracker._status_badge("running") == "[RUNNING]"
    assert tracker._status_badge("completed") == "[COMPLETED]"
    assert tracker._status_badge("failed") == "[FAILED]"
    assert tracker._status_badge("other") == "[OTHER]"
