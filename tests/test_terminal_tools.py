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

def test_system_admin_installed_apps():
    tool = MockTerminalTools()
    res = tool.installed_apps()
    
    assert "MOCK_PS" in res
    assert "HKLM:\\Mock\\Uninstall\\*" in res
    assert "HKLM:\\Mock64\\Uninstall\\*" in res
