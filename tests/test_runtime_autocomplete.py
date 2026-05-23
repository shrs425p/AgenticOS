import pytest
from unittest.mock import patch
from core.runtime import CommandCompleter

class MockCLI:
    def __init__(self, cfg=None):
        self.cfg = cfg or {}

@pytest.fixture
def mock_readline():
    with patch("core.runtime.readline") as mock_rl:
        yield mock_rl

def test_autocomplete_commands(mock_readline):
    commands = {"/help": "help", "/zone": "zone", "/exit": "exit", "/logs": "logs"}
    cli = MockCLI()
    completer = CommandCompleter(commands, cli)

    # Mock readline.get_line_buffer to return "/"
    mock_readline.get_line_buffer.return_value = "/"
    
    # Check that typing "/" lists all commands
    matches = []
    state = 0
    while True:
        match = completer.complete("", state)
        if match is None:
            break
        matches.append(match)
        state += 1
    
    assert sorted(matches) == sorted(["/help", "/zone", "/exit", "/logs"])

def test_autocomplete_partial_command(mock_readline):
    commands = {"/zone": "zone", "/exit": "exit", "/logs": "logs"}
    cli = MockCLI()
    completer = CommandCompleter(commands, cli)

    # Mock typing "/z"
    mock_readline.get_line_buffer.return_value = "/z"
    
    assert completer.complete("/z", 0) == "/zone"
    assert completer.complete("/z", 1) is None

def test_autocomplete_sub_arguments(mock_readline):
    commands = {"/zone": "zone", "/logs": "logs", "/tasks": "tasks"}
    cli = MockCLI()
    completer = CommandCompleter(commands, cli)

    # 1. Typing "/zone " (trailing space, empty text parameter)
    mock_readline.get_line_buffer.return_value = "/zone "
    matches = []
    state = 0
    while True:
        match = completer.complete("", state)
        if match is None:
            break
        matches.append(match)
        state += 1
    assert "yellow" in matches
    assert "green" in matches
    assert "red" in matches
    assert "blue" in matches

    # 2. Typing "/zone y"
    mock_readline.get_line_buffer.return_value = "/zone y"
    assert completer.complete("y", 0) == "yellow"
    assert completer.complete("y", 1) is None

    # 3. Typing "/logs t"
    mock_readline.get_line_buffer.return_value = "/logs t"
    assert completer.complete("t", 0) == "tail"

    # 4. Typing "/tasks c"
    mock_readline.get_line_buffer.return_value = "/tasks c"
    assert completer.complete("c", 0) == "current"

def test_autocomplete_dynamic_provider(mock_readline):
    commands = {"/provider": "provider"}
    # Setup mock configuration with cloud providers
    cfg = {
        "cloud": {
            "gemini": {"key": "test"},
            "nvidia": {"key": "test"}
        }
    }
    cli = MockCLI(cfg)
    completer = CommandCompleter(commands, cli)

    # Typing "/provider "
    mock_readline.get_line_buffer.return_value = "/provider "
    matches = []
    state = 0
    while True:
        match = completer.complete("", state)
        if match is None:
            break
        matches.append(match)
        state += 1
    
    assert "ollama" in matches
    assert "gemini" in matches
    assert "nvidia" in matches

    # Typing "/provider g"
    mock_readline.get_line_buffer.return_value = "/provider g"
    assert completer.complete("g", 0) == "gemini"
    assert completer.complete("g", 1) is None

def test_readline_missing_or_errors():
    with patch("core.runtime.readline", None):
        completer = CommandCompleter(["/zone"], MockCLI())
        # Should handle missing readline gracefully without raising exception
        assert completer.complete("", 0) is None

def test_autocomplete_path_fallback(mock_readline):
    commands = {"/logs": "logs"}
    cli = MockCLI()
    completer = CommandCompleter(commands, cli)

    with patch("os.path.isdir") as mock_isdir, \
         patch("os.listdir") as mock_listdir:
        
        def isdir_side_effect(path):
            norm = path.replace("\\", "/").rstrip("/")
            if norm in (".", "core", "workspace", "./core", "./workspace"):
                return True
            return False
            
        def listdir_side_effect(path):
            if path == ".":
                return ["core", "workspace", "dummy.txt", "main.py"]
            elif path == "core":
                return ["runtime.py", "memory_manager.py", "logger.py"]
            elif path == "workspace":
                return ["MEMORY.md", "AGENTS.md"]
            return []
            
        mock_isdir.side_effect = isdir_side_effect
        mock_listdir.side_effect = listdir_side_effect

        # Case 1: Partial match in current directory
        mock_readline.get_line_buffer.return_value = "/logs view main"
        assert completer.complete("main", 0) == "main.py"
        assert completer.complete("main", 1) is None

        # Case 2: Match directories and append slashes
        mock_readline.get_line_buffer.return_value = "/logs view cor"
        assert completer.complete("cor", 0) == "core/"

        # Case 3: Complete inside subdirectories
        mock_readline.get_line_buffer.return_value = "/logs view core/ru"
        assert completer.complete("core/ru", 0) == "core/runtime.py"

        # Case 4: Preserve backward slashes on Windows
        mock_readline.get_line_buffer.return_value = "view core\\me"
        assert completer.complete("core\\me", 0) == "core\\memory_manager.py"
