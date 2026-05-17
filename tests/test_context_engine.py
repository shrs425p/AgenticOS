from unittest.mock import MagicMock, patch
from core.context_engine import ContextEngine

class MockTaskTracker:
    def __init__(self):
        self.current = None

class MockTools:
    def __init__(self):
        self._canvas = ""
        self.shadow_mode = False

    def tool_descriptions(self):
        return "mock tools"

class MockAgent:
    def __init__(self, workspace: str = None):
        if workspace is None:
            # Create a temporary workspace directory
            import tempfile
            self.workspace = tempfile.mkdtemp()
        else:
            self.workspace = workspace
        self.cfg = {}
        self.task_tracker = MockTaskTracker()
        self.tools = MockTools()
        self.client = MagicMock()

def test_context_engine_init(tmp_path):
    agent = MockAgent(str(tmp_path))
    ce = ContextEngine(agent)
    assert ce.agent == agent
    assert ce.cfg == agent.cfg
    assert ce.workspace == str(tmp_path)
    assert ce.memory_manager is None

def test_set_memory_manager():
    ce = ContextEngine(MockAgent())
    mm = MagicMock()
    ce.set_memory_manager(mm)
    assert ce.memory_manager == mm

@patch("os.listdir")
@patch("os.path.isdir")
@patch("os.path.isfile")
@patch("os.path.getsize")
def test_scan_workspace(mock_getsize, mock_isfile, mock_isdir, mock_listdir):
    ce = ContextEngine(MockAgent("/workspace"))
    mock_listdir.side_effect = [
        ["dir1", "file1.txt", "file2.md"], # For workspace
        ["child1", "child2"], # For dir1
    ]
    mock_isdir.side_effect = lambda x: x.endswith("dir1")
    mock_isfile.side_effect = lambda x: not x.endswith("dir1")
    mock_getsize.return_value = 1024

    file_map_lines, md_files = ce._scan_workspace()
    
    assert "  dir1/  (2 items)" in file_map_lines
    assert "  file1.txt  (1024 bytes)" in file_map_lines
    assert "  file2.md  (1024 bytes)" in file_map_lines
    assert len(md_files) == 1
    assert md_files[0][0] == "file2.md"

@patch("core.context_engine.ContextEngine._scan_workspace")
@patch("builtins.open")
@patch("os.path.getsize")
def test_build_system_prompt_all_blocks(mock_getsize, mock_open, mock_scan):
    agent = MockAgent()
    agent.cfg = {
        "prompts": {
            "system_prompt": "You are {tool_descriptions}",
            "context_blocks": {
                "divider": "---DIVIDER---\n"
            }
        }
    }
    agent.task_tracker.current = {
        "goal": "Test goal",
        "objective": "Test obj",
        "plan": ["step 1"],
        "current_step": "step 1",
        "iteration": 1
    }
    agent.tools._canvas = "thinking content"
    agent.tools.shadow_mode = True
    
    ce = ContextEngine(agent)
    mock_scan.return_value = (["map_line_1"], [("test.md", "/workspace/test.md")])
    mock_getsize.return_value = 100
    mock_open.return_value.__enter__.return_value.read.return_value = "markdown content"
    
    prompt = ce.build_system_prompt("RECALL ", "COMMITMENTS")
    
    assert "You are mock tools" in prompt
    assert "---DIVIDER---" in prompt
    assert "Test goal" in prompt
    assert "thinking content" in prompt
    assert "WARNING: SHADOW MODE ACTIVE" in prompt
    assert "RECALL " in prompt
    assert "COMMITMENTS" in prompt
    assert "map_line_1" in prompt
    assert "markdown content" in prompt

def test_get_active_recall():
    ce = ContextEngine(MockAgent())
    assert ce.get_active_recall("test") == ""
    mm = MagicMock()
    mm.get_relevant_context.return_value = "context"
    ce.set_memory_manager(mm)
    assert ce.get_active_recall("test") == "context"
    mm.get_relevant_context.assert_called_with("test")

def test_get_commitments():
    ce = ContextEngine(MockAgent())
    assert ce.get_commitments() == ""
    mm = MagicMock()
    mm.get_active_commitments.return_value = "commits"
    ce.set_memory_manager(mm)
    assert ce.get_commitments() == "commits"
    mm.get_active_commitments.assert_called_once()

def test_compact_history_no_compaction():
    ce = ContextEngine(MockAgent())
    messages = [{"role": "user", "content": "1"}]
    assert ce.compact_history(messages, max_messages=5) == messages

def test_compact_history_llm_success():
    agent = MockAgent()
    agent.client.chat.return_value = "summarized context"
    ce = ContextEngine(agent)
    
    messages = [{"role": "user", "content": f"msg {i}"} for i in range(30)]
    compacted = ce.compact_history(messages, max_messages=20)
    
    assert len(compacted) == 11 # 1 compacted msg + 10 recent (min(20, 20//2)=10)
    assert "[COMPACTED CONTEXT]" in compacted[0]["content"]
    assert "summarized context" in compacted[0]["content"]
    assert compacted[1]["content"] == "msg 20"

def test_compact_history_llm_failure_fallback():
    agent = MockAgent()
    agent.client.chat.side_effect = Exception("API error")
    ce = ContextEngine(agent)
    
    messages = [{"role": "user", "content": f"msg {i}"} for i in range(30)]
    compacted = ce.compact_history(messages, max_messages=20)
    
    assert len(compacted) == 11
    assert "pruned" in compacted[0]["content"]
    assert "20 messages" in compacted[0]["content"]
