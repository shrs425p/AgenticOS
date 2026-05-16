# Error Patterns - 2026-05-16

## Exception Block Summary
- Specific: 45
- Generic: 253
- Bare: 0

## Top 5 Error Patterns
- `Invalid selection.` (Count: 2)
- `Selection required.` (Count: 2)
- `No models found for {var} .` (Count: 1)
- `Failed to reload: {var}` (Count: 1)
- `Ollama not reachable. Start with: `ollama serve`` (Count: 1)

## Vague Error Messages
- core/runtime.py:1124 - `Invalid selection.`
- core/runtime.py:1197 - `Invalid selection.`
- core/runtime.py:302 - `Failed to reload: {var}`
- core/runtime.py:1123 - `Selection required.`
- core/runtime.py:1196 - `Selection required.`
- core/runtime.py:1470 - `Unexpected error: {var}`
- core/runtime.py:1230 - `No models found.`
- core/runtime.py:1299 - `memory: Error: {var}`
- core/runtime.py:1318 - `audit_dir writable: Error: {var}`
- core/runtime.py:1332 - `provider check: Error: {var}`

## Potentially Sensitive Error Messages

## Old TODO/FIXME Comments (> 7 days)

## Health: GOOD
