import os
import sqlite3
import pytest
from unittest import mock

from core.audit_logger import _redact, AuditLogger
from core.session_memory_sqlite import SqliteSessionMemory

def test_audit_logger_redact_with_patterns():
    # Test that _redact uses the provided patterns
    patterns = [
        (r"(?i)(SECRET_TOKEN\s*=\s*)([^\s]+)", r"\1[MOCK_REDACTED]")
    ]
    
    text = "Here is my SECRET_TOKEN = 1234567890abcdef and some other text."
    redacted = _redact(text, patterns)
    
    assert "1234567890abcdef" not in redacted
    assert "SECRET_TOKEN = [MOCK_REDACTED]" in redacted
    assert "and some other text" in redacted

def test_audit_logger_redact_default():
    # Test that _redact falls back to its internal list if patterns=None
    text = "My Authorization: Bearer secret-token-12345678"
    redacted = _redact(text, None)
    
    assert "secret-token-12345678" not in redacted
    assert "Authorization: Bearer [REDACTED]" in redacted

@mock.patch("core.session_memory_sqlite._default_db_path")
def test_sqlite_memory_redaction(mock_db_path, tmp_path):
    # Setup mock db path
    db_file = tmp_path / "test.db"
    mock_db_path.return_value = str(db_file)
    
    cfg = {
        "workspace": str(tmp_path),
        "policy": {
            "redaction_patterns": [
                (r"(?i)(MOCK_KEY\s*=\s*)([^\s]+)", r"\1[MOCK_REDACTED]")
            ]
        }
    }
    
    memory = SqliteSessionMemory(cfg)
    
    # Test the internal _redact method
    text = "Testing MOCK_KEY=secret_value in memory."
    redacted = memory._redact(text)
    
    assert "secret_value" not in redacted
    assert "MOCK_KEY=[MOCK_REDACTED]" in redacted
    
    memory._conn.close()
