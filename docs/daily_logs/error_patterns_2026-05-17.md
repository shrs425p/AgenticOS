# Error Patterns - 2026-05-17

## Exception Block Summary
- Specific: 103
- Generic: 234
- Bare: 0

## Top 5 Error Patterns
- `Invalid selection.` (Count: 2)
- `Selection required.` (Count: 2)
- `Failed to save commitments: {var}` (Count: 1)
- `Failed to load commitments: {var}` (Count: 1)
- `ollama rate limit hit (attempt %d). Waiting %.2fs` (Count: 1)

## Vague Error Messages
- core\runtime.py:1141 - `Invalid selection.`
- core\runtime.py:1213 - `Invalid selection.`
- core\runtime.py:315 - `Failed to reload: {var}`
- core\runtime.py:1140 - `Selection required.`
- core\runtime.py:1212 - `Selection required.`
- core\runtime.py:1481 - `Unexpected error: {var}`
- core\runtime.py:1246 - `No models found.`
- core\runtime.py:1315 - `memory: Error: {var}`
- core\runtime.py:1334 - `audit_dir writable: Error: {var}`
- core\runtime.py:1348 - `provider check: Error: {var}`

## Potentially Sensitive Error Messages

## Old TODO/FIXME Comments (> 7 days)

## Health: GOOD

## Flags compared to yesterday
- NEW vague error messages introduced today:
-   - core\runtime.py:1246 - `No models found.`
-   - core\runtime.py:1481 - `Unexpected error: {var}`
-   - core\runtime.py:1212 - `Selection required.`
-   - core\runtime.py:1140 - `Selection required.`
-   - core\runtime.py:315 - `Failed to reload: {var}`
-   - core\runtime.py:1348 - `provider check: Error: {var}`
-   - core\runtime.py:1334 - `audit_dir writable: Error: {var}`
-   - core\runtime.py:1141 - `Invalid selection.`
-   - core\runtime.py:1315 - `memory: Error: {var}`
-   - core\runtime.py:1213 - `Invalid selection.`
