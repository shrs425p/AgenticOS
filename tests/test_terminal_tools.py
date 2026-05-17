import ctypes
from unittest import mock

from tools.terminal.openers import OpenersMixin
from tools.terminal.system_admin import SystemAdminMixin
from tools.terminal.system import SystemMixin

class MockTerminalTools(OpenersMixin, SystemAdminMixin, SystemMixin):
    def __init__(self):
        self.system = "Windows"
        self.cfg = {
            "endpoints": {
                "spotify_search": "https://mock.spotify.com/search/",
                "google_search": "https://mock.google.com/search?q="
            },
            "windows_paths": {
                "uninstall_registry": "HKLM:\\Mock\\Uninstall\\*",
                "wow6432_uninstall_registry": "HKLM:\\Mock64\\Uninstall\\*",
                "desktop_registry": "HKCU:\\Mock\\Desktop"
            }
        }
        
    def _get_timeout(self, *args, **kwargs):
        return 10
        
    def run_powershell(self, ps, timeout=None):
        return f"MOCK_PS: {ps}"
        
    def run_command(self, cmd, timeout=None):
        return f"MOCK_CMD: {cmd}"

@mock.patch("webbrowser.open")
def test_openers_spotify(mock_browser):
    tool = MockTerminalTools()
    res = tool.open_spotify_search("test track")
    
    assert res == "Opened."
    mock_browser.assert_called_once_with("https://mock.spotify.com/search/test%20track")

@mock.patch("webbrowser.open")
def test_openers_google(mock_browser):
    tool = MockTerminalTools()
    res = tool.open_google_search("hello world")
    
    assert res == "Opened."
    mock_browser.assert_called_once_with("https://mock.google.com/search?q=hello%20world")

def test_system_admin_installed_apps():
    tool = MockTerminalTools()
    res = tool.installed_apps()
    
    assert "MOCK_PS" in res
    assert "HKLM:\\Mock\\Uninstall\\*" in res
    assert "HKLM:\\Mock64\\Uninstall\\*" in res

def test_system_set_wallpaper():
    tool = MockTerminalTools()
    # We just want to check the registry verification part
    # since we can't easily mock ctypes
    # We can mock ctypes and run_powershell
    with mock.patch.object(ctypes, "windll", create=True) as mock_windll, \
         mock.patch("os.path.exists") as mock_exists:
        mock_windll.user32.SystemParametersInfoW.return_value = True
        mock_exists.return_value = True
        res = tool.set_wallpaper("C:\\mock\\image.jpg")
        
        # Verify it attempts to read the registry using the mock path
        assert "HKCU:\\Mock\\Desktop" in res or "Wallpaper set" in res
