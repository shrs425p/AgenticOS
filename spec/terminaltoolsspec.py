import ctypes
from unittest import mock

from ops.shell.open import OpenersMixin
from ops.shell.admin import SystemAdminMixin
from ops.shell.system import SystemMixin

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
        
    def runpowershell(self, ps, timeout=None):
        return f"MOCK_PS: {ps}"
        
    def runcommand(self, cmd, timeout=None):
        return f"MOCK_CMD: {cmd}"

def test_system_admin_installedapps():
    tool = MockTerminalTools()
    res = tool.installedapps()
    
    assert "MOCK_PS" in res
    assert "HKLM:\\Mock\\Uninstall\\*" in res
    assert "HKLM:\\Mock64\\Uninstall\\*" in res
