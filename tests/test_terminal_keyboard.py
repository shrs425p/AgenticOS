import pytest
from unittest.mock import MagicMock, patch
from tools.terminal.keyboard import KeyboardMixin, _combo_to_sendkeys, _combo_to_osascript

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

def test_hotkey_set_list_delete():
    tool = DummyKeyboardTool()
    assert "No custom shortcuts defined" in tool.hotkey_list()

    res = tool.hotkey_set("screenshot", "win+shift+s")
    assert "Custom shortcut set" in res

    res = tool.hotkey_list()
    assert "screenshot" in res

    res = tool.hotkey_delete("screenshot")
    assert "Removed custom shortcut" in res

    assert "Error" in tool.hotkey_set("", "win+c")
    assert "Error" in tool.hotkey_set("foo", "")
    assert "Error" in tool.hotkey_delete("")

@patch("subprocess.run")
def test_press_key(mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    res = tool.press_key("enter", 2)
    assert "Pressed [enter] x2" in res

    tool.system = "Darwin"
    res = tool.press_key("enter", 1)
    assert "Pressed [enter] x1" in res

    tool.system = "Linux"
    with patch("shutil.which", return_value="xdotool"):
        res = tool.press_key("enter", 1)
        assert "Pressed [enter] x1" in res

    assert "Error" in tool.press_key("")

@patch("subprocess.run")
def test_type_text(mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    res = tool.type_text("hello")
    assert "Typed 5 characters" in res

    tool.system = "Darwin"
    res = tool.type_text("hello")
    assert "Typed 5 characters" in res

    tool.system = "Linux"
    with patch("shutil.which", return_value="xdotool"):
        res = tool.type_text("hello")
        assert "Typed 5 characters" in res

    assert tool.type_text(None) == "Error: text required."

@patch("subprocess.run")
def test_key_down_up(mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    assert "key_down: shift" in tool.key_down("shift")
    assert "key_up: shift" in tool.key_up("shift")

    assert "Error" in tool.key_down("")
    assert "Error" in tool.key_up("")

@patch("subprocess.run")
def test_mouse_click_move_scroll(mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    assert "Error" not in tool.mouse_click("left")
    assert "Error" in tool.mouse_click("invalid")

    assert "Error" not in tool.mouse_move(100, 100)

    assert "Error" not in tool.mouse_scroll("down", 3)
    assert "Error" in tool.mouse_scroll("invalid", 3)

@patch("subprocess.run")
@patch("time.sleep")
def test_focus_window_and_hotkey(mock_sleep, mock_run):
    tool = DummyKeyboardTool("Windows")
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    assert "Focused" in tool.focus_window_and_hotkey("notepad", "ctrl+s")
    assert "Error" in tool.focus_window_and_hotkey("", "ctrl+s")
    assert "Error" in tool.focus_window_and_hotkey("notepad", "")
