import pytest
from unittest import mock
from tools.system_tools import SystemManager

def test_exit_agent():
    sm = SystemManager()
    
    with mock.patch("os._exit") as mock_exit:
        sm.exit_agent("Goodbye")
        mock_exit.assert_called_once_with(0)
