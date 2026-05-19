import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if not line.startswith('from __future__') and not line.strip() == '':
            lines.insert(i, 'import sys\nfrom core.logger import get_logger\nlogger = get_logger(__name__)\n\n')
            break

    for i, line in enumerate(lines):
        if re.search(r'\bprint\(', line):
            if 'def ' in line:
                continue

            # Keep streaming tokens UX intact per code review feedback by using sys.stdout.write
            if 'end=\"\"' in line or 'flush=True' in line:
                # Replace print(...) with sys.stdout.write(...)
                lines[i] = re.sub(r'(?<!_)print\(', 'sys.stdout.write(', line)
                lines[i] = re.sub(r',\s*end=[\"\'][^\"\']*[\"\']', '', lines[i])
                lines[i] = re.sub(r',\s*flush=True', '', lines[i])

                # We need to append sys.stdout.flush() to keep the stream effect
                indent = len(lines[i]) - len(lines[i].lstrip())
                lines[i] = lines[i].rstrip() + '\n' + (' ' * indent) + 'sys.stdout.flush()\n'
            elif 'print()' in line:
                lines[i] = line.replace('print()', 'sys.stdout.write(\"\\n\")')
            else:
                lower = line.lower()
                level = "info"
                if "error" in lower or "fail" in lower or "stop" in lower:
                    level = "error"
                elif "warning" in lower or "rate limit" in lower or "retry" in lower:
                    level = "warning"
                elif "iteration" in lower:
                    level = "debug"

                lines[i] = re.sub(r'(?<!_)print\(', f'logger.{level}(', line)

    with open(filepath, 'w') as f:
        f.writelines(lines)

for f in ['core/runtime.py', 'core/runtime_ui.py', 'core/model_clients.py', 'core/guardrails.py', 'core/memory_manager.py', 'core/self_improvement.py']:
    process_file(f)

# Handle config_validator.py separately because of future imports
with open('core/config_validator.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if line.startswith('from __future__'):
        lines.insert(i+1, '\nimport sys\nfrom core.logger import get_logger\nlogger = get_logger(__name__)\n\n')
        break
for i, line in enumerate(lines):
    if re.search(r'\bprint\(', line) and 'def ' not in line:
        lower = line.lower()
        level = "info"
        if "error" in lower or "fail" in lower or "stop" in lower or "_err" in lower or "✗" in lower:
            level = "error"
        elif "warning" in lower or "rate limit" in lower or "_warn" in lower or "⚠" in lower:
            level = "warning"

        lines[i] = re.sub(r'(?<!_)print\(', f'logger.{level}(', line)
with open('core/config_validator.py', 'w') as f:
    f.writelines(lines)
