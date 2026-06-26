import os
from unittest.mock import patch
from tools.terminal.openers import OpenersMixin

class MockTool(OpenersMixin):
    def __init__(self, system="Windows"):
        self.system = system
        self.cfg = {}
        self.launch_candidates = ["C:\\expanded\\path\\to\\app.exe"]

    def _run(self, cmd, timeout=10):
        return "Started: guess"

    def process_list(self, img):
        return "process detected"

    def start_background(self, cmd):
        return "background started"

    def _quote_arg(self, arg):
        return f'"{arg}"'

def test_find_app():
    tool = MockTool(system="Windows")
    
    # Empty app name
    assert "Error:" in tool.find_app("")
    
    # shutil.which works
    with patch("shutil.which", return_value="C:\\path\\to\\app.exe"):
        assert tool.find_app("app") == "C:\\path\\to\\app.exe"
        
    # Start Menu shortcuts lookup fallback
    with patch("shutil.which", return_value=None), \
         patch("core.platform_api.PlatformAPI.find_windows_app", return_value=os.path.join("/mock/dir", "my_app.lnk")):
             assert tool.find_app("my_app") == os.path.join("/mock/dir", "my_app.lnk")

def test_open_app():
    tool = MockTool(system="Windows")
    
    # Shortcut case
    with patch.object(tool, "find_app", return_value="C:\\path\\to\\app.lnk"), \
         patch("os.startfile", create=True) as mock_start:
             assert "Opened shortcut:" in tool.open_app("app")
             mock_start.assert_called_once()
             
    # Launch application fallback case
    with patch.object(tool, "find_app", return_value="Not found."), \
         patch.object(tool, "launch_application", return_value="Launch output") as mock_launch:
             assert tool.open_app("app") == "Launch output"
             mock_launch.assert_called_with("app", "")

@patch("subprocess.Popen")
@patch("shutil.which")
def test_launch_application(mock_which, mock_popen):
    tool = MockTool(system="Windows")
    
    # Empty
    assert "Error:" in tool.launch_application("")
    
    # Windows launch with resolved exe
    mock_which.return_value = "C:\\path\\to\\app.exe"
    with patch("os.path.exists", return_value=True), \
         patch("time.sleep"):
             res = tool.launch_application("app", "--arg")
             assert "Started" in res or "Start attempted" in res
             mock_popen.assert_called()

def test_open_file(tmp_path):
    tool = MockTool(system="Windows")
    
    # Path empty
    assert "Error:" in tool.open_file("")
    
    # File not found
    assert "Error: file not found" in tool.open_file("nonexistent.txt")
    
    # Found and opened on Windows
    file_path = tmp_path / "test.txt"
    file_path.touch()
    with patch("os.startfile", create=True) as mock_start:
        assert tool.open_file(str(file_path)) == "Opened."
        mock_start.assert_called_with(str(file_path))
        
    # Found and opened on Linux/Darwin
    tool_linux = MockTool(system="Linux")
    with patch.object(tool_linux, "_run", return_value="Opened.") as mock_run:
        assert tool_linux.open_file(str(file_path)) == "Opened."
        mock_run.assert_called()

def test_compose_email():
    tool = MockTool(system="Windows")
    
    with patch("webbrowser.open") as mock_open:
        res = tool.compose_email("test@example.com", "hello", "body text", "cc@example.com", "bcc@example.com")
        assert "Opened mail composer" in res
        mock_open.assert_called()

def test_open_url_verified():
    tool = MockTool(system="Windows")
    
    with patch("webbrowser.open"):
        res = tool.open_url_verified("https://google.com")
        assert "process detected" in res
