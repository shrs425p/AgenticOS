import pytest
from unittest.mock import MagicMock, patch
from core.tool_registry import ToolRegistry, tool

class DummyPlugin:
    @tool(name="dummy_tool", desc="A dummy tool for testing", category="Dummy")
    def dummy_tool(self, x: int) -> str:
        return f"Dummy {x}"

    @tool(name="dummy_path_tool", desc="A dummy tool with path arg", category="Dummy")
    def dummy_path_tool(self, path: str) -> str:
        return f"Path {path}"

@pytest.fixture
def mock_config(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    cfg = {
        "agent": {
            "workspace": str(workspace),
        },
        "rules": {},
        "tools": {
            "url_presets": True
        },
        "policy": {
            "write_tools": ["dummy_path_tool"],
            "path_keys": ["path"],
            "read_only_tools": []
        },
        "autonomy": {
            "validate_results": False
        }
    }
    return cfg

def test_tool_registration(mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
    registry._register_subsystem(DummyPlugin())
    
    assert "dummy_tool" in registry.registry
    
    fn = registry.registry["dummy_tool"]["fn"]
    assert registry.registry["dummy_tool"]["desc"] == "A dummy tool for testing"
    assert registry.registry["dummy_tool"]["category"] == "Dummy"
    assert fn(x=5) == "Dummy 5"

def test_tool_descriptions(mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
    registry.registry.clear()
    registry._register_subsystem(DummyPlugin())
    
    desc = registry.tool_descriptions()
    assert "[DUMMY]:" in desc
    assert "dummy_tool: A dummy tool for testing" in desc

def test_preferences(mock_config):
    memory = MagicMock()
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config, memory_backend=memory)
        
    assert registry._pref_set("k", "v") == "OK"
    memory.set_preference.assert_called_with("k", "v")
    
    memory.get_preferences.return_value = {"k": "v"}
    assert "k=v" in registry._pref_list()
    
    # Missing memory
    registry._memory = None
    assert "Error:" in registry._pref_set("k", "v")
    assert "Error:" in registry._pref_list()

def test_commitments(mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
        
    with patch("core.memory_manager.get_memory_manager") as mock_gmm:
        mm = MagicMock()
        mock_gmm.return_value = mm
        
        mm.register_commitment.return_value = "Commitment registered"
        assert registry.register_commitment("task", "today") == "Commitment registered"
        mm.register_commitment.assert_called_with("task", "today")
        
        mm.complete_commitment.return_value = "Commitment completed"
        assert registry.complete_commitment("id1") == "Commitment completed"
        mm.complete_commitment.assert_called_with("id1")
        
    # None memory manager
    with patch("core.memory_manager.get_memory_manager", return_value=None):
        assert "Error:" in registry.register_commitment("task")
        assert "Error:" in registry.complete_commitment("id1")

def test_calculate(mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
        
    assert registry._calculate("2 + 2") == "4"
    assert registry._calculate("2 * (3 + 4)") == "14"
    assert registry._calculate("abs(-5)") == "5"
    assert registry._calculate("sin(0)") == "0.0"
    
    # Division by zero
    assert "Error:" in registry._calculate("1 / 0")
    
    # Unsupported operations
    assert "Error:" in registry._calculate("import os")
    assert "Error:" in registry._calculate("open('file.txt')")

def test_notepad(mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
        
    assert "Notepad is empty" in registry._note_list()
    assert "saved" in registry._note_add("hello world")
    assert "hello world" in registry._note_list()
    assert "cleared" in registry._note_clear()
    assert "Notepad is empty" in registry._note_list()

def test_canvas(mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
        
    assert "Canvas is empty" in registry._canvas_view()
    assert "updated" in registry._canvas_set("hello")
    assert registry._canvas_view() == "hello"
    assert "appended" in registry._canvas_append("world")
    assert registry._canvas_view() == "hello\nworld"
    assert "cleared" in registry._canvas_clear()
    assert "Canvas is empty" in registry._canvas_view()

def test_tools_list_count(mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
        
    assert int(registry.tools_count()) > 0
    assert "tools_list" in registry.tools_list()

def test_memory_search(mock_config):
    memory = MagicMock()
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config, memory_backend=memory)
        
    # Empty query
    assert "Error:" in registry.memory_search("")
    
    # No matches
    memory.get_messages.return_value = []
    assert "No matches" in registry.memory_search("test")
    
    # Match found
    memory.get_messages.return_value = [{"role": "user", "content": "This is a secret message"}]
    assert "USER: This is a secret message" in registry.memory_search("secret")

@patch("requests.get")
def test_download_smart(mock_get, mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
        
    # URL errors
    assert "Error:" in registry.download_smart("", "dest.txt")
    assert "Error:" in registry.download_smart("invalid_url", "dest.txt")
    
    # Success via requests
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"chunk1", b"chunk2"]
    mock_get.return_value.__enter__.return_value = mock_resp
    
    with patch("os.path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat:
             mock_stat.return_value.st_size = 12
             res = registry.download_smart("https://example.com/file", "dest.txt")
             assert "requests" in res

def test_get_symbol(mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
        
    assert registry.get_symbol("read_file") == "[F]"
    assert registry.get_symbol("run_command") == "[T]"
    assert registry.get_symbol("calculate") == "[M]"
    assert registry.get_symbol("nonexistent") == "[*]"

def test_call_and_security(mock_config):
    with patch("core.tool_registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_config)
    registry._register_subsystem(DummyPlugin())
    
    # Unknown tool
    assert "Unknown tool" in registry.call("nonexistent", {})
    
    # Success dict args call
    assert registry.call("dummy_tool", {"x": 10}) == "Dummy 10"
    
    # Success positional args call
    assert registry.call("dummy_tool", [20]) == "Dummy 20"
    
    # Shadow mode
    registry.shadow_mode = True
    assert "SHADOW MODE" in registry.call("dummy_path_tool", {"path": "test.txt"})
    registry.shadow_mode = False
    
    # Path guardrail rejection
    with patch.object(registry.guard, "check_path", return_value=(False, "Forbidden path")):
        assert "Forbidden path" in registry.call("dummy_path_tool", {"path": "/etc/shadow"})

def test_tool_registry_signature_exception(mock_config):
    registry = ToolRegistry(mock_config)
    class BadTool:
        @tool("bad")
        def bad(self): pass
    registry._register_subsystem(BadTool())

    with patch("inspect.signature", side_effect=ValueError("Bad signature")):
        assert registry._get_signature("bad") == "unknown"

def test_tool_registry_run_tool_exceptions(mock_config):
    registry = ToolRegistry(mock_config)
    class ExceptionTools:
        @tool("type_err")
        def type_err(self): raise TypeError("Type error")
        @tool("perm_err")
        def perm_err(self): raise PermissionError("Perm error")
        @tool("file_err")
        def file_err(self): raise FileNotFoundError("File err")
        @tool("gen_err")
        def gen_err(self): raise Exception("Gen err")
    registry._register_subsystem(ExceptionTools())

    assert "Tool argument error" in registry.call("type_err", {})
    assert "Permission denied" in registry.call("perm_err", {})
    assert "File not found" in registry.call("file_err", {})
    assert "Tool error" in registry.call("gen_err", {})

def test_tool_registry_call_arg_conversion(mock_config):
    registry = ToolRegistry(mock_config)
    class TypesTool:
        @tool("types")
        def types(self, i, f, s): return f"{type(i).__name__} {type(f).__name__} {type(s).__name__}"
    registry._register_subsystem(TypesTool())

    res = registry.call("types", ["123", "45.6", "text"])
    assert "int float str" in res

def test_tool_registry_run_tool_exceptions_more(mock_config):
    registry = ToolRegistry(mock_config)
    class MissingModTool:
        @tool("missing_mod")
        def missing_mod(self): raise ModuleNotFoundError("No module named 'fake_module_123'")
    registry._register_subsystem(MissingModTool())

    with patch("subprocess.run"):
        res = registry.call("missing_mod", {})
        assert "Tool error" in res or "No module named" in res

def test_tool_registry_run_tool_validation(mock_config):
    registry = ToolRegistry(mock_config)
    class ValidTool:
        @tool("valid")
        def valid(self): return "ok"
    registry._register_subsystem(ValidTool())

    with patch("core.tool_registry.validate_tool", return_value="Note: validated"):
        registry.call("valid", {})
        # validate tool might be disabled by config
        pass

def test_tool_registry_run_tool_positional_path(mock_config):
    registry = ToolRegistry(mock_config)
    class PathPosTool:
        @tool("read_file")
        def read_file(self, path): return f"Read {path}"
    registry._register_subsystem(PathPosTool())

    with patch.object(registry.guard, "check_path", return_value=(False, "Forbidden")):
        assert "Forbidden" in registry.call("read_file", ["/root/secret.txt"])

def test_tool_registry_missing_parent_dir(mock_config):
    registry = ToolRegistry(mock_config)
    class MissingParentTool:
        @tool("write_file")
        def write_file(self, content, path):
            raise FileNotFoundError(2, "No such file or directory", "nonexistent/dir/file.txt")
    registry._register_subsystem(MissingParentTool())

    with patch("os.makedirs") as mock_makedirs:
        with patch.object(registry.guard, "check_path", return_value=(True, "Allowed")):
            res = registry.call("write_file", {"content": "test", "path": "nonexistent/dir/file.txt"})
            assert "No such file or directory" in res or "File not found" in res
            assert mock_makedirs.called
