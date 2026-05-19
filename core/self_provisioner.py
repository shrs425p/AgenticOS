"""Autonomous Self-Provisioning and Auto-Compiler Engine."""
import os
import shutil
import logging
import platform

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(BASE_DIR, "tools", "plugins")

def refresh_path() -> None:
    """Dynamically refreshes the active os.environ['PATH'] with package manager links."""
    if platform.system() == "Windows":
        user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        winget_links = os.path.join(user_profile, "AppData", "Local", "Microsoft", "WinGet", "Links")
        choco_links = os.path.join(os.environ.get("ProgramData", os.environ.get("SystemDrive", "C:") + "\\ProgramData"), "chocolatey", "bin")
        
        paths = os.environ.get("PATH", "").split(os.pathsep)
        updated = False
        for p in [winget_links, choco_links]:
            if os.path.isdir(p) and p not in paths:
                paths.append(p)
                updated = True
        if updated:
            os.environ["PATH"] = os.pathsep.join(paths)

def self_provision_command(command_name: str) -> bool:
    """Probes if the command is installed, installs if missing, and generates wrapper tool.

    Args:
        command_name (str): Name of the command binary to verify/install.

    Returns:
        bool: True if command is available and wrapper generated, False otherwise.
    """
    cmd_clean = command_name.lower().strip()
    if not cmd_clean:
        return False

    refresh_path()

    # Check path first
    if shutil.which(cmd_clean):
        return True

    logging.info(f"Self-provisioner: Command '{cmd_clean}' not found. Attempting auto-installation...")

    # Run the installation
    try:
        from tools.plugins.sys_package_installer import install_system_package
        res = install_system_package(cmd_clean)
    except Exception as e:
        logging.error(f"Self-provisioner: Failed to import/execute install_system_package: {e}")
        return False

    if "Success" not in res:
        logging.warning(f"Self-provisioner: Installation failed for '{cmd_clean}': {res}")
        return False

    refresh_path()

    # Re-verify path after installation
    if not shutil.which(cmd_clean):
        logging.warning(f"Self-provisioner: Command '{cmd_clean}' installed but not found on system PATH.")
        return False

    # Generate the plugin wrapper file
    plugin_file = os.path.join(PLUGINS_DIR, f"auto_{cmd_clean}.py")

    # Avoid overwriting custom files
    if os.path.exists(plugin_file):
        logging.info(f"Self-provisioner: Plugin wrapper file {plugin_file} already exists.")
        return True

    wrapper_code = f'''"""Auto-generated package wrapper plugin for {cmd_clean}."""
import subprocess
import shutil
import shlex
import platform
from core.tool_base import tool

@tool(name="auto_{cmd_clean}", desc="Auto-generated system tool to run the {cmd_clean} command. Args: args (a string of command arguments)", category="Plugins")
def auto_{cmd_clean}(args: str) -> str:
    """Runs the dynamically installed '{cmd_clean}' utility with the provided arguments.

    Args:
        args (str): Arguments to pass to {cmd_clean}.

    Returns:
        str: Standard output or standard error of the execution.
    """
    try:
        cmd_path = shutil.which("{cmd_clean}")
        if not cmd_path:
            return "Error: '{cmd_clean}' is not currently installed or found on system PATH."

        if platform.system() == "Windows":
            cmd = f"{{cmd_path}} {{args}}"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        else:
            cmd = [cmd_path] + shlex.split(args)
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()

        parts = []
        if out:
            parts.append(out)
        if err:
            parts.append(f"[stderr]\\n{{err}}")
        if not parts:
            parts.append(f"(exit code: {{res.returncode}})")
        else:
            parts.append(f"\\n[exit: {{res.returncode}}]")
        return "\\n".join(parts)
    except Exception as e:
        return f"Error running '{cmd_clean}': {{type(e).__name__}}: {{e}}"
'''

    try:
        os.makedirs(PLUGINS_DIR, exist_ok=True)
        with open(plugin_file, "w", encoding="utf-8") as f:
            f.write(wrapper_code)
        logging.info(f"Self-provisioner: Successfully generated wrapper plugin: {plugin_file}")
        return True
    except Exception as e:
        logging.error(f"Self-provisioner: Failed to write plugin wrapper for '{cmd_clean}': {e}")
        return False
