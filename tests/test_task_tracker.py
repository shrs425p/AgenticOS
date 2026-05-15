import os
import pytest
from core.task_tracker import TaskTracker

def test_set_goal(tmp_path):
    (tmp_path / "tasks").mkdir()
    tracker = TaskTracker(workspace=str(tmp_path), session_id="test1")
    
    tracker.start("Write a test", "mock_provider", "mock_model")
    
    assert tracker.current is not None
    assert tracker.current["objective"] == "Write a test"
    assert tracker.current["status"] == "running"
    
    # Check that it wrote to disk
    assert os.path.exists(tracker.active_json)
    assert os.path.exists(tracker.active_md)

def test_complete_task(tmp_path):
    (tmp_path / "tasks").mkdir()
    tracker = TaskTracker(workspace=str(tmp_path), session_id="test2")
    tracker.start("Write a test", "mock_provider", "mock_model")
    tracker.complete("Test passed final answer")
    
    assert tracker.current["status"] == "completed"
    assert tracker.current["final_answer"] == "Test passed final answer"

def test_fail_task(tmp_path):
    (tmp_path / "tasks").mkdir()
    tracker = TaskTracker(workspace=str(tmp_path), session_id="test3")
    tracker.start("Write a test", "mock_provider", "mock_model")
    tracker.fail("Test failed observation")
    
    assert tracker.current["status"] == "failed"
    assert tracker.current["last_observation"] == "Test failed observation"

def test_update_from_response(tmp_path):
    (tmp_path / "tasks").mkdir()
    tracker = TaskTracker(workspace=str(tmp_path), session_id="test4")
    tracker.start("Main Task", "mock_provider", "mock_model")
    
    # Mocking response parser logic slightly
    response = "Plan: \n- step 1\n- step 2"
    tracker.update_from_response(response, iteration=1)
    
    assert tracker.current["iteration"] == 1
    assert tracker.current["last_response"] == response
