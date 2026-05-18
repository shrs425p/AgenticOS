# Error Patterns - 2026-05-18

## Exception Block Summary
- Specific: 110
- Generic: 257
- Bare: 0

## Top 5 Error Patterns
- `Invalid selection.` (Count: 2)
- `Selection required.` (Count: 2)
- `Failed to auto-inject file %s: %s` (Count: 1)
- `LLM context compaction failed, falling back to truncation: %s` (Count: 1)
- `Event Bus: Listener callback failed: {var}` (Count: 1)

## Vague Error Messages
- core\runtime.py:1147 - `Invalid selection.`
- core\runtime.py:1219 - `Invalid selection.`
- core\runtime.py:315 - `Failed to reload: {var}`
- core\runtime.py:1146 - `Selection required.`
- core\runtime.py:1218 - `Selection required.`
- core\runtime.py:1487 - `Unexpected error: {var}`
- core\runtime.py:1252 - `No models found.`
- core\runtime.py:1321 - `memory: Error: {var}`
- core\runtime.py:1340 - `audit_dir writable: Error: {var}`
- core\runtime.py:1354 - `provider check: Error: {var}`

## Potentially Sensitive Error Messages

## Old TODO/FIXME Comments (> 7 days)

## Health: GOOD
