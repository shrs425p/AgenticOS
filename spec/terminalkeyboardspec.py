from unittest.mock import MagicMock, patch
from ops.shell.keyboard import KeyboardMixin, _combo_to_sendkeys, _combo_to_osascript

class DummyKeyboardTool(KeyboardMixin):
    def __init__(self, system="Windows"):
        self.system = system
        self.custom_keys = {}

def test_combo_to_sendkeys():
    assert _combo_to_sendkeys("ctrl+c") == "^c"
    assert _combo_to_sendkeys("ctrl+shift+s") == "^+s"
    assert _combo_to_sendkeys("alt+f4") == "%{F4}"
    assert _combo_to_sendkeys("win+d") == "#d"
    assert _combo_to_sendkeys("enter") == "{ENTER}"

def test_combo_to_osascript():
    assert 'using {control down}' in _combo_to_osascript("ctrl+c")
    assert 'key code 36' in _combo_to_osascript("enter")

@patch("subprocess.run")
def test_hotkey(mock_run):
    # Windows
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
    res = tool.hotkey("ctrl+c")
    assert "Sent hotkey" in res
    assert "^c" in res

    # Darwin
    tool.system = "Darwin"
    res = tool.hotkey("ctrl+c")
    assert "Sent hotkey" in res

    # Linux
    tool.system = "Linux"
    with patch("shutil.which", return_value="xdotool"):
        res = tool.hotkey("ctrl+c")
        assert "Sent hotkey" in res

    # Error path
    assert tool.hotkey("") == "Error: keys required."

def test_hotkeyset_list_delete():
    tool = DummyKeyboardTool()
    assert "No custom shortcuts defined" in tool.hotkeylist()

    res = tool.hotkeyset("screenshot", "win+shift+s")
    assert "Custom shortcut set" in res

    res = tool.hotkeylist()
    assert "screenshot" in res

    res = tool.hotkeydelete("screenshot")
    assert "Removed custom shortcut" in res

    assert "Error" in tool.hotkeyset("", "win+c")
    assert "Error" in tool.hotkeyset("foo", "")
    assert "Error" in tool.hotkeydelete("")

@patch("subprocess.run")
def test_presskey(mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    res = tool.presskey("enter", 2)
    assert "Pressed [enter] x2" in res

    tool.system = "Darwin"
    res = tool.presskey("enter", 1)
    assert "Pressed [enter] x1" in res

    tool.system = "Linux"
    with patch("shutil.which", return_value="xdotool"):
        res = tool.presskey("enter", 1)
        assert "Pressed [enter] x1" in res

    assert "Error" in tool.presskey("")

@patch("subprocess.run")
def test_typetext(mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    res = tool.typetext("hello")
    assert "Typed 5 characters" in res

    tool.system = "Darwin"
    res = tool.typetext("hello")
    assert "Typed 5 characters" in res

    tool.system = "Linux"
    with patch("shutil.which", return_value="xdotool"):
        res = tool.typetext("hello")
        assert "Typed 5 characters" in res

    assert tool.typetext(None) == "Error: text required."

@patch("subprocess.run")
def test_keydown_up(mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    assert "keydown: shift" in tool.keydown("shift")
    assert "keyup: shift" in tool.keyup("shift")

    assert "Error" in tool.keydown("")
    assert "Error" in tool.keyup("")

@patch("subprocess.run")
def test_mouseclick_move_scroll(mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    assert "Error" not in tool.mouseclick("left")
    assert "Error" in tool.mouseclick("invalid")

    assert "Error" not in tool.mousemove(100, 100)

    assert "Error" not in tool.mousescroll("down", 3)
    assert "Error" in tool.mousescroll("invalid", 3)

@patch("subprocess.run")
@patch("time.sleep")
def test_focuswindowandhotkey(mock_sleep, mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    assert "Focused" in tool.focuswindowandhotkey("notepad", "ctrl+s")
    assert "Error" in tool.focuswindowandhotkey("", "ctrl+s")
    assert "Error" in tool.focuswindowandhotkey("notepad", "")
