import ast
import os

def get_public_functions_missing_docstrings(directory):
    missing = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        content = f.read()
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                if not node.name.startswith('_'): # public
                                    is_prop = any(isinstance(dec, ast.Name) and dec.id == 'property' for dec in node.decorator_list)
                                    is_setter = any(isinstance(dec, ast.Attribute) and dec.attr == 'setter' for dec in node.decorator_list)
                                    if is_prop or is_setter:
                                        continue
                                    if not ast.get_docstring(node):
                                        missing.append((path, node.name))
                    except Exception as e:
                        print(f"Error parsing {path}: {e}")
    return missing

missing_core = get_public_functions_missing_docstrings('core')
missing_tools = get_public_functions_missing_docstrings('tools')

print(f"Missing in core: {len(missing_core)}")
for path, func in missing_core:
    print(f"  {path}: {func}")

print(f"Missing in tools: {len(missing_tools)}")
for path, func in missing_tools:
    print(f"  {path}: {func}")
