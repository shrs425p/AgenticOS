import os
import tempfile
import pytest
from kernel.checkpoint import CheckpointManager, _goal_to_task_id

def test_goal_to_task_id_normalization():
    goal1 = "  My   Super Goal  \n"
    goal2 = "my   super goal"
    assert _goal_to_task_id(goal1) == _goal_to_task_id(goal2)
    assert len(_goal_to_task_id(goal1)) == 12

def test_checkpoint_manager_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CheckpointManager(tmpdir)
        goal = "Test Checkpoint Resiliency"
        phases = [
            {"name": "Phase 1", "status": "pending", "steps": ["step 1"]},
            {"name": "Phase 2", "status": "pending", "steps": ["step 2"]}
        ]
        
        # 1. Create
        task_id = mgr.create(goal, phases)
        assert len(task_id) == 12
        
        # Check SQLite entry
        with mgr._get_connection() as conn:
            row = conn.execute("SELECT * FROM checkpoints WHERE task_id = ?", (task_id,)).fetchone()
            assert row is not None
            assert row["goal"] == goal
            assert row["status"] == "pending"
            
            p_rows = conn.execute("SELECT * FROM phases WHERE task_id = ?", (task_id,)).fetchall()
            assert len(p_rows) == 2
            assert p_rows[0]["name"] == "Phase 1"
            assert p_rows[0]["status"] == "pending"
        
        # 2. Load
        data = mgr.load(goal)
        assert data is not None
        assert data["task_id"] == task_id
        assert data["goal"] == goal
        assert len(data["phases"]) == 2
        
        # 3. Next pending phase
        next_p = mgr.next_pending_phase(task_id)
        assert next_p is not None
        assert next_p["name"] == "Phase 1"
        
        # 4. Update phase
        mgr.update_phase(task_id, "Phase 1", "complete", "Success result")
        data2 = mgr.load(goal)
        assert data2["phases"][0]["status"] == "complete"
        assert data2["phases"][0]["result"] == "Success result"
        
        next_p2 = mgr.next_pending_phase(task_id)
        assert next_p2 is not None
        assert next_p2["name"] == "Phase 2"
        
        # 5. Mark all complete
        mgr.update_phase(task_id, "Phase 2", "complete", "Done")
        next_p3 = mgr.next_pending_phase(task_id)
        assert next_p3 is None
        
        # SQLite status should be updated to complete
        with mgr._get_connection() as conn:
            row = conn.execute("SELECT status FROM checkpoints WHERE task_id = ?", (task_id,)).fetchone()
            assert row["status"] == "complete"
