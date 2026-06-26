import sys
import os
from unittest.mock import MagicMock, patch
import pytest
from core.exceptions import AgentError

# We still mock sys.modules just in case this is the first import
sys.modules['win32gui'] = MagicMock()
sys.modules['win32process'] = MagicMock()
sys.modules['win32security'] = MagicMock()
sys.modules['win32api'] = MagicMock()
sys.modules['win32con'] = MagicMock()
sys.modules['win32com'] = MagicMock()
sys.modules['win32com.client'] = MagicMock()
sys.modules['win32com'].client = sys.modules['win32com.client']
sys.modules['ntsecuritycon'] = MagicMock()

import tools.platform.windows_ui as win_ui
import tools.platform.macos_ui as mac_ui
import tools.platform.linux_desktop as linux_ui

# Setup module-level mocks to override cached imports
mock_gui = MagicMock()
mock_process = MagicMock()
mock_security = MagicMock()
mock_api = MagicMock()
mock_con = MagicMock()
mock_com_client = MagicMock()

win_ui.win32gui = mock_gui
win_ui.win32process = mock_process
win_ui.win32security = mock_security
win_ui.win32api = mock_api
win_ui.win32con = mock_con
win_ui.win32com_client = mock_com_client

# Define constants on mock_con so the code runs without raising mock attribute errors
mock_con.SW_RESTORE = 9
mock_con.MOUSEEVENTF_LEFTDOWN = 2
mock_con.MOUSEEVENTF_LEFTUP = 4

# --- Windows UI Tests ---
def test_windows_list_windows():
    mock_gui.reset_mock()
    def side_effect(callback, res):
        callback(101, res)
        callback(102, res)
    
    mock_gui.EnumWindows.side_effect = side_effect
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.side_effect = lambda hwnd: f"Window {hwnd}"
    mock_gui.GetClassName.return_value = "TestClass"
    
    with patch("tools.platform.windows_ui._HAS_WIN32", True):
        wins = win_ui.list_windows()
        assert len(wins) == 2
        assert wins[0]["hwnd"] == 101
        assert wins[0]["title"] == "Window 101"
        assert wins[0]["class"] == "TestClass"

def test_windows_focus_window_non_elevated():
    mock_gui.reset_mock()
    with patch("tools.platform.windows_ui._HAS_WIN32", True), \
         patch("tools.platform.windows_ui._is_hwnd_elevated", return_value=False):
        
        mock_gui.IsIconic.return_value = True
        win_ui.focus_window(123)
        mock_gui.ShowWindow.assert_called_once_with(123, 9)
        mock_gui.SetForegroundWindow.assert_called_once_with(123)

def test_windows_focus_window_elevated():
    with patch("tools.platform.windows_ui._HAS_WIN32", True), \
         patch("tools.platform.windows_ui._is_hwnd_elevated", return_value=True):
        
        with pytest.raises(AgentError) as exc_info:
            win_ui.focus_window(123)
        assert "UAC-elevated" in str(exc_info.value)
        assert exc_info.value.code == "SECURITY_VIOLATION"

def test_windows_click_at_win32():
    mock_api.reset_mock()
    with patch("tools.platform.windows_ui._HAS_WIN32", True):
        win_ui.click_at(100, 200)
        mock_api.SetCursorPos.assert_called_once_with((100, 200))
        assert mock_api.mouse_event.call_count == 2

def test_windows_type_text_win32():
    mock_com_client.reset_mock()
    mock_shell = MagicMock()
    mock_com_client.Dispatch.return_value = mock_shell
    
    with patch("tools.platform.windows_ui._HAS_WIN32", True):
        win_ui.type_text("Hello+World")
        mock_shell.SendKeys.assert_called_once_with("Hello{+}World", 0)

# --- macOS UI Tests ---
def test_macos_check_accessibility_permission_success():
    with patch("tools.platform.macos_ui.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        assert mac_ui.check_accessibility_permission() is True

def test_macos_check_accessibility_permission_fail():
    with patch("tools.platform.macos_ui.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        assert mac_ui.check_accessibility_permission() is False

def test_macos_list_windows():
    with patch("tools.platform.macos_ui.check_accessibility_permission", return_value=True), \
         patch("tools.platform.macos_ui.subprocess.run") as mock_run:
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Safari, Terminal, Finder\n"
        
        wins = mac_ui.list_windows()
        assert wins == ["Safari", "Terminal", "Finder"]

def test_macos_focus_window():
    with patch("tools.platform.macos_ui.check_accessibility_permission", return_value=True), \
         patch("tools.platform.macos_ui.subprocess.run") as mock_run:
        
        mock_run.return_value.returncode = 0
        mac_ui.focus_window("Safari")
        mock_run.assert_called_once()
        assert "tell application \"Safari\" to activate" in mock_run.call_args[0][0]

def test_macos_click_menu_item():
    with patch("tools.platform.macos_ui.check_accessibility_permission", return_value=True), \
         patch("tools.platform.macos_ui.subprocess.run") as mock_run:
        
        mock_run.return_value.returncode = 0
        mac_ui.click_menu_item("Safari", "New Tab", "File")
        mock_run.assert_called_once()
        script = mock_run.call_args[0][0][2]
        assert 'click menu item "New Tab" of menu "File" of menu bar 1' in script

def test_macos_type_text():
    with patch("tools.platform.macos_ui.check_accessibility_permission", return_value=True), \
         patch("tools.platform.macos_ui.subprocess.run") as mock_run:
        
        mock_run.return_value.returncode = 0
        mac_ui.type_text("Hello \"World\"")
        mock_run.assert_called_once()
        script = mock_run.call_args[0][0][2]
        assert 'keystroke "Hello \\"World\\""' in script

# --- Linux Desktop Tests ---
def test_linux_session_detection_wayland():
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"}):
        sess = linux_ui.detect_linux_session()
        assert sess["session_type"] == "wayland"
        assert sess["display"] == "wayland-0"

def test_linux_session_detection_x11():
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}):
        sess = linux_ui.detect_linux_session()
        assert sess["session_type"] == "x11"
        assert sess["display"] == ":0"

def test_linux_screenshot_wayland_success():
    with patch("tools.platform.linux_desktop.detect_linux_session", return_value={"session_type": "wayland"}), \
         patch("tools.platform.linux_desktop.shutil.which", return_value=True), \
         patch("tools.platform.linux_desktop.subprocess.run") as mock_run:
        
        mock_run.return_value.returncode = 0
        res = linux_ui.take_screenshot("test.png")
        assert res == "test.png"
        mock_run.assert_called_once_with(["grim", "test.png"], capture_output=True, text=True, timeout=10)

def test_linux_screenshot_x11_success():
    with patch("tools.platform.linux_desktop.detect_linux_session", return_value={"session_type": "x11"}), \
         patch("tools.platform.linux_desktop.shutil.which", return_value=True), \
         patch("tools.platform.linux_desktop.subprocess.run") as mock_run:
        
        mock_run.return_value.returncode = 0
        res = linux_ui.take_screenshot("test.png")
        assert res == "test.png"
        mock_run.assert_called_once_with(["scrot", "test.png"], capture_output=True, text=True, timeout=10)

def test_linux_screenshot_missing_tool():
    with patch("tools.platform.linux_desktop.detect_linux_session", return_value={"session_type": "wayland"}), \
         patch("tools.platform.linux_desktop.shutil.which", return_value=False):
        
        with pytest.raises(AgentError) as exc_info:
            linux_ui.take_screenshot("test.png")
        assert "grim not found" in str(exc_info.value)
