import sys
from unittest.mock import patch, MagicMock
import pytest
from main import run_health_check


def test_run_health_check_ollama_success():
    mock_config = {
        "agent": {"provider": "ollama"},
        "ollama": {"base_url": "http://localhost:11434"}
    }
    
    mock_issues_result = MagicMock()
    mock_issues_result.has_errors = False
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"version": "0.1.48"}'
    mock_response.__enter__.return_value = mock_response
    
    with patch("sys.exit") as mock_exit, \
         patch("core.runtime_config.load_config", return_value=mock_config), \
         patch("core.config_validator.warn_config_issues", return_value=mock_issues_result), \
         patch("urllib.request.urlopen", return_value=mock_response), \
         patch("urllib.request.Request") as mock_req:
         
        run_health_check()
        mock_exit.assert_called_once_with(0)


def test_run_health_check_nvidia_success():
    mock_config = {
        "agent": {"provider": "nvidia"},
        "cloud": {"nvidia": {"base_url": "https://integrate.api.nvidia.com/v1"}}
    }
    
    mock_issues_result = MagicMock()
    mock_issues_result.has_errors = False
    
    with patch("sys.exit") as mock_exit, \
         patch("core.runtime_config.load_config", return_value=mock_config), \
         patch("core.config_validator.warn_config_issues", return_value=mock_issues_result), \
         patch.dict("os.environ", {"NVIDIA_API_KEY": "nvapi-testkey"}), \
         patch("urllib.request.urlopen") as mock_urlopen:
         
        run_health_check()
        mock_exit.assert_called_once_with(0)


def test_run_health_check_missing_api_key_failure():
    mock_config = {
        "agent": {"provider": "nvidia"},
        "cloud": {"nvidia": {"base_url": "https://integrate.api.nvidia.com/v1"}}
    }
    
    mock_issues_result = MagicMock()
    mock_issues_result.has_errors = False
    
    with patch("sys.exit") as mock_exit, \
         patch("core.runtime_config.load_config", return_value=mock_config), \
         patch("core.config_validator.warn_config_issues", return_value=mock_issues_result), \
         patch.dict("os.environ", {}, clear=True):
         
        run_health_check()
        mock_exit.assert_called_once_with(1)

