import os
import sqlite3
import builtins
import time
import pytest
from unittest.mock import patch, MagicMock

from kernel.triage import RetryClassifier
from kernel.audit import infer_success

class ChaosMonkey:
    """ChaosMonkey fault injection harness.
    
    Dynamically patches standard Python and system calls to simulate:
    - SQLite database locks: raises sqlite3.OperationalError("database is locked")
    - File permissions errors: raises PermissionError on write attempts
    - LLM API timeouts/delays: raises TimeoutError or introduces sleep delay on chat calls
    """
    def __init__(self, db_locked=False, file_permission_error=False, llm_timeout=False, delay_seconds=0.0):
        self.db_locked = db_locked
        self.file_permission_error = file_permission_error
        self.llm_timeout = llm_timeout
        self.delay_seconds = delay_seconds
        self.active_patches = []

    def __enter__(self):
        # 1. SQLite locks
        if self.db_locked:
            def mock_connect(*args, **kwargs):
                raise sqlite3.OperationalError("database is locked")
            p_sql = patch("sqlite3.connect", new=mock_connect)
            p_sql.start()
            self.active_patches.append(p_sql)

        # 2. File permission errors (on write)
        if self.file_permission_error:
            real_open = builtins.open
            def mock_open(file, mode="r", *args, **kwargs):
                if any(char in mode for char in ["w", "a", "x", "+"]):
                    raise PermissionError(f"Permission denied (restricted area): {file}")
                return real_open(file, mode, *args, **kwargs)
            p_open = patch("builtins.open", new=mock_open)
            p_open.start()
            self.active_patches.append(p_open)

        # 3. LLM API timeout
        if self.llm_timeout:
            from kernel import models
            
            def make_mock_chat(orig_chat):
                def mock_chat(self_client, messages, system=""):
                    if self.delay_seconds > 0:
                        time.sleep(self.delay_seconds)
                    raise TimeoutError("LLM API request timed out")
                return mock_chat

            for attr in dir(models):
                val = getattr(models, attr)
                if isinstance(val, type) and hasattr(val, "chat") and attr != "FallbackRouter":
                    p_chat = patch.object(val, "chat", new=make_mock_chat(getattr(val, "chat")))
                    p_chat.start()
                    self.active_patches.append(p_chat)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for p in reversed(self.active_patches):
            p.stop()


@pytest.fixture
def chaos_monkey():
    def _create(db_locked=False, file_permission_error=False, llm_timeout=False, delay_seconds=0.0):
        return ChaosMonkey(
            db_locked=db_locked,
            file_permission_error=file_permission_error,
            llm_timeout=llm_timeout,
            delay_seconds=delay_seconds
        )
    return _create


def test_chaos_monkey_db_locked(chaos_monkey):
    """Verify that sqlite3.connect raises sqlite3.OperationalError when db_locked is True."""
    with chaos_monkey(db_locked=True):
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            sqlite3.connect("test.db")
        assert "database is locked" in str(exc_info.value)
    
    # Verify it restores successfully
    conn = sqlite3.connect(":memory:")
    conn.close()


def test_chaos_monkey_file_permission(chaos_monkey, tmp_path):
    """Verify that writing fails under file_permission_error while reading succeeds."""
    test_file = tmp_path / "test.txt"
    # Should write successfully before chaos monkey
    with open(test_file, "w") as f:
        f.write("hello")
    
    # Under chaos monkey, write should fail
    with chaos_monkey(file_permission_error=True):
        with pytest.raises(PermissionError) as exc_info:
            with open(test_file, "w") as f:
                f.write("world")
        assert "Permission denied" in str(exc_info.value)
        
        # Read should still succeed
        with open(test_file, "r") as f:
            assert f.read() == "hello"
    
    # Verify it restores successfully
    with open(test_file, "w") as f:
        f.write("restored")
    with open(test_file, "r") as f:
        assert f.read() == "restored"


def test_chaos_monkey_llm_timeout(chaos_monkey):
    """Verify that llm_timeout triggers TimeoutError and delay_seconds slows it down."""
    from kernel.models import OllamaClient
    client = OllamaClient({
        "ollama": {
            "base_url": "http://localhost:11434",
            "default_model": "test-model",
            "timeout": 30.0,
            "temperature": 0.7
        },
        "agent": {
            "stream": True
        }
    })
    
    with chaos_monkey(llm_timeout=True, delay_seconds=0.05):
        start = time.time()
        with pytest.raises(TimeoutError) as exc_info:
            client.chat([{"role": "user", "content": "hi"}])
        elapsed = time.time() - start
        assert "timed out" in str(exc_info.value)
        assert elapsed >= 0.04


def test_orchestrator_recovery_and_retry_classification():
    """Verify that RetryClassifier correctly identifies SQLite locks and timeouts as retryable."""
    classifier = RetryClassifier()
    
    # SQLite lock
    locked_decision = classifier.classify("Error: database is locked", exit_code=None)
    assert locked_decision.action == "retry"
    assert "locked" in locked_decision.reason
    assert locked_decision.max_retries == 3

    # LLM/Network Timeout
    timeout_decision = classifier.classify("Error: Connection timeout occurred", exit_code=None)
    assert timeout_decision.action == "retry"
    assert "timeout" in timeout_decision.reason
    assert timeout_decision.max_retries == 3

    # File permission (permanent)
    perm_decision = classifier.classify("Permission denied for writing to output.txt", exit_code=None)
    assert perm_decision.action == "abandon"
    assert "permission denied" in perm_decision.reason
    assert perm_decision.max_retries == 0


def test_agent_tool_retry_simulation():
    """Simulate Agent run-loop tool calling retry behavior on transient failures."""
    from kernel.agent import Agent
    
    cfg = {
        "agent": {"provider": "ollama", "workspace": "workspace", "max_iterations": 2},
        "prompts": {},
        "security": {"enable_zone_guard": False}
    }
    
    # Setup partial mock Agent
    agent = Agent.__new__(Agent)
    agent.cfg = cfg
    agent.retry_classifier = RetryClassifier()
    agent.stall_monitor = MagicMock()
    agent.ops = MagicMock()
    
    # Mock ops.call to fail first with SQLite lock and then succeed
    call_sequence = [
        "Error: database is locked",
        "Success: wrote record"
    ]
    agent.ops.call.side_effect = call_sequence
    
    # Replicate the orchestrator's run-loop logic for tool retrying
    tool_name = "sqlitequery"
    args = {"query": "INSERT INTO users VALUES (1)"}
    
    started = time.time()
    obs = agent.ops.call(tool_name, args)
    ended = time.time()
    elapsed = ended - started
    
    obs_text = str(obs or "")
    ok = infer_success(obs_text)
    
    # It failed, check if retry happens
    if not ok:
        decision = agent.retry_classifier.classify(obs_text, None)
        if decision.action == "retry":
            retries = 0
            max_retries = decision.max_retries
            while retries < max_retries and not ok:
                started = time.time()
                obs = agent.ops.call(tool_name, args)
                ended = time.time()
                elapsed = ended - started
                obs_text = str(obs or "")
                ok = infer_success(obs_text)
                retries += 1

    # Verify that the tool was called twice (first fail, second succeed)
    assert agent.ops.call.call_count == 2
    assert ok is True
    assert "Success" in obs_text
