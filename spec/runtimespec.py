import os
import pytest
from unittest.mock import MagicMock, patch
from kernel.cli import Agent

@pytest.fixture
def mock_cfg(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "tasks").mkdir()
    cfg = {
        "agent": {
            "provider": "ollama",
            "workspace": str(workspace),
            "max_iterations": 5,
            "verbose_thinking": True,
            "auto_confirm": True,
            "hot_reload": False,
            "enable_cov": False,
            "fallback_providers": ["gemini"]
        },
        "memory": {
            "sqlite_db_path": str(workspace / "db.sqlite3")
        },
        "heuristics": {
            "session_id_format": "%Y%m%d_%H%M%S",
            "direct_response_max_chars": 6000,
            "direct_response_max_words": 900,
            "hot_reload_throttle": 0.0,
            "max_dots_in_response": 50
        },
        "performance": {
            "max_context_messages": 40
        },
        "autonomy": {
            "autopilot": False,
            "task_tracking": True
        },
        "logging": {
            "audit_enabled": False
        },
        "prompts": {
            "nudges": {
                "repetition": "Alternative strategy nudge",
                "empty_response": "Empty response nudge",
                "format_error": "Format error nudge"
            }
        }
    }
    return cfg

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_agent_init(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_init"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    agent = Agent(mock_cfg)
    
    assert agent.cfg == mock_cfg
    assert agent.max_iter == 5
    assert agent.verbose is True
    assert agent.confirm is True
    assert agent.hot_reload_enabled is False
    assert agent.workspace == os.path.abspath(mock_cfg["agent"]["workspace"])
    
    # Check that template files are created
    for name in ["AGENTS.md", "MEMORY.md", "USERINFO.md"]:
        path = os.path.join(agent.workspace, name)
        assert os.path.exists(path)

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_agent_reload_disabled(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_reload"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    agent = Agent(mock_cfg)
    agent.check_reload()  # Should return immediately because hot_reload is False

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_agent_reload_enabled(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_reload_enabled"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    mock_cfg["agent"]["hot_reload"] = True
    
    with patch("kernel.cli.Agent._get_mtimes", return_value={"file1.py": 123.4}):
        agent = Agent(mock_cfg)
        assert agent.hot_reload_enabled is True
        assert agent.mtimes == {"file1.py": 123.4}
        
        # Test reload check with no changes
        agent._last_reload_check = 0  # Force check
        agent.check_reload()
        
        # Test reload check with changes
        with patch("kernel.cli.Agent._reload_everything") as mock_reload:
            agent._last_reload_check = 0  # Force check
            with patch("kernel.cli.Agent._get_mtimes", return_value={"file1.py": 125.0}):
                agent.check_reload()
                mock_reload.assert_called_once()

def test_get_mtimes_uses_configured_excluded_dirs(tmp_path):
    root = tmp_path
    keep_dir = root / "kernel"
    skip_dir = root / "generated"
    keep_dir.mkdir()
    skip_dir.mkdir()
    (keep_dir / "kept.py").write_text("print('kept')", encoding="utf-8")
    (skip_dir / "ignored.py").write_text("print('ignored')", encoding="utf-8")

    agent = Agent.__new__(Agent)
    agent.cfg = {
        "hot_reload": {
            "tracked_dirs": ["kernel", "generated"],
            "excluded_dirs": ["generated"],
        }
    }

    with patch("kernel.cli.BASE_DIR", str(root)):
        mtimes = agent._get_mtimes()

    assert os.path.join("kernel", "kept.py") in mtimes
    assert os.path.join("generated", "ignored.py") not in mtimes

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_verify_action(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_verify"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    agent = Agent(mock_cfg)
    
    # 1. Tool not in registry
    agent.ops.registry = {}
    ok, err = agent.verify_action("nonexistent_tool", {}, "some context")
    assert not ok
    assert "not in the registry" in err
    
    # 2. Tool exists, verification returns OK
    agent.ops.registry = {"my_tool": MagicMock()}
    agent.client.chat = MagicMock(return_value="OK")
    ok, err = agent.verify_action("my_tool", {}, "some context")
    assert ok
    assert err == "OK"
    
    # 3. Tool exists, verification returns REJECT
    agent.client.chat = MagicMock(return_value="REJECT: Loop detected")
    ok, err = agent.verify_action("my_tool", {}, "some context")
    assert not ok
    assert err == "Loop detected"

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_is_direct_response(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_is_direct"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    agent = Agent(mock_cfg)
    
    # Direct answer ending in question
    assert agent._is_direct_response("hello", "How can I help you?")
    
    # Final answer
    assert agent._is_direct_response("hello", "FINAL ANSWER: Done")
    
    # Contains control markers -> not direct response
    assert not agent._is_direct_response("hello", "PLAN: step 1\nACTION: run")

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_agent_run_direct_response(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_direct"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    agent = Agent(mock_cfg)
    
    # Mock SqliteSessionMemory messages & preferences
    agent.memory.turn_count = 0
    agent.memory.list_preferences = MagicMock(return_value={"pref1": "val1"})
    agent.memory.get_messages = MagicMock(return_value=[{"role": "user", "content": "hi"}])
    
    # Mock ContextEngine
    agent.context_engine.compact_history = MagicMock(side_effect=lambda msgs, **kwargs: msgs)
    agent.context_engine.get_active_recall = MagicMock(return_value="")
    agent.context_engine.get_commitments = MagicMock(return_value=[])
    agent.context_engine.build_system_prompt = MagicMock(return_value="System prompt")
    
    # Mock Client returning a direct response
    agent.client.chat = MagicMock(return_value="FINAL ANSWER: Here is your answer")
    
    with patch.object(agent.ops.term, "system_info", return_value="Win10"):
        agent.run("hi")
        
    agent.client.chat.assert_called_once()
    assert agent.task_tracker.current["status"] == "completed"

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_agent_run_repetition_and_empty(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_repeat"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    agent = Agent(mock_cfg)
    agent.memory.turn_count = 1
    agent.memory.get_messages = MagicMock(return_value=[])
    
    # 1st response: valid format but same repeatedly to trigger repetition warning
    # We will simulate 3 chat calls
    # Call 1: "TASK: repeat\nACTION: none"
    # Call 2: "TASK: repeat\nACTION: none"
    # Call 3: "FINAL ANSWER: done"
    agent.client.chat = MagicMock(side_effect=[
        "TASK: repeat\nACTION: none",
        "TASK: repeat\nACTION: none",
        "FINAL ANSWER: done"
    ])
    
    agent.run("test loop")
    assert agent.client.chat.call_count == 3

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_fallback_providers_init(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_fallback"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    
    mock_cfg["agent"]["fallback_providers"] = ["gemini", "groq", "nonexistent"]
    with patch("kernel.cli.GeminiClient") as mock_gemini, \
         patch("kernel.cli.GroqClient") as mock_groq:
             mock_gemini.return_value.provider = "gemini"
             mock_groq.return_value.provider = "groq"
             
             agent = Agent(mock_cfg)
             # TieredClient should be initialized
             assert hasattr(agent.client, "primary")
             assert agent.client.primary == mock_ollama.return_value

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_various_providers(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_providers"
    mock_cfg["agent"]["fallback_providers"] = []
    
    providers = ["nvidia", "gemini", "groq", "openai", "openrouter", "github", "deepseek"]
    for p in providers:
        mock_cfg["agent"]["provider"] = p
        client_name = f"kernel.cli.{p.capitalize()}Client" if p != "openai" else "kernel.cli.OpenAIClient"
        if p == "openrouter":
            client_name = "kernel.cli.OpenRouterClient"
        with patch(client_name) as mock_client:
            mock_client.return_value.provider = p
            agent = Agent(mock_cfg)
            assert agent.client == mock_client.return_value

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
def test_agent_reload_everything_real(mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_reload_real"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    agent = Agent(mock_cfg)
    
    # Reload cfg
    with patch("kernel.agent.load_cfg", return_value=mock_cfg), \
         patch("importlib.reload") as mock_reload:
             agent._reload_everything(["cfg.yaml", "kernel/cli.py"])
             mock_reload.assert_called()

@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
@patch("platform.system", return_value="Win10")
def test_preferences_autoload(mock_platform_sys, mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_prefs"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    agent = Agent(mock_cfg)
    agent.memory.turn_count = 0
    agent.memory.list_preferences = MagicMock(return_value={"pref1": "val1", "pref2": "val2"})
    agent.memory.get_messages = MagicMock(return_value=[])
    
    agent.client.chat = MagicMock(return_value="FINAL ANSWER: Done")
    
    agent.run("hi")
    
    # Check that system context & preferences are injected into memory.add argument
    call_args = agent.memory.add.call_args_list[0][0]
    assert "user" == call_args[0]
    assert "pref1=val1" in call_args[1]
    assert "Win10" in call_args[1]


@patch("kernel.cli.OllamaClient")
@patch("kernel.cli.SqliteSessionMemory")
@patch("kernel.cli.AuditLogger")
@patch("kernel.cli.ToolRegistry")
@patch("kernel.cli.ContextEngine")
@patch("kernel.cli.initialize_memory_manager")
@patch("platform.system", return_value="Win10")
def test_failed_parse_guardrail(mock_platform_sys, mock_init_mm, mock_ctx, mock_ops, mock_audit, mock_memory, mock_ollama, mock_cfg):
    mock_memory.return_value.session_id = "test_session_failed_parse"
    mock_ollama.return_value.provider = "ollama"
    mock_ollama.return_value.model = "llama2"
    agent = Agent(mock_cfg)
    agent.memory.turn_count = 0
    agent.memory.list_preferences = MagicMock(return_value={})
    agent.memory.get_messages = MagicMock(return_value=[])
    
    # First response attempts malformed ACTION JSON, second response completes with FINAL ANSWER
    agent.client.chat = MagicMock(side_effect=[
        'ACTION: {"tool": "write_file", "args": {invalid_json_here}',
        "FINAL ANSWER: Done"
    ])
    
    agent.run("hi")
    
    # Verify we had 2 turns
    assert agent.client.chat.call_count == 2
    # Verify that the memory or history got the parsing failure nudge
    nudge_added = False
    for call in agent.memory.add.call_args_list:
        role, content = call[0][0], call[0][1]
        if role == "user" and "Tool parsing failed" in content:
            nudge_added = True
            break
    assert nudge_added is True

