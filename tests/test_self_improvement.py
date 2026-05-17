import os
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from core.self_improvement import SelfImprovementDaemon, run_dream_cycle

@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws

def test_should_dream(workspace):
    daemon = SelfImprovementDaemon(str(workspace))
    
    # Force always true
    assert daemon.should_dream(force=True) is True
    
    # If no marker, should dream
    assert daemon.should_dream() is True
    
    # If daily log exists, should NOT dream
    today = datetime.now().strftime("%Y-%m-%d")
    daily_log = workspace / "daily_logs" / f"dream_log_{today}.md"
    daily_log.parent.mkdir(parents=True, exist_ok=True)
    daily_log.touch()
    assert daemon.should_dream() is False
    daily_log.unlink()
    
    # If marker is very recent, should NOT dream
    daemon.dream_marker_file.parent.mkdir(parents=True, exist_ok=True)
    daemon.dream_marker_file.write_text(datetime.now().isoformat())
    assert daemon.should_dream() is False
    
    # If marker is old, should dream
    old_time = datetime.now() - timedelta(hours=10)
    daemon.dream_marker_file.write_text(old_time.isoformat())
    assert daemon.should_dream() is True

def test_dream_cycle_skipped(workspace):
    daemon = SelfImprovementDaemon(str(workspace))
    daemon.should_dream = MagicMock(return_value=False)
    assert "skipped" in daemon.dream()

def test_dream_cycle_with_llm(workspace):
    client = MagicMock()
    client.chat.return_value = "- Avoid writing bugs\n- Drink water\n- Use pytest"
    
    daemon = SelfImprovementDaemon(str(workspace), llm_client=client)
    
    # Create fake tracking history
    tracking_file = daemon.memory_dir / "task_tracking.json"
    daemon.memory_dir.mkdir(parents=True, exist_ok=True)
    tracking_file.write_text(json.dumps({
        "completed_tasks": [
            {"goal": "make bug", "success": False, "duration": 10},
            {"goal": "make coffee", "success": True, "duration": 300, "tools_used": ["cup"]},
        ]
    }))
    
    res = daemon.dream(force=True)
    
    assert "completed" in res
    assert "MEMORY.md" in res
    
    memory_content = daemon.memory_file.read_text(encoding="utf-8")
    assert "Avoid writing bugs" in memory_content
    assert "Drink water" in memory_content
    
    # Check daily log
    today = datetime.now().strftime("%Y-%m-%d")
    daily_log = workspace / "daily_logs" / f"dream_log_{today}.md"
    daily_log_content = daily_log.read_text(encoding="utf-8")
    assert "Avoid writing bugs" in daily_log_content

def test_dream_cycle_fallback(workspace):
    # No LLM client => fallback heuristic
    daemon = SelfImprovementDaemon(str(workspace))
    
    tracking_file = daemon.memory_dir / "task_tracking.json"
    daemon.memory_dir.mkdir(parents=True, exist_ok=True)
    tracking_file.write_text(json.dumps({
        "completed_tasks": [
            {"goal": "make bug", "success": False, "duration": 10},
            {"goal": "make coffee", "success": True, "duration": 300, "tools_used": ["cup", "cup", "spoon"]},
        ]
    }))
    
    res = daemon.dream(force=True)
    assert "completed" in res
    
    memory_content = daemon.memory_file.read_text(encoding="utf-8")
    assert "failures" in memory_content.lower() or "slow" in memory_content.lower()

def test_offline_fallback_scan(workspace, monkeypatch):
    daemon = SelfImprovementDaemon(str(workspace))
    
    # Mock Path to point inside our workspace for testing offline fallback
    class MockPath:
        def __init__(self, p):
            self.p = p
        def exists(self): return True
        def is_dir(self): return True
        def rglob(self, pat):
            if pat == "*.py":
                fake_py = workspace / "fake_plugin.py"
                fake_py.write_text("def no_docstring():\n    pass")
                return [fake_py]
            elif pat == "*.log":
                fake_log = workspace / "fake.log"
                fake_log.write_text("INFO ok\nERROR bad thing happened\n")
                return [fake_log]
            return []
            
    monkeypatch.setattr("core.self_improvement.Path", MockPath)
    
    findings = daemon._offline_fallback_scan()
    assert any("missing docstring" in f for f in findings)
    assert any("ERROR bad thing happened" in f for f in findings)

def test_run_dream_cycle(workspace):
    res = run_dream_cycle(str(workspace), force=True)
    assert "Dream cycle" in res
