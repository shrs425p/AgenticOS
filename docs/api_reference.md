<a id="core"></a>

# core

Core AgenticOs runtime package.

Import concrete modules directly, for example:
- core.runtime
- core.session_memory

<a id="core.tool_registry"></a>

# core.tool_registry

Tool registration and dispatch for the AgenticOs runtime.

<a id="core.logger"></a>

# core.logger

Centralized logging factory for AgenticOs.

<a id="core.logger.get_logger"></a>

#### get_logger

```python
def get_logger(name: str) -> logging.Logger
```

Returns a configured logger with standard formatting.

**Arguments**:

- `name` - The name of the logger to construct or retrieve.

**Returns**:

- `logging.Logger` - A configured, standard-compliant logger.

<a id="core.tool_base"></a>

# core.tool_base

Base classes and decorators for AgenticOs tools.

<a id="core.tool_base.tool"></a>

#### tool

```python
def tool(name: str = None,
         desc: str = None,
         category: str = "general",
         version: str = "1.0.0",
         author: str = "AgenticOs")
```

Decorator to mark a function as a tool for AgenticOs.

<a id="core.memory_manager"></a>

# core.memory_manager

Enhanced memory management system for AgenticOs.
Provides long-term memory consolidation, daily logging, and knowledge retention.

<a id="core.memory_manager.MemoryManager"></a>

## MemoryManager Objects

```python
class MemoryManager()
```

Manages long-term memory consolidation and daily logging for AgenticOs.

<a id="core.memory_manager.MemoryManager.register_commitment"></a>

#### register_commitment

```python
def register_commitment(text: str, due_date: Optional[str] = None)
```

Register a new commitment/follow-up.

<a id="core.memory_manager.MemoryManager.get_active_commitments"></a>

#### get_active_commitments

```python
def get_active_commitments() -> str
```

Get all pending commitments formatted for system prompt.

<a id="core.memory_manager.MemoryManager.complete_commitment"></a>

#### complete_commitment

```python
def complete_commitment(commitment_id: str)
```

Mark a commitment as completed.

<a id="core.memory_manager.MemoryManager.get_relevant_context"></a>

#### get_relevant_context

```python
def get_relevant_context(query: str, limit: int = 3) -> str
```

Retrieve relevant snippets from long-term memory for pre-flight injection (Active Recall).

<a id="core.memory_manager.MemoryManager.get_daily_memory_file"></a>

#### get_daily_memory_file

```python
def get_daily_memory_file(date: Optional[datetime] = None) -> Path
```

Get the memory file for a specific date (defaults to today).

<a id="core.memory_manager.MemoryManager.log_daily_event"></a>

#### log_daily_event

```python
def log_daily_event(event_type: str,
                    description: str,
                    metadata: Optional[Dict] = None)
```

Log an event to the daily memory file.

<a id="core.memory_manager.MemoryManager.log_task_completion"></a>

#### log_task_completion

```python
def log_task_completion(task_goal: str,
                        final_answer: str,
                        tools_used: List[str],
                        success: bool,
                        duration: float,
                        metadata: Optional[Dict] = None)
```

Log a completed task to daily memory and prepare for consolidation.

<a id="core.memory_manager.MemoryManager.consolidate_long_term_memory"></a>

#### consolidate_long_term_memory

```python
def consolidate_long_term_memory()
```

Consolidate recent task experiences into long-term memory.

<a id="core.memory_manager.MemoryManager.get_memory_stats"></a>

#### get_memory_stats

```python
def get_memory_stats() -> Dict[str, Any]
```

Get statistics about the memory system.

<a id="core.memory_manager.MemoryManager.cleanup_old_memories"></a>

#### cleanup_old_memories

```python
def cleanup_old_memories(days_to_keep: int = 30)
```

Clean up memory files older than specified days.

<a id="core.memory_manager.initialize_memory_manager"></a>

#### initialize_memory_manager

```python
def initialize_memory_manager(workspace_root: str,
                              llm_client: Optional[Any] = None,
                              cfg: Optional[Dict] = None) -> MemoryManager
```

Initialize the global memory manager.

<a id="core.memory_manager.get_memory_manager"></a>

#### get_memory_manager

```python
def get_memory_manager() -> Optional[MemoryManager]
```

Get the global memory manager instance.

<a id="core.memory_manager.log_task_completion"></a>

#### log_task_completion

```python
def log_task_completion(goal: str,
                        final_answer: str,
                        tools_used: List[str],
                        success: bool,
                        duration: float,
                        metadata: Optional[Dict] = None)
```

Convenience function to log task completion.

<a id="core.memory_manager.log_daily_event"></a>

#### log_daily_event

```python
def log_daily_event(event_type: str,
                    description: str,
                    metadata: Optional[Dict] = None)
```

Convenience function to log daily events.

<a id="core.memory_manager.get_memory_stats"></a>

#### get_memory_stats

```python
def get_memory_stats() -> Dict[str, Any]
```

Get memory system statistics.

<a id="core.memory_manager.consolidate_memory"></a>

#### consolidate_memory

```python
def consolidate_memory()
```

Trigger manual memory consolidation.

<a id="core.memory_manager.cleanup_old_memories"></a>

#### cleanup_old_memories

```python
def cleanup_old_memories(days_to_keep: int = 30) -> int
```

Clean up old memory files.

<a id="core.self_provisioner"></a>

# core.self_provisioner

Autonomous Self-Provisioning and Auto-Compiler Engine.

<a id="core.self_provisioner.refresh_path"></a>

#### refresh_path

```python
def refresh_path() -> None
```

Dynamically refreshes the active os.environ['PATH'] with package manager links.

<a id="core.self_provisioner.self_provision_command"></a>

#### self_provision_command

```python
def self_provision_command(command_name: str) -> bool
```

Probes if the command is installed, installs if missing, and generates wrapper tool.

**Arguments**:

- `command_name` _str_ - Name of the command binary to verify/install.

**Returns**:

- `bool` - True if command is available and wrapper generated, False otherwise.

<a id="core.event_bus"></a>

# core.event_bus

Asynchronous OS Hardware Event Bus and telemetry polling daemon.

<!-- If you have Liquid or Jekyll variables below, ensure they are properly closed. -->

<a id="core.config_types"></a>

# core.config_types

TypedDict definitions for configuration sections (static typing helpers).

These types are intentionally lightweight and `total=False` so they can be
used as hints without enforcing strict runtime checks. They improve IDE
completion and serve as a single place to document common config keys.

<a id="core.audit_logger"></a>

# core.audit_logger

Structured audit logging (no chat content).

Writes separate JSONL logs for:
- session events (start/stop, provider/model)
- tool calls (timing, args summary, validation, success)
- errors

#### infer_success

```python
def infer_success(tool_result: str) -> bool
```

Heuristic: treat explicit Error/Permission/Not found as failure.

<!-- Remainder of file omitted for brevity -->
