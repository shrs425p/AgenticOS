# Daily Memory Schema and State Log
**Date:** 2026-05-16

## 1. Database Tables Found
- **sessions**: session_id (TEXT PRIMARY KEY), created_at (TEXT), updated_at (TEXT), summary (TEXT)
- **preferences**: key (TEXT PRIMARY KEY), value (TEXT), updated_at (TEXT)
- **tasks**: task_id (TEXT PRIMARY KEY), session_id (TEXT), goal (TEXT), status (TEXT), created_at (TEXT), updated_at (TEXT), final_answer (TEXT), next_steps (TEXT), summary (TEXT)
- **tool_events**: id (INTEGER PRIMARY KEY), session_id (TEXT), tool_name (TEXT), tool_args (TEXT), observation (TEXT), created_at (TEXT)
- **artifacts**: id (INTEGER PRIMARY KEY), session_id (TEXT), kind (TEXT), action (TEXT), value (TEXT), created_at (TEXT)
- **outcomes**: session_id (TEXT PRIMARY KEY), final_answer (TEXT), next_steps (TEXT), updated_at (TEXT)
- **messages**: id (INTEGER PRIMARY KEY), session_id (TEXT), role (TEXT), content (TEXT), created_at (TEXT)

## 2. Raw SQL Strings (Security Risk)
- `None found`

## 3. Missing Indexes
The following columns are frequently queried but missing indexes:
- `messages.role`
- `sessions.session_id` (Already a PRIMARY KEY)
- `messages.session_id` (Already indexed with `messages.id`)

## 4. Unused Config Values
- `cache.root_dir`

## 5. Missing Config Values
- `blocklist` (Found in `core/url_presets.py`)

## 6. Duplicate Config Values
- `agent.provider`
- `agent.stream`
- `agent.workspace`
- `autonomy.autopilot`
- `autonomy.power_mode`
- `autonomy.startup_model_prompt`
- `autonomy.startup_provider_prompt`
- `cloud.nvidia.model`
- `logging.audit_enabled`
- `logging.audit_format`
- `performance.max_pref_chars`
- `performance.max_pref_items`

## 7. Global Mutable State Found
- `_memory_manager` in `core/memory_manager.py` (initialized globally)

## 8. Memory Health
**WARNING**
Memory health is a warning. There is global mutable state (`_memory_manager`) which is non-ideal for isolation or testability, and unused configuration values that clutter the system.
