import os
import json
import hashlib
import sqlite3
import contextlib
from datetime import datetime
from typing import Optional, List, Dict, Any

def _goal_to_task_id(goal: str) -> str:
    """Normalize goal and compute stable 12-char SHA256 identifier."""
    normalized = goal.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]

class CheckpointManager:
    """Manager for multi-session linear phase checkpoints with JSON/SQLite dual persistence."""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.checkpoints_dir = os.path.join(workspace_root, ".checkpoints")
        os.makedirs(self.checkpoints_dir, exist_ok=True)
        self.sqlite_path = os.path.join(self.checkpoints_dir, "checkpoints.sqlite3")
        self._init_sqlite()

    def _get_connection(self):
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return contextlib.closing(conn)

    def _init_sqlite(self):
        """Initialize secondary index tables in SQLite."""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS checkpoints (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS phases (
                    task_id TEXT,
                    name TEXT,
                    status TEXT,
                    result TEXT,
                    PRIMARY KEY(task_id, name)
                )
            ''')
            conn.commit()

    def create(self, goal: str, phases: List[Dict[str, Any]]) -> str:
        """Create a new task checkpoint, insert into SQLite, and save JSON."""
        task_id = _goal_to_task_id(goal)
        now = datetime.utcnow().isoformat()
        
        # Prepare JSON structure
        checkpoint_data = {
            "task_id": task_id,
            "goal": goal,
            "phases": [
                {
                    "name": p.get("name", ""),
                    "status": p.get("status", "pending"),
                    "steps": p.get("steps", []),
                    "result": p.get("result", None)
                } for p in phases
            ],
            "created_at": now,
            "updated_at": now
        }
        
        # Save JSON file
        json_path = os.path.join(self.checkpoints_dir, f"{task_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
        # Save to SQLite
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO checkpoints (task_id, goal, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_id, goal, "pending", now, now))
            
            for p in phases:
                conn.execute('''
                    INSERT OR REPLACE INTO phases (task_id, name, status, result)
                    VALUES (?, ?, ?, ?)
                ''', (task_id, p.get("name"), p.get("status", "pending"), p.get("result")))
            conn.commit()
            
        return task_id

    def load(self, goal: str) -> Optional[Dict[str, Any]]:
        """Load checkpoint by goal string from JSON."""
        task_id = _goal_to_task_id(goal)
        json_path = os.path.join(self.checkpoints_dir, f"{task_id}.json")
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def update_phase(self, task_id: str, phase_name: str, status: str, result: Optional[str] = None) -> None:
        """Update status of a specific phase in JSON and SQLite DB."""
        now = datetime.utcnow().isoformat()
        json_path = os.path.join(self.checkpoints_dir, f"{task_id}.json")
        
        # Update JSON file
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                updated = False
                for p in data.get("phases", []):
                    if p.get("name") == phase_name:
                        p["status"] = status
                        if result is not None:
                            p["result"] = result
                        updated = True
                        break
                
                if updated:
                    data["updated_at"] = now
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
                
        # Update SQLite
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO phases (task_id, name, status, result)
                VALUES (?, ?, ?, ?)
            ''', (task_id, phase_name, status, result))
            
            # If all phases are complete, mark the checkpoint status as complete
            cursor = conn.execute('SELECT status FROM phases WHERE task_id = ?', (task_id,))
            rows = cursor.fetchall()
            if rows:
                all_complete = all(row['status'] == 'complete' for row in rows)
                chk_status = 'complete' if all_complete else 'running'
                conn.execute('''
                    UPDATE checkpoints 
                    SET status = ?, updated_at = ?
                    WHERE task_id = ?
                ''', (chk_status, now, task_id))
            conn.commit()

    def next_pending_phase(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Return the first phase where status != 'complete'."""
        json_path = os.path.join(self.checkpoints_dir, f"{task_id}.json")
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for p in data.get("phases", []):
                if p.get("status") != "complete":
                    return p
        except Exception:
            pass
        return None
