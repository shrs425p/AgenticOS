import pytest
import sqlite3
import datetime
from pathlib import Path
from tools.plugins.session_summary import generate_session_summary

@pytest.fixture
def mock_dirs(tmp_path, monkeypatch):
    """Fixture to create mock data and workspace directories."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)

    workspace_dir = tmp_path / "workspace" / "daily_logs"
    workspace_dir.mkdir(parents=True)

    original_path = Path

    class MockPath(type(Path())):
        def __new__(cls, *args, **kwargs):
            if args and str(args[0]) == "data":
                return original_path(str(data_dir))
            elif args and str(args[0]) == "workspace/daily_logs":
                return original_path(str(workspace_dir))
            return original_path(*args, **kwargs)

    monkeypatch.setattr("tools.plugins.session_summary.Path", MockPath)

    return data_dir, workspace_dir

def setup_sqlite_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE tool_events (tool_name TEXT)")
    cursor.execute("INSERT INTO tool_events VALUES ('search'), ('search'), ('read_file')")

    cursor.execute("CREATE TABLE messages (content TEXT)")
    cursor.execute("INSERT INTO messages VALUES ('an error occurred'), ('warning: slow'), ('all good')")

    cursor.execute("CREATE TABLE tasks (task_id TEXT, created_at TEXT, updated_at TEXT)")
    now = datetime.datetime.now()
    t1_start = now.isoformat()
    t1_end = (now + datetime.timedelta(seconds=10)).isoformat()
    t2_start = now.isoformat()
    t2_end = (now + datetime.timedelta(seconds=50)).isoformat()

    cursor.execute("INSERT INTO tasks VALUES ('task1', ?, ?), ('task2', ?, ?)",
                   (t1_start, t1_end, t2_start, t2_end))

    conn.commit()
    conn.close()

def test_generate_session_summary_normal_data(mock_dirs):
    data_dir, workspace_dir = mock_dirs

    # Create evaluation_output.txt
    eval_file = data_dir / "evaluation_output.txt"
    eval_file.write_text("This is an Error. Also a Warning. Another error.")

    # Create SQLite DB
    db_file = data_dir / "memory.sqlite3"
    setup_sqlite_db(db_file)

    res = generate_session_summary()
    assert "Summary written to" in res

    today = datetime.date.today().isoformat()
    summary_file = workspace_dir / f"session_summary_{today}.md"
    assert summary_file.exists()

    content = summary_file.read_text()
    assert "- **Total Tools Called**: 3" in content
    assert "- **Unique Tools Used**: 2" in content
    assert "- **Errors Logged**: 3" in content # 2 from eval, 1 from db
    assert "- **Warnings Logged**: 2" in content # 1 from eval, 1 from db
    assert "- **Longest Running Task**: task2" in content
    assert "(Duration: 50.0s)" in content

def test_generate_session_summary_both_missing(mock_dirs):
    data_dir, workspace_dir = mock_dirs
    res = generate_session_summary()
    assert res == "no session data found"

    today = datetime.date.today().isoformat()
    summary_file = workspace_dir / f"session_summary_{today}.md"
    assert summary_file.exists()
    assert summary_file.read_text() == "no session data found\n"

def test_generate_session_summary_missing_eval(mock_dirs):
    data_dir, workspace_dir = mock_dirs
    db_file = data_dir / "memory.sqlite3"
    setup_sqlite_db(db_file)

    res = generate_session_summary()
    assert "Summary written to" in res

    today = datetime.date.today().isoformat()
    summary_file = workspace_dir / f"session_summary_{today}.md"
    content = summary_file.read_text()
    assert "- **Errors Logged**: 1" in content # Only from DB

def test_generate_session_summary_missing_sqlite(mock_dirs):
    data_dir, workspace_dir = mock_dirs
    eval_file = data_dir / "evaluation_output.txt"
    eval_file.write_text("Warning")

    res = generate_session_summary()
    assert "Summary written to" in res

    today = datetime.date.today().isoformat()
    summary_file = workspace_dir / f"session_summary_{today}.md"
    content = summary_file.read_text()
    assert "- **Warnings Logged**: 1" in content
    assert "- **Total Tools Called**: 0" in content

def test_generate_session_summary_empty_files(mock_dirs):
    data_dir, workspace_dir = mock_dirs
    eval_file = data_dir / "evaluation_output.txt"
    eval_file.write_text("")

    db_file = data_dir / "memory.sqlite3"
    conn = sqlite3.connect(db_file)
    # Empty DB with no tables
    conn.close()

    res = generate_session_summary()
    assert "Summary written to" in res

    today = datetime.date.today().isoformat()
    summary_file = workspace_dir / f"session_summary_{today}.md"
    content = summary_file.read_text()
    assert "- **Total Tools Called**: 0" in content
    assert "- **Errors Logged**: 0" in content
