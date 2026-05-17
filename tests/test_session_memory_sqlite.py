import os
import sqlite3
import pytest
from core.session_memory_sqlite import SqliteSessionMemory

@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return str(ws)

def test_init_and_schema(workspace):
    cfg = {"workspace": workspace}
    db = SqliteSessionMemory(cfg)
    
    assert os.path.exists(db.db_path)
    # Check tables
    cur = db._conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in cur.fetchall()}
    assert {"sessions", "preferences", "tasks", "tool_events", "artifacts", "outcomes", "messages"}.issubset(tables)
    
    # Check session created
    cur.execute("SELECT session_id FROM sessions")
    assert cur.fetchone()[0] == db.session_id

def test_add_and_get_messages(workspace):
    db = SqliteSessionMemory({"workspace": workspace})
    
    db.add("user", "Hello")
    db.add("assistant", "Hi there")
    
    assert db.turn_count == 1
    
    msgs = db.get_messages()
    assert len(msgs) == 2
    assert msgs[0] == {"role": "user", "content": "Hello"}
    assert msgs[1] == {"role": "assistant", "content": "Hi there"}

def test_max_messages_overflow(workspace):
    db = SqliteSessionMemory({"workspace": workspace, "max_messages": 2})
    
    db.add("user", "msg1")
    db.add("assistant", "msg2")
    db.add("user", "msg3")
    
    msgs = db.get_messages()
    assert len(msgs) == 2
    assert msgs[0]["content"] == "msg2"
    assert msgs[1]["content"] == "msg3"
    
    # Check overflow file
    overflow_dir = os.path.join(workspace, "memory")
    overflow_file = os.path.join(overflow_dir, f"overflow-{db.session_id}.md")
    assert os.path.exists(overflow_file)
    with open(overflow_file, "r") as f:
        content = f.read()
        assert "msg1" in content

def test_redaction(workspace):
    db = SqliteSessionMemory({"workspace": workspace, "redact_secrets": True})
    
    # default pattern
    db.add("user", "my OPENAI_API_KEY=sk-12345 is secret")
    msgs = db.get_messages()
    assert "sk-12345" not in msgs[0]["content"]
    assert "[REDACTED]" in msgs[0]["content"]
    
    # Check disable redaction
    db_no_redact = SqliteSessionMemory({"workspace": workspace, "redact_secrets": False, "db_path": os.path.join(workspace, "db2.sqlite")})
    db_no_redact.add("user", "my OPENAI_API_KEY=sk-12345")
    assert "sk-12345" in db_no_redact.get_messages()[0]["content"]

def test_import_messages(workspace):
    db = SqliteSessionMemory({"workspace": workspace})
    msgs = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"}
    ]
    db.import_messages(msgs)
    
    loaded = db.get_messages()
    assert len(loaded) == 2
    assert loaded[0]["content"] == "hello"

def test_events_and_artifacts(workspace):
    db = SqliteSessionMemory({"workspace": workspace})
    
    db.record_tool_event("search", "query='test'", "found 2 results")
    db.record_artifact("path/to/file", "created")
    
    cur = db._conn.cursor()
    cur.execute("SELECT tool_name, observation FROM tool_events")
    event = cur.fetchone()
    assert event == ("search", "found 2 results")
    
    cur.execute("SELECT kind, action, value FROM artifacts")
    artifact = cur.fetchone()
    assert artifact == ("path", "created", "path/to/file")

def test_outcomes(workspace):
    db = SqliteSessionMemory({"workspace": workspace})
    db.set_outcome("Done", "Next")
    
    cur = db._conn.cursor()
    cur.execute("SELECT final_answer, next_steps FROM outcomes")
    assert cur.fetchone() == ("Done", "Next")

def test_tasks(workspace):
    db = SqliteSessionMemory({"workspace": workspace})
    db.start_task("t1", "Do it")
    
    cur = db._conn.cursor()
    cur.execute("SELECT status, goal FROM tasks WHERE task_id='t1'")
    assert cur.fetchone() == ("running", "Do it")
    
    db.update_task("t1", "paused")
    cur.execute("SELECT status FROM tasks WHERE task_id='t1'")
    assert cur.fetchone()[0] == "paused"
    
    db.complete_task("t1", "Done", "None", "Summary")
    cur.execute("SELECT status, final_answer FROM tasks WHERE task_id='t1'")
    assert cur.fetchone() == ("completed", "Done")

def test_preferences(workspace):
    db = SqliteSessionMemory({"workspace": workspace})
    db.set_preference("color", "blue")
    db.set_preference("font", "arial")
    
    prefs = db.get_preferences()
    assert prefs == {"color": "blue", "font": "arial"}

def test_summary(workspace):
    db = SqliteSessionMemory({"workspace": workspace})
    assert db.summary() == ""
    
    db.set_summary("This is a test session")
    assert db.summary() == "This is a test session"

def test_clear_and_close(workspace):
    db = SqliteSessionMemory({"workspace": workspace})
    db.add("user", "test")
    db.set_summary("summ")
    
    db.clear()
    assert len(db.get_messages()) == 0
    assert db.summary() == ""
    
    db.close()
    with pytest.raises(sqlite3.ProgrammingError):
        db._conn.execute("SELECT 1")
