from core.memory_manager import MemoryManager

def test_memory_manager_init(tmp_path):
    manager = MemoryManager(workspace_root=str(tmp_path))
    assert manager.memory_dir.exists()
    assert manager.commitments == []

def test_commitments(tmp_path):
    manager = MemoryManager(workspace_root=str(tmp_path))
    
    # Add a commitment
    manager.register_commitment("Remember this", "2026-12-31")
    assert len(manager.commitments) == 1
    assert manager.commitments[0]["text"] == "Remember this"
    
    # Ensure it's saved to disk
    assert manager.commitments_file.exists()
    
    # Complete the commitment
    cid = manager.commitments[0]["id"]
    manager.complete_commitment(cid)
    assert manager.commitments[0]["status"] == "completed"

def test_log_interaction(tmp_path):
    manager = MemoryManager(workspace_root=str(tmp_path))
    manager.log_daily_event("USER", "Hello there")
    manager.log_daily_event("AGENT", "Hi!")
    
    # It creates a file formatted like memory-YYYY-MM-DD.md
    files = list(manager.daily_memory_dir.glob("memory-*.md"))
    assert len(files) == 1
    
    content = files[0].read_text(encoding="utf-8")
    assert "USER" in content
    assert "Hello there" in content
    assert "AGENT" in content
    assert "Hi!" in content
