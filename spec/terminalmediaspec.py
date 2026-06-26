from unittest.mock import MagicMock, patch
from ops.shell.media import MediaMixin

# Define a mock tool class that inherits from MediaMixin
class MockTool(MediaMixin):
    def __init__(self, system="Windows"):
        self.system = system

def test_nircmd_path():
    tool = MockTool()
    
    # Path not found
    with patch("os.path.isfile", return_value=False):
        assert tool._nircmd_path() == ""
        
    # Base env var found
    with patch("os.environ.get", return_value="/mock/base"):
        with patch("os.path.isfile", return_value=True):
            assert "nircmd.exe" in tool._nircmd_path()

@patch("subprocess.run")
def test_send_media_key(mock_run):
    tool = MockTool(system="Windows")
    
    # OK
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    res = tool._send_media_key("B3")
    assert res == "OK"
    
    # Error
    mock_run.return_value = MagicMock(returncode=1, stderr="failed key")
    res = tool._send_media_key("B3")
    assert "Error: failed key" in res
    
    # Exception
    mock_run.side_effect = Exception("Crash")
    res = tool._send_media_key("B3")
    assert "Error: Crash" in res

@patch("subprocess.run")
def test_run_nircmd(mock_run):
    tool = MockTool(system="Windows")
    
    # No nircmd path
    with patch.object(tool, "_nircmd_path", return_value=""):
        res = tool._run_nircmd("volume", "2")
        assert "not found" in res
        
    # Found
    with patch.object(tool, "_nircmd_path", return_value="/cli/nircmd.exe"):
        mock_run.return_value = MagicMock(stdout="OK")
        res = tool._run_nircmd("volume", "2")
        assert res == "OK"

@patch("shutil.which")
@patch("subprocess.run")
def test_run_playerctl(mock_run, mock_which):
    tool = MockTool(system="Linux")
    
    # playerctl not installed
    mock_which.return_value = None
    res = tool._run_playerctl("status")
    assert "not installed" in res
    
    # playerctl installed
    mock_which.return_value = "/usr/cli/playerctl"
    mock_run.return_value = MagicMock(stdout="playing")
    res = tool._run_playerctl("status")
    assert res == "playing"

@patch("subprocess.run")
def test_run_osascript(mock_run):
    tool = MockTool(system="Darwin")
    mock_run.return_value = MagicMock(stdout="OK")
    res = tool._run_osascript("test script")
    assert res == "OK"

def test_playback_controls():
    for sys_name in ["Windows", "Darwin", "Linux"]:
        tool = MockTool(system=sys_name)
        
        with patch.object(tool, "_send_media_key", return_value="OK") as mock_key, \
             patch.object(tool, "_run_osascript", return_value="OK") as mock_osa, \
             patch.object(tool, "_run_playerctl", return_value="OK") as mock_play:
                 
            assert tool.mediaplaypause() == "OK"
            assert tool.mediaplay() == "OK"
            assert tool.mediapause() == "OK"
            assert tool.mediastop() == "OK"
            assert tool.medianext() == "OK"
            assert tool.mediaprevious() == "OK"
            
            if sys_name == "Windows":
                mock_key.assert_called()
            elif sys_name == "Darwin":
                mock_osa.assert_called()
            else:
                mock_play.assert_called()

@patch("subprocess.run")
def test_mediastatus(mock_run):
    # Windows SMTC fallback
    tool = MockTool(system="Windows")
    
    # Tasklist fallback if SMTC unavailable
    mock_run.return_value = MagicMock(stdout="spotify.exe  1234 Console")
    res = tool.mediastatus()
    assert "Running players: spotify" in res
    
    # Darwin status
    tool_darwin = MockTool(system="Darwin")
    with patch.object(tool_darwin, "_run_osascript", return_value="Playing: song — artist"):
        assert "Playing: song — artist" in tool_darwin.mediastatus()
        
    # Linux status
    tool_linux = MockTool(system="Linux")
    with patch.object(tool_linux, "_run_playerctl", side_effect=["playing", "song", "artist"]):
        res = tool_linux.mediastatus()
        assert "Status: playing" in res
        assert "Title:  song" in res

@patch("shutil.which")
def test_mediaseek(mock_which):
    # Seek invalid
    tool = MockTool(system="Linux")
    assert "must be a number" in tool.mediaseek("abc")
    
    # Windows seek (unsupported unless playerctl found)
    tool_win = MockTool(system="Windows")
    mock_which.return_value = None
    assert "not universally supported" in tool_win.mediaseek(10)
    
    # Darwin seek
    tool_darwin = MockTool(system="Darwin")
    with patch.object(tool_darwin, "_run_osascript", return_value="OK") as mock_osa:
        assert tool_darwin.mediaseek(10) == "OK"
        mock_osa.assert_called()
        
    # Linux seek
    tool_linux = MockTool(system="Linux")
    mock_which.return_value = "/usr/cli/playerctl"
    with patch.object(tool_linux, "_run_playerctl", return_value="OK") as mock_play:
        assert tool_linux.mediaseek(-5) == "OK"
        mock_play.assert_called_with("position", "5.0")

