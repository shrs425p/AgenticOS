import ast
import os

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines()
    tree = ast.parse(content)

    insertions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not node.name.startswith('_'): # public
                is_prop = any(isinstance(dec, ast.Name) and dec.id == 'property' for dec in node.decorator_list)
                is_setter = any(isinstance(dec, ast.Attribute) and dec.attr == 'setter' for dec in node.decorator_list)
                if is_prop or is_setter:
                    continue

                if not ast.get_docstring(node):
                    # We need to insert a docstring.
                    # Find the colon line
                    # it could be multiline def
                    end_lineno = node.body[0].lineno - 1
                    # let's just insert before the first statement
                    indent = ' ' * getattr(node.body[0], 'col_offset', 4)
                    insertions.append((end_lineno, f'{indent}"""{node.name} function."""'))

    if not insertions:
        return

    # Sort backwards to avoid messing up line numbers
    insertions.sort(key=lambda x: x[0], reverse=True)
    for line_idx, docstring in insertions:
        lines.insert(line_idx, docstring)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

for root, _, files in os.walk('core'):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))

for root, _, files in os.walk('tools'):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
