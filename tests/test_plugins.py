import os
from unittest import mock

from tools.plugins.fast_disk import fast_disk_audit

@mock.patch("core.platform_api.PlatformAPI.check_output_powershell")
def test_fast_disk_default_path(mock_check_output):
    mock_check_output.return_value = "Mock result"
    
    # Call without path
    res = fast_disk_audit(path=None, mode="all")
    
    # Check that it defaulted to the OS root
    root_path = os.path.abspath(os.sep)
    
    # Check that it attempted to run powershell commands with the root path
    assert "Mock result" in res
    assert mock_check_output.call_count >= 2
    
    # In 'all' mode, it searches 'Users' inside the root path
    expected_scan_path = os.path.join(root_path, "Users")
    
    # Get the arguments passed to the second call of check_output_powershell (the duplicates check)
    args, kwargs = mock_check_output.call_args_list[1]
    cmd = args[0]  # The actual powershell command is the first argument
    
    assert expected_scan_path.replace("'", "''") in cmd
