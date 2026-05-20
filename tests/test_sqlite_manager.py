"""Unit tests for the SQLite manager plugin tools."""

import os
import json
import pytest
import sqlite3
import tempfile

from tools.plugins.sqlite_manager import (
    sqlite_list_tables,
    sqlite_get_schema,
    sqlite_query,
    sqlite_execute,
)


@pytest.fixture
def test_db():
    """Fixture to create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    
    # Initialize schema
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            content TEXT
        )
    ''')
    cursor.execute('''
        INSERT INTO users (username, email) VALUES
        ('alice', 'alice@example.com'),
        ('bob', 'bob@example.com')
    ''')
    conn.commit()
    conn.close()
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


def test_sqlite_list_tables(test_db):
    result = sqlite_list_tables(test_db)
    assert "users" in result
    assert "posts" in result


def test_sqlite_list_tables_not_found():
    result = sqlite_list_tables("nonexistent_path.db")
    assert "Error: Database file not found" in result


def test_sqlite_get_schema(test_db):
    result = sqlite_get_schema(test_db, "users")
    assert "Table: users" in result
    assert "username" in result
    assert "email" in result


def test_sqlite_get_schema_invalid_table(test_db):
    result = sqlite_get_schema(test_db, "invalid_table")
    assert "does not exist or has no columns" in result


def test_sqlite_query_select(test_db):
    result = sqlite_query(test_db, "SELECT * FROM users ORDER BY username ASC")
    
    # Should be valid JSON
    data = json.loads(result)
    assert len(data) == 2
    assert data[0]["username"] == "alice"
    assert data[1]["username"] == "bob"


def test_sqlite_query_limit(test_db):
    result = sqlite_query(test_db, "SELECT * FROM users", max_rows=1)
    data = json.loads(result)
    assert len(data) == 1


def test_sqlite_query_invalid_statement(test_db):
    # Should prevent INSERT via query
    result = sqlite_query(test_db, "INSERT INTO users (username) VALUES ('eve')")
    assert "only supports SELECT or PRAGMA" in result


def test_sqlite_execute_insert(test_db):
    result = sqlite_execute(test_db, "INSERT INTO users (username, email) VALUES ('eve', 'eve@example.com')")
    assert "Rows affected: 1" in result
    
    # Verify insertion
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 3


def test_sqlite_execute_destructive_protection(test_db):
    # Should block unconfirmed destructive query
    result = sqlite_execute(test_db, "DROP TABLE users;")
    assert "appears destructive" in result
    assert "confirm_destructive=True" in result
    
    # Verify table still exists
    tables = sqlite_list_tables(test_db)
    assert "users" in tables


def test_sqlite_execute_destructive_confirmed(test_db):
    # Should allow if confirmed
    result = sqlite_execute(test_db, "DROP TABLE users;", confirm_destructive=True)
    assert "Rows affected" in result
    
    # Verify table is gone
    tables = sqlite_list_tables(test_db)
    assert "users" not in tables
