import os
import sys
import pytest
import requests
import importlib.metadata
from unittest.mock import MagicMock, patch
from kernel.plugins import PluginRegistryClient
from kernel.errors import AgentError

@pytest.fixture(autouse=True)
def cleanup_test_plugins():
    yield
    # Cleanup downloaded files and modules to avoid polluting environment
    names = ["test_temp_plugin", "test_temp_plugin_incompat", "test_temp_plugin_missing", "test_temp_plugin_error"]
    plugin_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "ops", "addons")
    )
    for name in names:
        file_path = os.path.join(plugin_dir, f"{name}.py")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        mod_name = f"ops.addons.{name}"
        if mod_name in sys.modules:
            del sys.modules[mod_name]

def test_fetch_plugin_manifest_success():
    client = PluginRegistryClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "test_temp_plugin",
        "version": "1.0.0",
        "dependencies": {"numpy": ">=1.20.0"}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response) as mock_get:
        manifest = client.fetch_plugin_manifest("test_temp_plugin", "http://mock-registry.com")
        mock_get.assert_called_once_with("http://mock-registry.com/manifests/test_temp_plugin.json", timeout=10)
        assert manifest["name"] == "test_temp_plugin"
        assert manifest["version"] == "1.0.0"

def test_fetch_plugin_manifest_network_error():
    client = PluginRegistryClient()
    with patch("requests.get", side_effect=requests.RequestException("Connection refused")):
        with pytest.raises(AgentError) as exc_info:
            client.fetch_plugin_manifest("test_temp_plugin", "http://mock-registry.com")
        assert exc_info.value.code == "FETCH_MANIFEST_FAILED"

def test_fetch_plugin_manifest_invalid_json():
    client = PluginRegistryClient()
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(AgentError) as exc_info:
            client.fetch_plugin_manifest("test_temp_plugin", "http://mock-registry.com")
        assert exc_info.value.code == "INVALID_MANIFEST"

def test_verify_dependencies_success():
    client = PluginRegistryClient()
    manifest = {
        "dependencies": {
            "numpy": ">=1.20.0",
            "requests": ">=2.0.0,<3.0.0"
        }
    }

    def mock_version(pkg):
        if pkg == "numpy":
            return "1.24.2"
        if pkg == "requests":
            return "2.31.0"
        raise importlib.metadata.PackageNotFoundError

    with patch("importlib.metadata.version", side_effect=mock_version):
        # Should not raise any exception
        client.verify_dependencies(manifest)

def test_verify_dependencies_invalid_type():
    client = PluginRegistryClient()
    manifest = {
        "dependencies": "not-a-dict"
    }
    # Should silently return without error
    client.verify_dependencies(manifest)

def test_verify_dependencies_invalid_specifier():
    client = PluginRegistryClient()
    manifest = {
        "dependencies": {
            "numpy": "invalid_specifier"
        }
    }
    with patch("importlib.metadata.version", return_value="1.24.2"):
        with pytest.raises(AgentError) as exc_info:
            client.verify_dependencies(manifest)
        assert exc_info.value.code == "INCOMPATIBLE_VERSION"
        assert "Invalid dependency version specifier" in exc_info.value.message

def test_verify_dependencies_missing():
    client = PluginRegistryClient()
    manifest = {
        "dependencies": {
            "nonexistent_pkg": ">=1.0.0"
        }
    }

    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        with pytest.raises(AgentError) as exc_info:
            client.verify_dependencies(manifest)
        assert exc_info.value.code == "MISSING_DEPENDENCY"
        assert "nonexistent_pkg" in exc_info.value.message

def test_verify_dependencies_incompatible():
    client = PluginRegistryClient()
    manifest = {
        "dependencies": {
            "numpy": ">=1.20.0"
        }
    }

    with patch("importlib.metadata.version", return_value="1.19.5"):
        with pytest.raises(AgentError) as exc_info:
            client.verify_dependencies(manifest)
        assert exc_info.value.code == "INCOMPATIBLE_VERSION"
        assert "numpy" in exc_info.value.message

