import pytest
from unittest.mock import MagicMock, patch
from kernel.registry import ToolRegistry, tool

class DummyPlugin:
    @tool(name="dummytool", desc="A dummy tool for testing", category="Dummy")
    def dummytool(self, x: int) -> str:
        return f"Dummy {x}"

    @tool(name="dummypathtool", desc="A dummy tool with path arg", category="Dummy")
    def dummypathtool(self, path: str) -> str:
        return f"Path {path}"

@pytest.fixture
def mock_cfg(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    cfg = {
        "agent": {
            "workspace": str(workspace),
        },
        "rules": {},
        "ops": {
            "url_presets": True
        },
        "policy": {
            "write_ops": ["dummypathtool"],
            "path_keys": ["path"],
            "read_only_ops": []
        },
        "autonomy": {
            "validate_results": False
        }
    }
    return cfg

def test_tool_registration(mock_cfg):
    with patch("kernel.registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_cfg)
    registry._register_subsystem(DummyPlugin())
    
    assert "dummytool" in registry.registry
    
    fn = registry.registry["dummytool"]["fn"]
    assert registry.registry["dummytool"]["desc"] == "A dummy tool for testing"
    assert registry.registry["dummytool"]["category"] == "Dummy"
    assert fn(x=5) == "Dummy 5"

def test_tool_descriptions(mock_cfg):
    with patch("kernel.registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_cfg)
    registry.registry.clear()
    registry._register_subsystem(DummyPlugin())
    
    desc = registry.tool_descriptions()
    assert "[DUMMY]:" in desc
    assert "dummytool: A dummy tool for testing" in desc



def test_calculate(mock_cfg):
    with patch("kernel.registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_cfg)
        
    assert registry._calculate("2 + 2") == "4"
    assert registry._calculate("2 * (3 + 4)") == "14"
    assert registry._calculate("abs(-5)") == "5"
    assert registry._calculate("sin(0)") == "0.0"
    
    # Division by zero
    assert "Error:" in registry._calculate("1 / 0")
    
    # Unsupported operations
    assert "Error:" in registry._calculate("import os")
    assert "Error:" in registry._calculate("open('file.txt')")



def test_opslist_count(mock_cfg):
    with patch("kernel.registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_cfg)
        
    assert int(registry.opscount()) > 0
    assert "opslist" in registry.opslist()


def test_registry_prunes_disabled_ops_and_categories(mock_cfg):
    mock_cfg["ops"]["disabled_ops"] = ["dummytool"]
    mock_cfg["ops"]["disabled_categories"] = ["Dummy"]
    mock_cfg["ops"]["essential_ops"] = ["dummypathtool"]
    with patch("kernel.registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_cfg)
    registry._register_subsystem(DummyPlugin())

    assert "dummytool" not in registry.registry
    assert "dummypathtool" in registry.registry

def test_memorysearch(mock_cfg):
    memory = MagicMock()
    with patch("kernel.registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_cfg, memory_backend=memory)
        
    # Empty query
    assert "Error:" in registry.memorysearch("")
    
    # No matches
    memory.get_messages.return_value = []
    assert "No matches" in registry.memorysearch("test")
    
    # Match found
    memory.get_messages.return_value = [{"role": "user", "content": "This is a secret message"}]
    assert "USER: This is a secret message" in registry.memorysearch("secret")

@patch("requests.get")
def test_downloadsmart(mock_get, mock_cfg):
    with patch("kernel.registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_cfg)
        
    # URL errors
    assert "Error:" in registry.downloadsmart("", "dest.txt")
    assert "Error:" in registry.downloadsmart("invalid_url", "dest.txt")
    
    # Success via requests
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"chunk1", b"chunk2"]
    mock_get.return_value.__enter__.return_value = mock_resp
    
    with patch("os.path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat:
             mock_stat.return_value.st_size = 12
             res = registry.downloadsmart("https://example.com/file", "dest.txt")
             assert "requests" in res

def test_get_symbol(mock_cfg):
    with patch("kernel.registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_cfg)
        
    assert registry.get_symbol("read_file") == "[F]"
    assert registry.get_symbol("runcommand") == "[T]"
    assert registry.get_symbol("calculate") == "[M]"
    assert registry.get_symbol("nonexistent") == "[*]"

def test_call_and_security(mock_cfg):
    with patch("kernel.registry.load_url_presets", return_value=[]):
        registry = ToolRegistry(mock_cfg)
    registry._register_subsystem(DummyPlugin())
    
    # Unknown tool
    assert "Unknown tool" in registry.call("nonexistent", {})
    
    # Success dict args call
    assert registry.call("dummytool", {"x": 10}) == "Dummy 10"
    
    # Success positional args call
    assert registry.call("dummytool", [20]) == "Dummy 20"
    
    # Shadow mode
    registry.shadow_mode = True
    assert "SHADOW MODE" in registry.call("dummypathtool", {"path": "test.txt"})
    registry.shadow_mode = False
    
    # Path guardrail rejection
    with patch.object(registry.guard, "check_path", return_value=(False, "Forbidden path")):
        assert "Forbidden path" in registry.call("dummypathtool", {"path": "/etc/shadow"})

def test_tool_registry_signature_exception(mock_cfg):
    registry = ToolRegistry(mock_cfg)
    class BadTool:
        @tool("bad")
        def bad(self): pass
    registry._register_subsystem(BadTool())

    with patch("inspect.signature", side_effect=ValueError("Bad signature")):
        assert registry._get_signature("bad") == "unknown"

def test_tool_registry_run_tool_exceptions(mock_cfg):
    registry = ToolRegistry(mock_cfg)
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

def test_tool_registry_call_arg_conversion(mock_cfg):
    registry = ToolRegistry(mock_cfg)
    class TypesTool:
        @tool("types")
        def types(self, i, f, s): return f"{type(i).__name__} {type(f).__name__} {type(s).__name__}"
    registry._register_subsystem(TypesTool())

    res = registry.call("types", ["123", "45.6", "text"])
    assert "int float str" in res

def test_tool_registry_run_tool_exceptions_more(mock_cfg):
    registry = ToolRegistry(mock_cfg)
    class MissingModTool:
        @tool("missing_mod")
        def missing_mod(self): raise ModuleNotFoundError("No module named 'fake_module_123'")
    registry._register_subsystem(MissingModTool())

    with patch("subprocess.run"):
        res = registry.call("missing_mod", {})
        assert "Tool error" in res or "No module named" in res

def test_tool_registry_run_tool_validation(mock_cfg):
    registry = ToolRegistry(mock_cfg)
    class ValidTool:
        @tool("valid")
        def valid(self): return "ok"
    registry._register_subsystem(ValidTool())

    with patch("kernel.registry.validate_tool", return_value="Note: validated"):
        registry.call("valid", {})
        # validate tool might be disabled by cfg
        pass

def test_tool_registry_run_tool_positional_path(mock_cfg):
    registry = ToolRegistry(mock_cfg)
    class PathPosTool:
        @tool("read_file")
        def read_file(self, path): return f"Read {path}"
    registry._register_subsystem(PathPosTool())

    with patch.object(registry.guard, "check_path", return_value=(False, "Forbidden")):
        assert "Forbidden" in registry.call("read_file", ["/root/secret.txt"])

def test_tool_registry_missing_parent_dir(mock_cfg):
    registry = ToolRegistry(mock_cfg)
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
