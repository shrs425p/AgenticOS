import os
import sys
import requests
import importlib.metadata
import importlib.util
from pathlib import Path
from packaging.specifiers import SpecifierSet
from core.exceptions import AgentError

class PluginRegistryClient:
    """Client for fetching, verifying dependencies, and downloading custom plugins from a remote registry."""
    
    def __init__(self, registry=None):
        """
        Initialize the plugin registry client.
        
        Args:
            registry: An optional active ToolRegistry instance to register downloaded tools.
        """
        self.registry = registry

    def fetch_plugin_manifest(self, name: str, registry_url: str) -> dict:
        """
        Fetches the plugin manifest from the remote registry.
        
        Args:
            name: The name of the plugin.
            registry_url: The base URL of the remote registry.
            
        Returns:
            dict: The parsed manifest JSON.
            
        Raises:
            AgentError: If the manifest cannot be fetched or parsed.
        """
        url = f"{registry_url.rstrip('/')}/manifests/{name}.json"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise AgentError(
                code="FETCH_MANIFEST_FAILED",
                message=f"Failed to fetch manifest for plugin '{name}' from '{url}': {e}",
                original_exception=e
            )
        except ValueError as e:
            raise AgentError(
                code="INVALID_MANIFEST",
                message=f"Failed to parse JSON manifest for plugin '{name}' from '{url}': {e}",
                original_exception=e
            )

    def verify_dependencies(self, manifest: dict) -> None:
        """
        Verifies that all dependencies in the plugin manifest are installed and satisfy version requirements.
        
        Args:
            manifest: The plugin manifest dictionary.
            
        Raises:
            AgentError: If a dependency is missing (MISSING_DEPENDENCY) or has an incompatible version (INCOMPATIBLE_VERSION).
        """
        dependencies = manifest.get("dependencies", {})
        if not isinstance(dependencies, dict):
            return

        for pkg, spec_str in dependencies.items():
            try:
                installed_ver = importlib.metadata.version(pkg)
            except importlib.metadata.PackageNotFoundError:
                raise AgentError(
                    code="MISSING_DEPENDENCY",
                    message=f"Required package '{pkg}' is not installed.",
                    suggestions=[f"Run: pip install {pkg}"]
                )

            try:
                spec = SpecifierSet(spec_str)
                if installed_ver not in spec:
                    raise AgentError(
                        code="INCOMPATIBLE_VERSION",
                        message=f"Package '{pkg}' version '{installed_ver}' does not satisfy requirement '{spec_str}'.",
                        suggestions=[f"Upgrade package: pip install --upgrade '{pkg}{spec_str}'"]
                    )
            except Exception as e:
                if isinstance(e, AgentError):
                    raise
                raise AgentError(
                    code="INCOMPATIBLE_VERSION",
                    message=f"Invalid dependency version specifier '{spec_str}' for package '{pkg}': {e}",
                    original_exception=e
                )

    def download_plugin(self, name: str, registry_url: str) -> str:
        """
        Downloads a plugin, verifies its dependencies, saves it to tools/plugins/{name}.py, and registers it.
        
        Args:
            name: The name of the plugin.
            registry_url: The base URL of the remote registry.
            
        Returns:
            str: The local file path to the installed plugin.
            
        Raises:
            AgentError: If download, validation, or loading fails.
        """
        manifest = self.fetch_plugin_manifest(name, registry_url)
        self.verify_dependencies(manifest)

        download_url = manifest.get("download_url") or manifest.get("url")
        if not download_url:
            download_url = f"{registry_url.rstrip('/')}/plugins/{name}.py"

        try:
            response = requests.get(download_url, timeout=15)
            response.raise_for_status()
            code_content = response.text
        except requests.RequestException as e:
            raise AgentError(
                code="DOWNLOAD_PLUGIN_FAILED",
                message=f"Failed to download plugin code for '{name}' from '{download_url}': {e}",
                original_exception=e
            )

        # Write downloaded files to tools/plugins/{name}.py
        plugin_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "tools", "plugins")
        )
        os.makedirs(plugin_dir, exist_ok=True)
        file_path = os.path.join(plugin_dir, f"{name}.py")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code_content)
        except IOError as e:
            raise AgentError(
                code="WRITE_PLUGIN_FAILED",
                message=f"Failed to write plugin to file path '{file_path}': {e}",
                original_exception=e
            )

        # Register the new tool in the active registry
        full_mod_name = f"tools.plugins.{name}"
        try:
            spec = importlib.util.spec_from_file_location(full_mod_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[full_mod_name] = module
                spec.loader.exec_module(module)
                
                if self.registry:
                    self.registry._register_module_tools(module)
            else:
                raise AgentError(
                    code="LOAD_PLUGIN_FAILED",
                    message=f"Could not construct module spec for '{name}' from '{file_path}'"
                )
        except Exception as e:
            if isinstance(e, AgentError):
                raise
            raise AgentError(
                code="LOAD_PLUGIN_FAILED",
                message=f"Failed to dynamically load downloaded plugin '{name}': {e}",
                original_exception=e
            )

        return file_path