def test_download_plugin_success():
    mock_registry = MagicMock()
    client = PluginRegistryClient(registry=mock_registry)

    manifest = {
        "name": "test_temp_plugin",
        "version": "1.0.0",
        "dependencies": {"numpy": ">=1.20.0"},
        "download_url": "http://mock-registry.com/plugins/test_temp_plugin.py"
    }
    plugin_code = """
from kernel.base import tool

@tool(name="testtemptool", desc="A temporary test tool")
def testtemptool(val: str) -> str:
    return f"Processed {val}"
"""

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "manifests" in url:
            resp.json.return_value = manifest
        else:
            resp.text = plugin_code
        return resp

    with patch("requests.get", side_effect=mock_get), \
         patch("importlib.metadata.version", return_value="1.24.2"):
        
        file_path = client.download_plugin("test_temp_plugin", "http://mock-registry.com")
        
        # Verify file is written
        assert os.path.exists(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            assert "testtemptool" in f.read()

        # Verify dynamic load registration was triggered
        assert mock_registry._register_module_ops.called
        
        # Verify the module is in sys.modules and callable
        module = sys.modules.get("ops.addons.test_temp_plugin")
        assert module is not None
        assert hasattr(module, "testtemptool")
        assert module.testtemptool("test") == "Processed test"

def test_download_plugin_default_url():
    client = PluginRegistryClient()
    # Manifest without download_url or url
    manifest = {
        "name": "test_temp_plugin",
        "version": "1.0.0"
    }
    
    urls_called = []
    def mock_get(url, *args, **kwargs):
        urls_called.append(url)
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "manifests" in url:
            resp.json.return_value = manifest
        else:
            resp.text = "# mock code"
        return resp

    with patch("requests.get", side_effect=mock_get):
        client.download_plugin("test_temp_plugin", "http://mock-registry.com")
        # Should construct default download URL: http://mock-registry.com/plugins/test_temp_plugin.py
        assert "http://mock-registry.com/plugins/test_temp_plugin.py" in urls_called

def test_download_plugin_network_error():
    client = PluginRegistryClient()
    manifest = {
        "name": "test_temp_plugin",
        "version": "1.0.0",
        "download_url": "http://mock-registry.com/plugins/test_temp_plugin.py"
    }
    
    def mock_get(url, *args, **kwargs):
        if "manifests" in url:
            resp = MagicMock()
            resp.json.return_value = manifest
            resp.raise_for_status = MagicMock()
            return resp
        raise requests.RequestException("Download failed")

    with patch("requests.get", side_effect=mock_get):
        with pytest.raises(AgentError) as exc_info:
            client.download_plugin("test_temp_plugin", "http://mock-registry.com")
        assert exc_info.value.code == "DOWNLOAD_PLUGIN_FAILED"

def test_download_plugin_io_error():
    client = PluginRegistryClient()
    manifest = {
        "name": "test_temp_plugin",
        "version": "1.0.0",
        "download_url": "http://mock-registry.com/plugins/test_temp_plugin.py"
    }

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "manifests" in url:
            resp.json.return_value = manifest
        else:
            resp.text = "# some code"
        return resp

    with patch("requests.get", side_effect=mock_get), \
         patch("builtins.open", side_effect=IOError("Permission denied")):
        with pytest.raises(AgentError) as exc_info:
            client.download_plugin("test_temp_plugin", "http://mock-registry.com")
        assert exc_info.value.code == "WRITE_PLUGIN_FAILED"

def test_download_plugin_load_error():
    client = PluginRegistryClient()
    manifest = {
        "name": "test_temp_plugin",
        "version": "1.0.0",
        "download_url": "http://mock-registry.com/plugins/test_temp_plugin.py"
    }

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "manifests" in url:
            resp.json.return_value = manifest
        else:
            resp.text = "# some code"
        return resp

    with patch("requests.get", side_effect=mock_get), \
         patch("importlib.util.spec_from_file_location", return_value=None):
        with pytest.raises(AgentError) as exc_info:
            client.download_plugin("test_temp_plugin", "http://mock-registry.com")
        assert exc_info.value.code == "LOAD_PLUGIN_FAILED"
        assert "Could not construct module spec" in exc_info.value.message

def test_download_plugin_generic_load_error():
    client = PluginRegistryClient()
    manifest = {
        "name": "test_temp_plugin",
        "version": "1.0.0",
        "download_url": "http://mock-registry.com/plugins/test_temp_plugin.py"
    }

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "manifests" in url:
            resp.json.return_value = manifest
        else:
            resp.text = "# some code"
        return resp

    with patch("requests.get", side_effect=mock_get), \
         patch("importlib.util.module_from_spec", side_effect=RuntimeError("Generic load fail")):
        with pytest.raises(AgentError) as exc_info:
            client.download_plugin("test_temp_plugin", "http://mock-registry.com")
        assert exc_info.value.code == "LOAD_PLUGIN_FAILED"
        assert "Failed to dynamically load" in exc_info.value.message
