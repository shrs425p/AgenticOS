import os
import sys
import inspect
import importlib.util
from typing import get_type_hints

def validate_plugins(plugin_dir: str):
    """
    Validates all plugins in the given directory.
    A plugin must:
    1. Be decorated with @tool (have _is_tool attribute)
    2. Have a name (_tool_name)
    3. Have a description (_tool_desc)
    4. Be a callable function (acts as the run method)
    5. Return a typed result
    """
    errors = []

    if not os.path.exists(plugin_dir):
        print(f"Error: Plugin directory '{plugin_dir}' does not exist.")
        sys.exit(1)

    for root, _, files in os.walk(plugin_dir):
        for filename in files:
            if filename.endswith(".py") and filename != "__init__.py":
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, plugin_dir)
                mod_path = rel_path[:-3].replace(os.path.sep, ".")
                full_mod_name = f"ops.addons.{mod_path}"

                try:
                    spec = importlib.util.spec_from_file_location(full_mod_name, file_path)
                    if not spec or not spec.loader:
                        errors.append(f"{file_path}: Failed to load spec.")
                        continue

                    module = importlib.util.module_from_spec(spec)
                    # We need to temporarily set the module in sys.modules so imports inside the plugin work
                    sys.modules[full_mod_name] = module
                    spec.loader.exec_module(module)

                    found_tool = False
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if callable(attr) and getattr(attr, "_is_tool", False):
                            found_tool = True

                            # 1. Must have a name
                            name = getattr(attr, "_tool_name", None)
                            if not name:
                                errors.append(f"{file_path} - {attr_name}: Missing '_tool_name' (name).")

                            # 2. Must have a description
                            desc = getattr(attr, "_tool_desc", None)
                            if not desc:
                                errors.append(f"{file_path} - {attr_name}: Missing '_tool_desc' (desc/description).")

                            # 3. Must be a callable run method
                            if not hasattr(attr, "__call__"):
                                errors.append(f"{file_path} - {attr_name}: Is not callable (missing run() method equivalent).")

                            # 4. Must return a typed result
                            try:
                                hints = get_type_hints(attr)
                                if "return" not in hints:
                                    # Fallback: check if the AST or inspect signature has it
                                    sig = inspect.signature(attr)
                                    if sig.return_annotation is inspect.Signature.empty:
                                        errors.append(f"{file_path} - {attr_name}: Missing return type annotation.")
                            except Exception:
                                # Sometimes get_type_hints fails on complex types without globals
                                sig = inspect.signature(attr)
                                if sig.return_annotation is inspect.Signature.empty:
                                    errors.append(f"{file_path} - {attr_name}: Missing return type annotation or could not evaluate type hints.")

                    if not found_tool:
                        errors.append(f"{file_path}: No @tool functions found.")

                except Exception as e:
                    errors.append(f"{file_path}: Failed to import or process module. Error: {e}")

    if errors:
        print("Plugin Validation Failed:\n")
        for error in errors:
            print(f" - {error}")
        sys.exit(1)
    else:
        print("All plugins validated successfully.")
        sys.exit(0)

if __name__ == "__main__":
    # Ensure project root is in sys.path so 'kernel' and other top-level modules can be imported
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
    validate_plugins(plugin_dir)