@patch("shutil.which")
@patch("subprocess.run")
def test_volumeset(mock_run, mock_which):
    # Volume Set invalid
    tool = MockTool()
    assert "must be 0–100" in tool.volumeset("abc")
    
    # Windows volume set (nircmd path found)
    tool_win = MockTool(system="Windows")
    with patch.object(tool_win, "_nircmd_path", return_value="/cli/nircmd.exe"):
        with patch.object(tool_win, "_run_nircmd", return_value="OK") as mock_nir:
            assert tool_win.volumeset(50) == "OK"
            mock_nir.assert_called_with("setsysvolume", "32767")
            
    # Windows volume set fallback (no nircmd path)
    with patch.object(tool_win, "_nircmd_path", return_value=""):
        mock_run.return_value = MagicMock(stdout="Volume set to 50%")
        assert "Volume set to 50%" in tool_win.volumeset(50)
        
    # Darwin volume set
    tool_darwin = MockTool(system="Darwin")
    with patch.object(tool_darwin, "_run_osascript", return_value="OK") as mock_osa:
        assert tool_darwin.volumeset(30) == "OK"
        mock_osa.assert_called()
        
    # Linux volume set with pactl
    tool_linux = MockTool(system="Linux")
    mock_which.side_effect = lambda x: x == "pactl"
    mock_run.return_value = MagicMock(stdout="")
    assert "Volume set to 60%" in tool_linux.volumeset(60)
    
    # Linux volume set with amixer
    mock_which.side_effect = lambda x: x == "amixer"
    assert "Volume set to 70%" in tool_linux.volumeset(70)
    
    # Linux volume set no ops
    mock_which.side_effect = lambda x: False
    assert "Error:" in tool_linux.volumeset(50)

@patch("shutil.which")
@patch("subprocess.run")
def test_volumeup_down_mute(mock_run, mock_which):
    # Windows Up/Down with nircmd
    tool_win = MockTool(system="Windows")
    with patch.object(tool_win, "_nircmd_path", return_value="/cli/nircmd.exe"):
        with patch.object(tool_win, "_run_nircmd", return_value="OK"):
            assert tool_win.volumeup(10) == "OK"
            assert tool_win.volumedown(10) == "OK"
            assert tool_win.volumemute() == "OK"
        
    # Windows Up/Down fallbacks without nircmd
    with patch.object(tool_win, "_nircmd_path", return_value=""), \
         patch.object(tool_win, "_send_media_key", return_value="OK"):
             assert "increased by" in tool_win.volumeup(10)
             assert "decreased by" in tool_win.volumedown(10)
             assert tool_win.volumemute() == "OK"
             
    # Darwin
    tool_darwin = MockTool(system="Darwin")
    with patch.object(tool_darwin, "_run_osascript", return_value="OK"):
        assert tool_darwin.volumeup(10) == "OK"
        assert tool_darwin.volumedown(10) == "OK"
        assert tool_darwin.volumemute() == "OK"
        
    # Linux pactl
    tool_linux = MockTool(system="Linux")
    mock_which.side_effect = lambda x: x == "pactl"
    assert "increased by" in tool_linux.volumeup(10)
    assert "decreased by" in tool_linux.volumedown(10)
    assert "Mute" in tool_linux.volumemute()
    
    # Linux amixer
    mock_which.side_effect = lambda x: x == "amixer"
    assert "increased by" in tool_linux.volumeup(10)
    assert "decreased by" in tool_linux.volumedown(10)
    assert "Mute" in tool_linux.volumemute()

@patch("shutil.which")
@patch("subprocess.run")
def test_volumeget(mock_run, mock_which):
    # Windows
    tool_win = MockTool(system="Windows")
    mock_run.return_value = MagicMock(stdout="Volume: 50% | Muted: False")
    assert "Volume: 50%" in tool_win.volumeget()
    
    # Darwin
    tool_darwin = MockTool(system="Darwin")
    with patch.object(tool_darwin, "_run_osascript", return_value="70"):
        assert tool_darwin.volumeget() == "70"
        
    # Linux pactl
    tool_linux = MockTool(system="Linux")
    mock_which.side_effect = lambda x: x == "pactl"
    mock_run.return_value = MagicMock(stdout="Volume: 60%")
    assert "Volume: 60%" in tool_linux.volumeget()
    
    # Linux amixer
    mock_which.side_effect = lambda x: x == "amixer"
    mock_run.return_value = MagicMock(stdout="Simple mixer control")
    assert "Simple mixer control" in tool_linux.volumeget()
