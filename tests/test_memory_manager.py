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
    mm.log_task_completion("open test document", "answer1", ["tool1"], True, 10.5, {"extra": "info"})
    
    tracking_file = mm.memory_dir / "task_tracking.json"
    assert tracking_file.exists()
    
    data = json.loads(tracking_file.read_text(encoding="utf-8"))
    assert len(data["completed_tasks"]) == 1
    assert data["completed_tasks"][0]["goal"] == "open test document"

def test_consolidation_check(workspace):
    mm = MemoryManager(str(workspace))
    mm.memory_consolidation_threshold = 2
    
    try:
        mm.log_task_completion("open test document", "ans", [], True, 1)
    except Exception:
        pass
    mm.log_task_completion("kill brave process", "ans", [], False, 1)
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
    
    log_task_completion("open test document", "A", [], True, 1.0)
    log_daily_event("E", "D")
    
    stats = get_memory_stats()
    assert stats["daily_files"] == 1
    
    consolidate_memory()
    cleaned = cleanup_old_memories()
    assert cleaned == 0

def test_consolidate_long_term_memory_manual(workspace):
    from core.memory_manager import MemoryManager
    import json
    mm = MemoryManager(str(workspace))
    mm.log_task_completion("execute test goal", "ans", [], True, 1.0)
    mm.consolidate_long_term_memory()
    tracking_file = mm.memory_dir / "task_tracking.json"
    data = json.loads(tracking_file.read_text(encoding="utf-8"))
    assert data.get("last_consolidation") is not None

def test_consolidate_long_term_memory_llm_json_fallback(workspace):
    from unittest.mock import MagicMock
    from core.memory_manager import MemoryManager
    client = MagicMock()
    client.chat.return_value = "invalid json {[[[}"
    mm = MemoryManager(str(workspace), llm_client=client)
    tasks = [{"goal": "G1", "success": True, "duration": 5, "tools_used": ["T1"], "timestamp": "2024-01-01T00:00:00"}]
    insights = mm._generate_insights_from_tasks(tasks)
    assert insights["success_rate"] == 1.0

def test_get_relevant_context_exceptions(workspace):
    from unittest.mock import patch
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    with patch("builtins.open", side_effect=Exception("Read error")):
        ctx = mm.get_relevant_context("query")
        assert ctx == ""

def test_log_daily_event_exceptions(workspace):
    from unittest.mock import patch
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    with patch("builtins.open", side_effect=Exception("Write error")):
        try:
            mm.log_daily_event("E", "D")
        except Exception:
            pass

def test_log_task_completion_exceptions(workspace):
    from unittest.mock import patch
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    with patch("builtins.open", side_effect=Exception("Write error")):
        try:
            mm.log_task_completion("open test document", "A", [], True, 1.0)
        except Exception:
            pass

def test_consolidate_memory_no_files(workspace):
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    mm.consolidate_long_term_memory()

def test_update_long_term_memory_no_header(workspace):
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    mm.long_term_memory_file.write_text("just some\nrandom\ntext", encoding="utf-8")
    mm._update_long_term_memory({}, [])
    content = mm.long_term_memory_file.read_text()
    assert "random" in content

def test_get_memory_stats_exceptions(workspace):
    from unittest.mock import patch
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    mm.log_daily_event("E", "D")
    with patch("builtins.open", side_effect=Exception("Read error")):
        stats = mm.get_memory_stats()
        assert stats["daily_files"] == 1
        assert stats["total_logged_events"] == 0

def test_consolidate_long_term_memory_error_llm(workspace):
    from unittest.mock import MagicMock
    from core.memory_manager import MemoryManager
    client = MagicMock()
    client.chat.side_effect = Exception("LLM Error")
    mm = MemoryManager(str(workspace), llm_client=client)
    tasks = [{"goal": "G1", "success": True, "duration": 5, "tools_used": ["T1"], "timestamp": "2024-01-01T00:00:00"}]
    insights = mm._generate_insights_from_tasks(tasks)
    assert insights["success_rate"] == 1.0

def test_memory_manager_missing_tracking_file(workspace):
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    tracking_file = mm.memory_dir / "task_tracking.json"
    if tracking_file.exists():
        tracking_file.unlink()
    # Log task creates the file
    try:
        mm.log_task_completion("open test document", "ans", [], True, 1)
    except Exception:
        pass
    assert tracking_file.exists()

def test_cleanup_old_memories_no_dir(tmp_path):
    from core.memory_manager import MemoryManager
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    mm = MemoryManager(str(ws))
    # Remove dir to hit the exception
    import shutil
    try:
        shutil.rmtree(str(mm.memory_dir))
    except Exception:
        pass
    assert mm.cleanup_old_memories() == 0

def test_consolidate_check_exception(workspace):
    from unittest.mock import patch
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    # Make consolidation threshold very low to trigger it
    mm.memory_consolidation_threshold = 0
    # Override log_daily_event to throw an exception but only when called from check_consolidation
    try:
        mm.log_task_completion("open test document", "ans", [], True, 1)
    except Exception:
        pass

    # We want an exception in _check_consolidation_needed
    # We can mock consolidate_long_term_memory to raise
    with patch.object(mm, "consolidate_long_term_memory", side_effect=Exception("Consolidation error")):
        mm._check_consolidation_needed() # should catch exception and pass

def test_consolidate_check_load_exception(workspace):
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    mm.memory_consolidation_threshold = 0
    # Create invalid tracking json
    tracking_file = mm.memory_dir / "task_tracking.json"
    tracking_file.write_text("invalid json", encoding="utf-8")

    # Should catch JSONDecodeError internally or just create new
    try:
        mm.log_task_completion("open test document", "ans", [], True, 1)
    except Exception:
        pass

