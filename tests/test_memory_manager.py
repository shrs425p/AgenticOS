import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from core.memory_manager import (
    MemoryManager,
    initialize_memory_manager,
    get_memory_manager,
    log_task_completion,
    log_daily_event,
    get_memory_stats,
    consolidate_memory,
    cleanup_old_memories
)

@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws

def test_init_memory_manager(workspace):
    mm = MemoryManager(str(workspace))
    assert mm.workspace_root == workspace
    assert mm.memory_dir.exists()
    assert mm.long_term_memory_file == workspace / "MEMORY.md"

def test_commitments(workspace):
    mm = MemoryManager(str(workspace))
    
    res = mm.register_commitment("Test commit", "tomorrow")
    assert "Test commit" in res
    assert len(mm.commitments) == 1
    
    active = mm.get_active_commitments()
    assert "Test commit" in active
    assert "tomorrow" in active
    
    cid = mm.commitments[0]["id"]
    res_complete = mm.complete_commitment(cid)
    assert "marked as completed" in res_complete
    
    active_after = mm.get_active_commitments()
    assert "Test commit" not in active_after
    
    res_bad = mm.complete_commitment("bad_id")
    assert "not found" in res_bad

def test_get_relevant_context(workspace):
    mm = MemoryManager(str(workspace))
    
    # query too short
    assert mm.get_relevant_context("sh") == ""
    
    # MEMORY.md match
    mm.long_term_memory_file.write_text("line 1\nspecial keyword\nline 3", encoding="utf-8")
    ctx = mm.get_relevant_context("special keyword")
    assert "special keyword" in ctx
    assert "[MEMORY.md]" in ctx
    
    # Daily log match
    today = datetime.now()
    daily_file = mm.get_daily_memory_file(today)
    daily_file.write_text("another unique term", encoding="utf-8")
    ctx2 = mm.get_relevant_context("unique term")
    assert "[LOG" in ctx2

def test_logging_events(workspace):
    mm = MemoryManager(str(workspace))
    
    mm.log_daily_event("TEST_EVENT", "description", {"meta": "data"})
    daily_file = mm.get_daily_memory_file()
    content = daily_file.read_text(encoding="utf-8")
    assert "TEST_EVENT" in content
    assert "description" in content
    assert "meta: data" in content

def test_log_task_completion(workspace):
    mm = MemoryManager(str(workspace))
    mm.log_task_completion("goal1", "answer1", ["tool1"], True, 10.5, {"extra": "info"})
    
    tracking_file = mm.memory_dir / "task_tracking.json"
    assert tracking_file.exists()
    
    data = json.loads(tracking_file.read_text(encoding="utf-8"))
    assert len(data["completed_tasks"]) == 1
    assert data["completed_tasks"][0]["goal"] == "goal1"

def test_consolidation_check(workspace):
    mm = MemoryManager(str(workspace))
    mm.memory_consolidation_threshold = 2
    
    mm.log_task_completion("goal1", "ans", [], True, 1)
    mm.log_task_completion("goal2", "ans", [], False, 1)
    mm._check_consolidation_needed()
    
    # Threshold is 2, so consolidation should have occurred
    tracking_file = mm.memory_dir / "task_tracking.json"
    data = json.loads(tracking_file.read_text(encoding="utf-8"))
    assert data.get("last_consolidation") is not None

def test_generate_insights_with_llm(workspace):
    client = MagicMock()
    client.chat.return_value = "- LLM insight 1\n- LLM insight 2"
    mm = MemoryManager(str(workspace), llm_client=client)
    
    tasks = [
        {"goal": "G1", "success": True, "duration": 5, "tools_used": ["T1"], "timestamp": "2024-01-01T00:00:00"},
        {"goal": "G2", "success": False, "duration": 10, "tools_used": ["T1", "T2"], "timestamp": "2024-01-01T00:01:00"}
    ]
    
    insights = mm._generate_insights_from_tasks(tasks)
    assert len(insights["success_patterns"]) == 2
    assert "LLM insight 1" in insights["success_patterns"][0]
    assert insights["success_rate"] == 0.5
    assert insights["avg_duration"] == 7.5

def test_extract_patterns_fallback(workspace):
    mm = MemoryManager(str(workspace))
    tasks = [
        {"goal": "create file"},
        {"goal": "create api"},
        {"goal": "read file"}
    ]
    patterns = mm._extract_patterns(tasks)
    # actions: create, read
    # objects: file, api
    assert any("create" in p for p in patterns)
    assert any("file" in p for p in patterns)

def test_update_long_term_memory(workspace):
    mm = MemoryManager(str(workspace))
    mm.long_term_memory_file.write_text("# Existing Header\n\nOld info", encoding="utf-8")
    
    insights = {
        "success_rate": 1.0,
        "avg_duration": 5.0,
        "success_patterns": ["Pattern 1"]
    }
    recent = [{"goal": "Goal1", "success": True}]
    
    mm._update_long_term_memory(insights, recent)
    
    content = mm.long_term_memory_file.read_text(encoding="utf-8")
    assert "Existing Header" in content
    assert "Pattern 1" in content
    assert "Old info" in content

def test_memory_stats_and_cleanup(workspace):
    mm = MemoryManager(str(workspace))
    
    # Create old daily file
    old_date = datetime.now() - timedelta(days=40)
    old_file = mm.get_daily_memory_file(old_date)
    old_file.write_text("old data", encoding="utf-8")
    
    # Create new daily file
    new_date = datetime.now()
    new_file = mm.get_daily_memory_file(new_date)
    new_file.write_text("## [12:00] EVENT\nnew data", encoding="utf-8")
    
    mm.long_term_memory_file.write_text("data", encoding="utf-8")
    
    stats = mm.get_memory_stats()
    assert stats["daily_files"] == 2
    assert stats["long_term_memory_exists"] is True
    assert stats["total_logged_events"] == 1
    
    cleaned = mm.cleanup_old_memories(days_to_keep=30)
    assert cleaned == 1
    assert not old_file.exists()
    assert new_file.exists()

def test_global_helpers(workspace):
    import core.memory_manager
    core.memory_manager._memory_manager = None
    
    mm = initialize_memory_manager(str(workspace))
    assert get_memory_manager() == mm
    
    log_task_completion("G", "A", [], True, 1.0)
    log_daily_event("E", "D")
    
    stats = get_memory_stats()
    assert stats["daily_files"] == 1
    
    consolidate_memory()
    cleaned = cleanup_old_memories()
    assert cleaned == 0