def test_long_term_memory_update_no_insights(workspace):
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    mm._update_long_term_memory(None, [])
    assert mm.long_term_memory_file.exists()

def test_long_term_memory_update_missing_insights_keys(workspace):
    from core.memory_manager import MemoryManager
    mm = MemoryManager(str(workspace))
    mm._update_long_term_memory({"success_rate": 0.5}, [{"success": False}])
    assert mm.long_term_memory_file.exists()

def test_cleanup_old_memories_exception(tmp_path):
    from core.memory_manager import MemoryManager
    # This tests the 'except Exception:' inside the glob loop
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    mm = MemoryManager(str(ws))
    # A memory file with wrong date format
    bad_file = mm.memory_dir / "memory-not-a-date.md"
    bad_file.write_text("test")
    mm.cleanup_old_memories()
    assert bad_file.exists()

def test_is_meaningful_task():
    from core.memory_manager import is_meaningful_task
    
    # Meaningful tasks
    assert is_meaningful_task("open session memory file") is True
    assert is_meaningful_task("what is current RAM speed (MHz)") is True
    assert is_meaningful_task("play tu chahiye on spotify") is True
    assert is_meaningful_task("kill brave process") is True
    
    # Nonsense / trivial tasks
    assert is_meaningful_task("hey") is False
    assert is_meaningful_task("hello") is False
    assert is_meaningful_task("yo") is False
    assert is_meaningful_task("wtf") is False
    assert is_meaningful_task("wtf...") is False
    assert is_meaningful_task("continue") is False
    assert is_meaningful_task("more") is False
    assert is_meaningful_task("u") is False
    assert is_meaningful_task("?") is False
    assert is_meaningful_task(None) is False
    assert is_meaningful_task("") is False

    # Short conversational / contextual fluff
    assert is_meaningful_task("parts names") is False
    assert is_meaningful_task("in inr") is False
    assert is_meaningful_task("ram price") is False
    assert is_meaningful_task("what else") is False
    assert is_meaningful_task("ddr5 right?") is False
    assert is_meaningful_task("its not current month or year") is False

    # Meaningful short two-word commands
    assert is_meaningful_task("open yt") is True
    assert is_meaningful_task("kill brave") is True
    assert is_meaningful_task("sys info") is True


def test_clean_historical_memory(workspace):
    from core.memory_manager import MemoryManager
    import json
    
    # 1. Create dummy files with both meaningful and nonsense entries
    memory_md_content = """# AgenticOs Long-Term Memory

Curated knowledge, insights, and learned patterns from agent experiences.

## ▪ SAVE — Memory Consolidation - 2026-05-22 17:33:20

**Period:** 2026-05-22T17:26:49 to 2026-05-22T17:33:06
**Tasks Processed:** 10
**Success Rate:** 100.0%

**Notable Recent Tasks:**
1. ✓ parts names...
2. ✓ open yt...
3. ✓ ram price...
4. ✓ kill brave...
5. ✓ hey...

---
"""
    
    task_tracking_content = {
        "completed_tasks": [
            {"goal": "parts names", "success": True},
            {"goal": "open yt", "success": True},
            {"goal": "ram price", "success": True},
            {"goal": "kill brave", "success": True},
            {"goal": "hey", "success": True}
        ]
    }
    
    daily_log_content = """## [17:05:08] TASK_COMPLETION
**Goal:** parts names

**Result:** SUCCESS
---
## [17:05:48] TASK_COMPLETION
**Goal:** open yt

**Result:** SUCCESS
---
## [17:06:14] TASK_COMPLETION
**Goal:** ram price

**Result:** SUCCESS
---
"""
    
    # Write dummy files to workspace
    long_term_file = workspace / "MEMORY.md"
    long_term_file.write_text(memory_md_content, encoding="utf-8")
    
    memory_dir = workspace / "memory"
    memory_dir.mkdir(exist_ok=True)
    
    tracking_file = memory_dir / "task_tracking.json"
    with open(tracking_file, "w", encoding="utf-8") as f:
        json.dump(task_tracking_content, f)
        
    daily_file = memory_dir / "memory-2026-05-22.md"
    daily_file.write_text(daily_log_content, encoding="utf-8")
    
    # 2. Initialize MemoryManager (which triggers clean_historical_memory automatically)
    MemoryManager(str(workspace))
    
    # 3. Verify clean MEMORY.md
    cleaned_md = long_term_file.read_text(encoding="utf-8")
    assert "parts names" not in cleaned_md
    assert "ram price" not in cleaned_md
    assert "hey" not in cleaned_md
    assert "1. ✓ open yt..." in cleaned_md
    assert "2. ✓ kill brave..." in cleaned_md
    # Renumbering checks
    assert "3. ✓" not in cleaned_md
    
    # 4. Verify clean task_tracking.json
    with open(tracking_file, "r", encoding="utf-8") as f:
        cleaned_tracking = json.load(f)
    goals = [t["goal"] for t in cleaned_tracking["completed_tasks"]]
    assert "open yt" in goals
    assert "kill brave" in goals
    assert "parts names" not in goals
    assert "ram price" not in goals
    assert "hey" not in goals
    
    # 5. Verify clean daily logs
    cleaned_daily = daily_file.read_text(encoding="utf-8")
    assert "parts names" not in cleaned_daily
    assert "ram price" not in cleaned_daily
    assert "open yt" in cleaned_daily



