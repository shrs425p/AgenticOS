<a id="core"></a>

# core

Core AgenticOs runtime package.

Import concrete modules directly, for example:
- core.runtime
- core.session_memory

<a id="core.tool_registry"></a>

# core.tool\_registry

Tool registration and dispatch for the AgenticOs runtime.

<a id="core.logger"></a>

# core.logger

Centralized logging factory for AgenticOs.

<a id="core.logger.get_logger"></a>

#### get\_logger

```python
def get_logger(name: str) -> logging.Logger
```

Returns a configured logger with standard formatting.

**Arguments**:

- `name` - The name of the logger to construct or retrieve.


**Returns**:

- `logging.Logger` - A configured, standard-compliant logger.

<a id="core.tool_base"></a>

# core.tool\_base

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

# core.memory\_manager

Enhanced memory management system for AgenticOs.
Provides long-term memory consolidation, daily logging, and knowledge retention.

<a id="core.memory_manager.MemoryManager"></a>

## MemoryManager Objects

```python
class MemoryManager()
```

Manages long-term memory consolidation and daily logging for AgenticOs.

<a id="core.memory_manager.MemoryManager.register_commitment"></a>

#### register\_commitment

```python
def register_commitment(text: str, due_date: Optional[str] = None)
```

Register a new commitment/follow-up.

<a id="core.memory_manager.MemoryManager.get_active_commitments"></a>

#### get\_active\_commitments

```python
def get_active_commitments() -> str
```

Get all pending commitments formatted for system prompt.

<a id="core.memory_manager.MemoryManager.complete_commitment"></a>

#### complete\_commitment

```python
def complete_commitment(commitment_id: str)
```

Mark a commitment as completed.

<a id="core.memory_manager.MemoryManager.get_relevant_context"></a>

#### get\_relevant\_context

```python
def get_relevant_context(query: str, limit: int = 3) -> str
```

Retrieve relevant snippets from long-term memory for pre-flight injection (Active Recall).

<a id="core.memory_manager.MemoryManager.get_daily_memory_file"></a>

#### get\_daily\_memory\_file

```python
def get_daily_memory_file(date: Optional[datetime] = None) -> Path
```

Get the memory file for a specific date (defaults to today).

<a id="core.memory_manager.MemoryManager.log_daily_event"></a>

#### log\_daily\_event

```python
def log_daily_event(event_type: str,
                    description: str,
                    metadata: Optional[Dict] = None)
```

Log an event to the daily memory file.

<a id="core.memory_manager.MemoryManager.log_task_completion"></a>

#### log\_task\_completion

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

#### consolidate\_long\_term\_memory

```python
def consolidate_long_term_memory()
```

Consolidate recent task experiences into long-term memory.

<a id="core.memory_manager.MemoryManager.get_memory_stats"></a>

#### get\_memory\_stats

```python
def get_memory_stats() -> Dict[str, Any]
```

Get statistics about the memory system.

<a id="core.memory_manager.MemoryManager.cleanup_old_memories"></a>

#### cleanup\_old\_memories

```python
def cleanup_old_memories(days_to_keep: int = 30)
```

Clean up memory files older than specified days.

<a id="core.memory_manager.initialize_memory_manager"></a>

#### initialize\_memory\_manager

```python
def initialize_memory_manager(workspace_root: str,
                              llm_client: Optional[Any] = None,
                              cfg: Optional[Dict] = None) -> MemoryManager
```

Initialize the global memory manager.

<a id="core.memory_manager.get_memory_manager"></a>

#### get\_memory\_manager

```python
def get_memory_manager() -> Optional[MemoryManager]
```

Get the global memory manager instance.

<a id="core.memory_manager.log_task_completion"></a>

#### log\_task\_completion

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

#### log\_daily\_event

```python
def log_daily_event(event_type: str,
                    description: str,
                    metadata: Optional[Dict] = None)
```

Convenience function to log daily events.

<a id="core.memory_manager.get_memory_stats"></a>

#### get\_memory\_stats

```python
def get_memory_stats() -> Dict[str, Any]
```

Get memory system statistics.

<a id="core.memory_manager.consolidate_memory"></a>

#### consolidate\_memory

```python
def consolidate_memory()
```

Trigger manual memory consolidation.

<a id="core.memory_manager.cleanup_old_memories"></a>

#### cleanup\_old\_memories

```python
def cleanup_old_memories(days_to_keep: int = 30) -> int
```

Clean up old memory files.

<a id="core.self_provisioner"></a>

# core.self\_provisioner

Autonomous Self-Provisioning and Auto-Compiler Engine.

<a id="core.self_provisioner.refresh_path"></a>

#### refresh\_path

```python
def refresh_path() -> None
```

Dynamically refreshes the active os.environ['PATH'] with package manager links.

<a id="core.self_provisioner.self_provision_command"></a>

#### self\_provision\_command

```python
def self_provision_command(command_name: str) -> bool
```

Probes if the command is installed, installs if missing, and generates wrapper tool.

**Arguments**:

- `command_name` _str_ - Name of the command binary to verify/install.


**Returns**:

- `bool` - True if command is available and wrapper generated, False otherwise.

<a id="core.event_bus"></a>

# core.event\_bus

Asynchronous OS Hardware Event Bus and telemetry polling daemon.

<a id="core.config_types"></a>

# core.config\_types

TypedDict definitions for configuration sections (static typing helpers).

These types are intentionally lightweight and `total=False` so they can be
used as hints without enforcing strict runtime checks. They improve IDE
completion and serve as a single place to document common config keys.

<a id="core.audit_logger"></a>

# core.audit\_logger

Structured audit logging (no chat content).

Writes separate JSONL logs for:
- session events (start/stop, provider/model)
- tool calls (timing, args summary, validation, success)
- errors

<a id="core.audit_logger.infer_success"></a>

#### infer\_success

```python
def infer_success(tool_result: str) -> bool
```

Heuristic: treat explicit Error/Permission/Not found as failure.

<a id="core.runtime_config"></a>

# core.runtime\_config

Config and path helpers for the AgenticOs runtime.

<a id="core.runtime_config.get_path"></a>

#### get\_path

```python
def get_path(rel_path: str) -> str
```

get_path function.

<a id="core.runtime_config.resolve_local_path"></a>

#### resolve\_local\_path

```python
def resolve_local_path(path: str, default: str = "") -> str
```

resolve_local_path function.

<a id="core.runtime_config.load_config"></a>

#### load\_config

```python
def load_config(path: str = None) -> ConfigDict
```

load_config function.

<a id="core.retry"></a>

# core.retry

Simple retry/backoff helper used across model clients.

<a id="core.retry.retry_call"></a>

#### retry\_call

```python
def retry_call(
    fn: Callable,
    max_retries: int = 5,
    base_delay: float = 5.0,
    retry_on_exception: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[int, Exception, float],
                                None]] = None) -> object
```

Call `fn()` with exponential backoff.

- `retry_on_exception(exc)` returns True to retry, False to re-raise immediately.
- `on_retry(attempt, exc, delay)` is called before sleeping.

<a id="core.runtime_ui"></a>

# core.runtime\_ui

UI helpers and response parsing for the AgenticOs runtime.

<a id="core.runtime_ui.typewriter_print"></a>

#### typewriter\_print

```python
def typewriter_print(text: str, delay: float = 0.002, color: str = "")
```

typewriter_print function.

<a id="core.runtime_ui.pulse_line"></a>

#### pulse\_line

```python
def pulse_line(length: int = 60, char: str = "=")
```

Animate a line with a breathing color effect.

<a id="core.runtime_ui.banner"></a>

#### banner

```python
def banner(cfg: dict = None)
```

banner function.

<a id="core.runtime_ui.parse_actions"></a>

#### parse\_actions

```python
def parse_actions(text: str) -> list[tuple]
```

Extract one or more actions from model output.

Supported formats:
- ACTION: tool | arg1 | arg2
- ACTION: {"tool": "...", "args": {...}}
- ACTION: tool(arg1, arg2)

<a id="core.runtime_ui.parse_action"></a>

#### parse\_action

```python
def parse_action(text: str) -> Optional[tuple]
```

Deprecated: use parse_actions instead. Returns the first action found.

<a id="core.runtime_ui.has_final_answer"></a>

#### has\_final\_answer

```python
def has_final_answer(text: str) -> bool
```

has_final_answer function.

<a id="core.runtime_ui.print_section"></a>

#### print\_section

```python
def print_section(label: str,
                  content: str,
                  color: str = C.CYAN,
                  max_len: int = 1000)
```

print_section function.

<a id="core.runtime_ui.print_action"></a>

#### print\_action

```python
def print_action(tool: str, args, symbol: str = "[*]")
```

print_action function.

<a id="core.runtime_ui.print_observation"></a>

#### print\_observation

```python
def print_observation(result: str, max_len: int = 600)
```

print_observation function.

<a id="core.runtime_ui.print_error"></a>

#### print\_error

```python
def print_error(msg: str)
```

print_error function.

<a id="core.runtime_ui.print_warning"></a>

#### print\_warning

```python
def print_warning(msg: str)
```

print_warning function.

<a id="core.runtime_ui.print_info"></a>

#### print\_info

```python
def print_info(msg: str)
```

print_info function.

<a id="core.runtime_ui.print_success"></a>

#### print\_success

```python
def print_success(msg: str)
```

print_success function.

<a id="core.task_tracker"></a>

# core.task\_tracker

Task tracking helpers for autonomous runs.

<a id="core.model_clients"></a>

# core.model\_clients

Model client adapters for Ollama and Nvidia NIM.

<a id="core.model_clients.GeminiClient"></a>

## GeminiClient Objects

```python
class GeminiClient()
```

Google Gemini API client using the google-genai SDK.

<a id="core.model_clients.GeminiClient.list_models"></a>

#### list\_models

```python
def list_models() -> list
```

list_models function.

<a id="core.model_clients.GeminiClient.chat"></a>

#### chat

```python
def chat(messages: list, system: str = "") -> str
```

chat function.

<a id="core.model_clients.GroqClient"></a>

## GroqClient Objects

```python
class GroqClient()
```

Groq API client using the official groq SDK.

<a id="core.model_clients.GroqClient.list_models"></a>

#### list\_models

```python
def list_models() -> list
```

list_models function.

<a id="core.model_clients.GroqClient.chat"></a>

#### chat

```python
def chat(messages: list, system: str = "") -> str
```

chat function.

<a id="core.model_clients.OpenAICompatibleClient"></a>

## OpenAICompatibleClient Objects

```python
class OpenAICompatibleClient()
```

Base class for OpenAI, OpenRouter, and GitHub Models.

<a id="core.model_clients.OpenAICompatibleClient.list_models"></a>

#### list\_models

```python
def list_models() -> list
```

list_models function.

<a id="core.model_clients.OpenAICompatibleClient.chat"></a>

#### chat

```python
def chat(messages: list, system: str = "") -> str
```

chat function.

<a id="core.model_clients.TieredClient"></a>

## TieredClient Objects

```python
class TieredClient()
```

Wraps multiple model clients and provides automatic failover.

If the primary client raises an exception during `chat()`, the TieredClient
automatically tries the next client in the tier list.  This ensures near-100%
uptime across providers.

Usage:
    primary = OllamaClient(cfg)
    fallbacks = [GeminiClient(cfg), GroqClient(cfg)]
    client = TieredClient(primary, fallbacks)
    response = client.chat(messages, system="...")

<a id="core.model_clients.TieredClient.provider"></a>

#### provider

```python
@property
def provider()
```

provider function.

<a id="core.model_clients.TieredClient.model"></a>

#### model

```python
@property
def model()
```

model function.

<a id="core.model_clients.TieredClient.model"></a>

#### model

```python
@model.setter
def model(value)
```

model function.

<a id="core.model_clients.TieredClient.last_list_error"></a>

#### last\_list\_error

```python
@property
def last_list_error()
```

last_list_error function.

<a id="core.model_clients.TieredClient.last_list_error"></a>

#### last\_list\_error

```python
@last_list_error.setter
def last_list_error(value)
```

last_list_error function.

<a id="core.model_clients.TieredClient.list_models"></a>

#### list\_models

```python
def list_models() -> list
```

list_models function.

<a id="core.model_clients.TieredClient.chat"></a>

#### chat

```python
def chat(messages: list, system: str = "") -> str
```

Try the active client; on failure, cascade through fallbacks.

<a id="core.model_clients.TieredClient.get_active_provider"></a>

#### get\_active\_provider

```python
def get_active_provider() -> str
```

Return the currently active provider name.

<a id="core.model_clients.TieredClient.get_failure_stats"></a>

#### get\_failure\_stats

```python
def get_failure_stats() -> dict
```

Return per-provider failure counts.

<a id="core.config_validator"></a>

# core.config\_validator

Startup config validator for AgenticOs.

Validates the fully-merged config dict (root config.yaml + config/*.yaml layers)
and emits structured warnings for missing or clearly invalid keys.

Design goals
------------
* Never crash the agent — all findings are warnings, not exceptions.
* Be layered-config-aware: only flag keys that are absent *after* all layers
  have been merged, so users aren't penalised for relying on defaults.
* Surface actionable hints, not raw key paths.

<a id="core.config_validator.validate_config"></a>

#### validate\_config

```python
def validate_config(merged_cfg: dict,
                    *,
                    root_cfg: Optional[dict] = None) -> ValidationResult
```

Run all checks against the fully-merged config.

Parameters
----------
merged_cfg:
    The dict returned by ``load_config()`` after all layer merges.
root_cfg:
    (Optional) The raw dict loaded *only* from the root ``config.yaml``
    before merging.  When supplied, unknown-key detection is enabled.

Returns
-------
ValidationResult
    Contains a list of :class:`ConfigIssue` instances.

<a id="core.config_validator.warn_config_issues"></a>

#### warn\_config\_issues

```python
def warn_config_issues(merged_cfg: dict,
                       *,
                       root_cfg: Optional[dict] = None,
                       quiet: bool = False) -> ValidationResult
```

Validate and print warnings to stdout.

Call this once at startup.  Tries to use AgenticOs's own print helpers
so the output blends in with the banner; falls back to plain ``print``
if the UI module isn't available yet.

Parameters
----------
quiet:
    If ``True``, suppress INFO-level issues (only show WARNING / ERROR).

<a id="core.runtime"></a>

# core.runtime

AgenticOs runtime orchestration.

<a id="core.runtime.main"></a>

#### main

```python
def main()
```

main function.

<a id="core.validators"></a>

# core.validators

Post-tool validation helpers.

Goal: reduce "tool said OK, but nothing happened" failures by checking reality
after common actions and returning a short validation note.

<a id="core.validators.validate_tool"></a>

#### validate\_tool

```python
def validate_tool(tool_name: str, args, result: str, *,
                  workspace_root: Path) -> str
```

validate_tool function.

<a id="core.url_presets"></a>

# core.url\_presets

URL presets for generating many useful open/search tools.

These presets are registered as individual tools at runtime to avoid writing
hundreds of nearly-identical functions.

<a id="core.url_presets.load_url_presets"></a>

#### load\_url\_presets

```python
def load_url_presets(cfg: dict | None = None) -> list[dict]
```

Load URL presets dynamically.

Precedence:
1) tools.url_presets_path (YAML file) if set and readable
2) config/url_presets.yaml (default YAML file)
3) tools.url_presets (inline list) if provided
4) empty list (fallback)

<a id="core.sentinel"></a>

# core.sentinel

Sentinel provides runtime monitoring and policy enforcement for tool usage.

Features:
- Loads a simple blocklist (tool names that are prohibited).
- Pre‑execution check that can abort a tool call with a clear error message.
- Post‑execution logging of every tool invocation to a workspace‑local log file.
- Optional callback hook for real‑time alerts (e.g., sending a desktop notification).

<a id="core.self_improvement"></a>

# core.self\_improvement

Self-Improvement ("Dreaming") module for AgenticOs.

Analyzes past task logs and failures to extract "Lessons Learned"
and write them to MEMORY.md. Can be triggered via `python main.py --dream`
or called programmatically at the start of a new session.

<a id="core.self_improvement.SelfImprovementDaemon"></a>

## SelfImprovementDaemon Objects

```python
class SelfImprovementDaemon()
```

Analyzes historical task performance and writes learned lessons to MEMORY.md.

<a id="core.self_improvement.SelfImprovementDaemon.should_dream"></a>

#### should\_dream

```python
def should_dream(force: bool = False) -> bool
```

Check if enough time has passed since the last dream cycle.

<a id="core.self_improvement.SelfImprovementDaemon.dream"></a>

#### dream

```python
def dream(force: bool = False) -> str
```

The main "Dreaming" loop.

1. Loads the task_tracking.json to find recent failures and slow tasks.
2. Loads recent daily logs for context.
3. Asks the LLM to generate "Lessons Learned".
4. Appends the lessons to MEMORY.md.

<a id="core.self_improvement.run_dream_cycle"></a>

#### run\_dream\_cycle

```python
def run_dream_cycle(workspace_root: str,
                    llm_client=None,
                    force: bool = False,
                    cfg: Optional[Dict] = None) -> str
```

Convenience function to run a dream cycle.

<a id="core.context_engine"></a>

# core.context\_engine

ContextEngine for AgenticOs.
Manages system prompt assembly, message history pruning,
and proactive context injection (Active Recall).

<a id="core.session_memory_sqlite"></a>

# core.session\_memory\_sqlite

SQLite-backed session memory.

Stores conversation messages per session in a local SQLite database inside the workspace.
This avoids unbounded JSON growth and makes history queries cheap.

<a id="tools"></a>

# tools

Role-based tool package for AgenticOs.

<a id="tools.system_tools"></a>

# tools.system\_tools

Module for system_tools.py

<a id="tools.system_tools.SystemManager"></a>

## SystemManager Objects

```python
class SystemManager()
```

Manager for agent session and system lifecycle.

<a id="tools.system_tools.SystemManager.exit_agent"></a>

#### exit\_agent

```python
@tool(name="exit_agent",
      desc=
      "Gracefully terminates the current agent session and exits the program.",
      category="System")
def exit_agent(reason: str = "User requested exit") -> str
```

Exits the agent process.

**Arguments**:

- `reason` - The reason for exiting.

<a id="tools.system_tools.SystemManager.get_system_telemetry"></a>

#### get\_system\_telemetry

```python
@tool(
    name="get_system_telemetry",
    desc=
    "Retrieves real-time system performance telemetry (CPU, Virtual Memory, Root Partition Disk space, and Network Bandwidth).",
    category="System")
def get_system_telemetry() -> dict
```

Retrieves real-time resource utilization statistics of the host machine.

**Returns**:

- `dict` - Structured metrics containing CPU, virtual memory, disk storage, and network transport statistics.

<a id="tools.plugins.diff_summarizer"></a>

# tools.plugins.diff\_summarizer

Plugin module for summarizing differences between two texts in plain English.

<a id="tools.plugins.diff_summarizer.summarize_text_diff"></a>

#### summarize\_text\_diff

```python
@tool(name="diff_summarizer", category="Custom", desc="Automated description")
def summarize_text_diff(old_text: str, new_text: str) -> str
```

Takes two text strings and returns a detailed, plain-English summary of what changed between them.

**Arguments**:

- `old_text` _str_ - The baseline/original text content.
- `new_text` _str_ - The updated/target text content.


**Returns**:

- `str` - A highly organized, line-by-line summary of additions, deletions, and modifications.

<a id="tools.plugins.fast_disk"></a>

# tools.plugins.fast\_disk

Module for fast_disk.py

<a id="tools.plugins.fast_disk.fast_disk_audit"></a>

#### fast\_disk\_audit

```python
@tool(
    name="fast_disk_audit",
    desc=
    "Optimized disk analysis using native PowerShell. Finds large files, duplicates, and old files in seconds.",
    category="Files")
def fast_disk_audit(path: str = None,
                    top_n: int = 20,
                    min_mb: int = 100,
                    mode: str = "all")
```

Performs a high-speed disk audit using PowerShell.
Modes: 'large' (top files), 'duplicates' (duplicate filenames), 'old' (not accessed in 180d), 'all'.

<a id="tools.plugins.code_complexity"></a>

# tools.plugins.code\_complexity

Plugin module for analyzing Python file cyclomatic complexity using Radon.

<a id="tools.plugins.code_complexity.code_complexity"></a>

#### code\_complexity

```python
@tool(name="code_complexity",
      category="Developer",
      desc="Automated description")
def code_complexity(file_path: str) -> str
```

Analyzes the cyclomatic complexity of functions and classes in a Python file.

Dynamically installs 'radon' if missing, computes the complexity of every
code block, and outputs a ranked markdown analysis report.

**Arguments**:

- `file_path` _str_ - The absolute or relative path to the Python file to analyze.


**Returns**:

- `str` - A detailed markdown cyclomatic complexity report.

<a id="tools.plugins.research_loop"></a>

# tools.plugins.research\_loop

Module for research_loop.py

<a id="tools.plugins.research_loop.research_loop"></a>

#### research\_loop

```python
@tool(name="research_loop",
      desc="Runs a multi-round research loop on a topic.",
      category="Research")
def research_loop(topic: str, rounds: str = "3") -> str
```

Runs a multi-round research loop on a topic.

<a id="tools.plugins.competitive_intel"></a>

# tools.plugins.competitive\_intel

Module for competitive_intel.py

<a id="tools.plugins.competitive_intel.competitive_intel"></a>

#### competitive\_intel

```python
@tool(name="competitive_intel",
      category="Business",
      desc="Fetches competitor intelligence matrix.")
def competitive_intel(competitors: list = None) -> str
```

Fetches competitor intelligence matrix.

**Arguments**:

- `competitors` - Optional list of competitor names.

<a id="tools.plugins.example_plugin"></a>

# tools.plugins.example\_plugin

Module for example_plugin.py

<a id="tools.plugins.example_plugin.calculate_tax"></a>

#### calculate\_tax

```python
@tool(desc="Automated description")
def calculate_tax(amount: float)
```

Calculates the tax for a given amount (15%).

<a id="tools.plugins.example_plugin.hello"></a>

#### hello

```python
@tool(name="greet_user", category="social", desc="Automated description")
def hello(name: str)
```

Greets the user with a friendly message.

<a id="tools.plugins.os_sandbox_auditor"></a>

# tools.plugins.os\_sandbox\_auditor

Plugin module for auditing OS environment runtimes, active window telemetry, and package registries.

<a id="tools.plugins.os_sandbox_auditor.os_sandbox_auditor"></a>

#### os\_sandbox\_auditor

```python
@tool(name="os_sandbox_auditor",
      category="System",
      desc="Automated description")
def os_sandbox_auditor() -> str
```

Performs a deep audit of the host environment, runtimes, package modules, and active windows.

Identifies installed interpreters/compilers, active GUI desktop windows,
and returns a formatted plain-English cross-platform capability report.

**Returns**:

- `str` - A detailed markdown capability and diagnostics report.

<a id="tools.plugins.plugin_health_check"></a>

# tools.plugins.plugin\_health\_check

Plugin health check module.

Scans all plugins in tools/plugins/ to ensure they have valid syntax,
a module docstring, and at least one callable.

<a id="tools.plugins.plugin_health_check.plugin_health_check"></a>

#### plugin\_health\_check

```python
@tool(name="plugin_health_check", category="System")
def plugin_health_check() -> Dict[str, str]
```

Scans all .py files in tools/plugins/.
For each: checks valid syntax, has docstring, has at least one callable.
Returns {plugin_name: "ok" | "missing_description" | "syntax_error" | "no_callable"}
Writes plugin_health_YYYY-MM-DD.md to workspace/daily_logs/

<a id="tools.plugins.url_safety_check"></a>

# tools.plugins.url\_safety\_check

Plugin module for validating URL safety, SSL certificates, and domain registration age.

<a id="tools.plugins.url_safety_check.url_safety_check"></a>

#### url\_safety\_check

```python
@tool(name="url_safety_check",
      category="Security",
      desc="Automated description")
def url_safety_check(url: str) -> str
```

Performs a comprehensive security and cryptographic audit of a URL.

Checks SSL certificate validity, registers WHOIS age, runs domain heuristics,
and returns a risk score (0 to 10) with a detailed assessment report.

**Arguments**:

- `url` _str_ - The absolute URL (including protocol, e.g., https://example.com) to analyze.


**Returns**:

- `str` - A detailed markdown report containing the security analysis and threat scores.

<a id="tools.plugins.vision_coordinator"></a>

# tools.plugins.vision\_coordinator

Plugin module for unified multi-modal visual coordinate mapping and hardware actions.

<a id="tools.plugins.vision_coordinator.click_element_by_name"></a>

#### click\_element\_by\_name

```python
@tool(
    name="click_element_by_name",
    desc=
    "Capture screen, find a text element matching the label using OCR coordinate mapping, and click it. Args: label",
    category="Plugins")
def click_element_by_name(label: str) -> str
```

Captures the current screen, resolves coordinates of the label text using WinRT/Tesseract OCR, and performs a native mouse click.

**Arguments**:

- `label` _str_ - Text label or phrase to click on screen (e.g. 'File', 'Settings', 'Cancel').


**Returns**:

- `str` - Success detail or error message.

<a id="tools.plugins.vision_coordinator.drag_and_drop_visual"></a>

#### drag\_and\_drop\_visual

```python
@tool(
    name="drag_and_drop_visual",
    desc=
    "Perform visual drag and drop from source text label to destination text label. Args: source, destination",
    category="Plugins")
def drag_and_drop_visual(source: str, destination: str) -> str
```

Finds coordinates of source and destination labels using visual coordinate mapping and performs a smooth mouse drag-and-drop.

**Arguments**:

- `source` _str_ - Label of the item to drag.
- `destination` _str_ - Label of the drop target.


**Returns**:

- `str` - Success or failure description.

<a id="tools.plugins.self_healing_test"></a>

# tools.plugins.self\_healing\_test

Module for self_healing_test.py

<a id="tools.plugins.self_healing_test.self_healing_test"></a>

#### self\_healing\_test

```python
@tool(name="self_healing_test",
      desc="Runs daily self-healing tests, validating recovery logic.",
      category="System")
def self_healing_test() -> str
```

Runs daily self-healing tests, validating recovery logic.

<a id="tools.plugins.session_summary"></a>

# tools.plugins.session\_summary

Module for session_summary.py

<a id="tools.plugins.session_summary.generate_session_summary"></a>

#### generate\_session\_summary

```python
@tool(category="System",
      desc="Generates a daily session summary from logs and evaluation output")
def generate_session_summary()
```

Reads evaluation_output.txt and SQLite audit logs from data/ (if they exist),
counts total tools called, unique tools used, errors logged, warnings logged,
identifies the longest-running task, and writes the summary to workspace/daily_logs/.

<a id="tools.plugins.meta_evolution"></a>

# tools.plugins.meta\_evolution

AgenticOs — Meta-Evolution Plugin
Allows the agent to autonomously generate and install new capabilities.

<a id="tools.plugins.meta_evolution.create_plugin"></a>

#### create\_plugin

```python
@tool(
    name="create_plugin",
    desc=
    "Autonomously create a new Python tool plugin. Args: name (lowercase), code (Python string), description (str). The code MUST use the @tool decorator.",
    category="meta",
    version="1.0.0",
    author="AgenticOs Engine")
def create_plugin(name: str, code: str, description: str = "") -> str
```

Writes a new .py file to tools/plugins/ to expand agent capabilities.

<a id="tools.plugins.sys_package_installer"></a>

# tools.plugins.sys\_package\_installer

Plugin module for unified cross-platform system package manager probing and installation.

<a id="tools.plugins.sys_package_installer.check_package_managers"></a>

#### check\_package\_managers

```python
@tool(name="check_package_managers",
      category="System",
      desc="Automated description")
def check_package_managers() -> str
```

Probes and identifies available package managers on the host machine.

**Returns**:

- `str` - A markdown report of available package managers and their installation paths.

<a id="tools.plugins.sys_package_installer.install_system_package"></a>

#### install\_system\_package

```python
@tool(name="install_system_package",
      category="System",
      desc="Automated description")
def install_system_package(package_name: str) -> str
```

Autonomously installs a system utility package using the preferred local manager.

**Arguments**:

- `package_name` _str_ - Name of the package to install (e.g. 'ffmpeg', 'git', 'curl').


**Returns**:

- `str` - The outcome details of the installation attempt.

<a id="tools.plugins.validate_config_tool"></a>

# tools.plugins.validate\_config\_tool

Module for validate_config_tool.py

<a id="tools.plugins.validate_config_tool.deep_merge"></a>

#### deep\_merge

```python
def deep_merge(source, destination)
```

Deep merges source dict into destination dict.

<a id="tools.plugins.validate_config_tool.validate_config"></a>

#### validate\_config

```python
@tool(
    category="System",
    desc="Validates the AgenticOs configuration and generates an audit report")
def validate_config()
```

Reads config.yaml and layered files in config/, validates specific fields and their types,
checks if the workspace is writable, and generates an audit report in workspace/daily_logs/.

<a id="tools.web.api"></a>

# tools.web.api

JSON/GraphQL API helper methods for WebTools.

<a id="tools.web.browser"></a>

# tools.web.browser

AgenticOs — browser automation tools
Playwright-based browser automation: navigate, read DOM, click, fill forms,
execute JS, take screenshots, manage cookies, and more.

Installation (one-time):
    pip install playwright
    playwright install chromium

<a id="tools.web.browser.BrowserManager"></a>

## BrowserManager Objects

```python
class BrowserManager()
```

Manages a dedicated background thread with its own asyncio loop for Playwright.

<a id="tools.web.browser.BrowserManager.start"></a>

#### start

```python
def start()
```

start function.

<a id="tools.web.browser.BrowserManager.run_coro"></a>

#### run\_coro

```python
def run_coro(coro)
```

run_coro function.

<a id="tools.web.browser.BrowserMixin"></a>

## BrowserMixin Objects

```python
class BrowserMixin()
```

Full browser automation via Playwright (async API, thread-safe wrapper).

<a id="tools.web.spotify"></a>

# tools.web.spotify

Module for spotify.py

<a id="tools.web.web_pick_best_link"></a>

# tools.web.web\_pick\_best\_link

Standalone web_pick_best_link helper.

This module is intentionally self-contained so it can be registered as a tool
without requiring changes to existing WebTools internals.

<a id="tools.web.web_pick_best_link.web_pick_best_link"></a>

#### web\_pick\_best\_link

```python
def web_pick_best_link(query: str, domain_hint: str = "") -> str
```

Search Google HTML results and pick a best link.

**Notes**:

  - This is a best-effort helper for "open the actual thing" workflows.
  - It avoids requiring an API key by parsing the search results page.

<a id="tools.web"></a>

# tools.web

AgenticOs — web tools
Web tools: search, fetch, download, API calls, scraping, headers, whois, DNS, and utilities.

<a id="tools.web.utils"></a>

# tools.web.utils

Utility helpers for WebTools.

<a id="tools.web.youtube"></a>

# tools.web.youtube

Module for youtube.py

<a id="tools.web.session"></a>

# tools.web.session

Shared HTTP session helpers for WebTools.

<a id="tools.web.session.requests_module"></a>

#### requests\_module

```python
def requests_module()
```

requests_module function.

<a id="tools.web.session.bs4_beautifulsoup"></a>

#### bs4\_beautifulsoup

```python
def bs4_beautifulsoup()
```

bs4_beautifulsoup function.

<a id="tools.web.session.build_default_session"></a>

#### build\_default\_session

```python
def build_default_session(existing_session=None)
```

build_default_session function.

<a id="tools.web.session.parse_headers_json"></a>

#### parse\_headers\_json

```python
def parse_headers_json(headers: str) -> dict
```

parse_headers_json function.

<a id="tools.web.fetch"></a>

# tools.web.fetch

Fetch/scrape/download methods for WebTools.

<a id="tools.web.inspect"></a>

# tools.web.inspect

Inspection methods (headers, SSL, whois, DNS, IP helpers) for WebTools.

<a id="tools.web.search"></a>

# tools.web.search

Search-related methods for WebTools.

<a id="tools.terminal.runner"></a>

# tools.terminal.runner

Module for runner.py

<a id="tools.terminal.dev"></a>

# tools.terminal.dev

Module for dev.py

<a id="tools.terminal.openers"></a>

# tools.terminal.openers

Module for openers.py

<a id="tools.terminal.system_admin"></a>

# tools.terminal.system\_admin

Module for system_admin.py

<a id="tools.terminal.safety"></a>

# tools.terminal.safety

Module for safety.py

<a id="tools.terminal.network"></a>

# tools.terminal.network

Module for network.py

<a id="tools.terminal"></a>

# tools.terminal

AgenticOs — terminal tools
Shell command execution, process management, environment, system info.
Supports PowerShell (Windows), Bash/Zsh (Unix/macOS), CMD.

<a id="tools.terminal.windows_windows"></a>

# tools.terminal.windows\_windows

Module for windows_windows.py

<a id="tools.terminal.windows_windows.WindowsWindowsMixin"></a>

## WindowsWindowsMixin Objects

```python
class WindowsWindowsMixin()
```

Windows window management via PowerShell.

Uses COM/Shell techniques rather than fragile coordinate automation.

<a id="tools.terminal.windows_windows.WindowsWindowsMixin.focus_app"></a>

#### focus\_app

```python
def focus_app(app_name: str) -> str
```

Bring a matching application window to the foreground.

<a id="tools.terminal.windows_windows.WindowsWindowsMixin.window_list"></a>

#### window\_list

```python
@tool(name="window_list",
      desc="List windows with titles (Windows). Args: filter_str(optional)",
      category="Terminal")
def window_list(filter_str: str = "") -> str
```

window_list function.

<a id="tools.terminal.windows_windows.WindowsWindowsMixin.window_focus"></a>

#### window\_focus

```python
@tool(name="window_focus",
      desc="Focus a window by title substring (Windows). Args: title",
      category="Terminal")
def window_focus(title: str) -> str
```

Focus the first window whose title contains the given substring.

**Arguments**:

- `title` - Substring to match against window titles (case-insensitive).

<a id="tools.terminal.windows_windows.WindowsWindowsMixin.window_close"></a>

#### window\_close

```python
@tool(name="window_close",
      desc="Close a window by title substring (Windows). Args: title",
      category="Terminal")
def window_close(title: str) -> str
```

Close the first window whose title contains the given substring.

**Arguments**:

- `title` - Substring to match against window titles (case-insensitive).

<a id="tools.terminal.windows_windows.WindowsWindowsMixin.get_browser_url"></a>

#### get\_browser\_url

```python
@tool(
    name="get_browser_url",
    desc=
    "Get the current URL shown in the active browser tab. Args: browser(optional, e.g. 'brave')",
    category="Terminal")
def get_browser_url(browser: str = "") -> str
```

Read the URL currently shown in the active browser tab.

Focuses the browser address bar (Ctrl+L), copies its contents, and
returns the URL via clipboard. Works with any browser.

**Arguments**:

- `browser` - Optional process/window name hint to focus first (e.g. 'brave', 'chrome').
  If omitted, assumes the browser window is already active.

<a id="tools.terminal.windows_windows.WindowsWindowsMixin.browser_read_page_text"></a>

#### browser\_read\_page\_text

```python
@tool(
    name="browser_read_page_text",
    desc=
    "Read all visible text from the active browser tab (Ctrl+A+C). Args: browser(optional)",
    category="Terminal")
def browser_read_page_text(browser: str = "") -> str
```

Read all visible text from the currently active browser tab.

Selects all page content (Ctrl+A), copies it (Ctrl+C), and returns
the clipboard text. Works best on simple pages; Gmail/SPAs may return
partial text due to virtual DOM rendering.

**Arguments**:

- `browser` - Optional process/window name hint to focus first (e.g. 'brave', 'chrome').
  If omitted, assumes the browser window is already active.

<a id="tools.terminal.windows_windows.WindowsWindowsMixin.browser_read_selection"></a>

#### browser\_read\_selection

```python
@tool(
    name="browser_read_selection",
    desc=
    "Read the currently selected/highlighted text in the browser. Args: browser(optional)",
    category="Terminal")
def browser_read_selection(browser: str = "") -> str
```

Read the text currently selected/highlighted in the active browser tab.

Copies whatever the browser has selected (Ctrl+C) and returns it from
the clipboard. Useful for reading a specific section of a page that
the user or agent has highlighted.

**Arguments**:

- `browser` - Optional process/window name hint to focus first (e.g. 'brave', 'chrome').
  If omitted, assumes the browser window is already active.

<a id="tools.terminal.keyboard"></a>

# tools.terminal.keyboard

AgenticOs — keyboard shortcut and input mixin
Send hotkeys, press individual keys, type text, and simulate mouse clicks.

Windows : WScript.Shell SendKeys  +  ctypes user32 for special keys
macOS   : osascript (System Events keystroke / key code)
Linux   : xdotool (X11) or ydotool (Wayland)

SendKeys special-character reference (Windows WScript.Shell):
  Modifier prefixes : ^ = Ctrl  % = Alt  + = Shift  # = Win
  Special keys      : {ENTER} {TAB} {ESC} {SPACE} {BACKSPACE} {DELETE}
                      {UP} {DOWN} {LEFT} {RIGHT} {HOME} {END}
                      {PGUP} {PGDN} {F1}–{F24} {INS} {PRTSC}
  Literal braces    : {{}  {}}
  Repeat syntax     : {KEY n}  e.g. {DOWN 3}

<a id="tools.terminal.keyboard.KeyboardMixin"></a>

## KeyboardMixin Objects

```python
class KeyboardMixin()
```

Keyboard shortcut, hotkey, and text-input methods.

<a id="tools.terminal.keyboard.KeyboardMixin.hotkey"></a>

#### hotkey

```python
@tool(
    name="hotkey",
    desc=
    "Send a keyboard shortcut/hotkey. Args: keys (e.g. ctrl+c, alt+f4, win+d), window(optional)",
    category="Terminal")
def hotkey(keys: str, window: str = "") -> str
```

Send a keyboard shortcut / hotkey combination.

**Arguments**:

  keys  : Key combo OR a custom named shortcut defined in config.yaml.
  Use + to separate modifiers and keys.
- `Examples` - ctrl+c  ctrl+shift+s  alt+f4  win+d
  screenshot  emoji_picker  my_custom_action
- `window` - (optional) Bring this window title to foreground first.

  Built-in shortcuts (examples):
  ctrl+c / ctrl+x / ctrl+v   Copy / Cut / Paste
  ctrl+z / ctrl+y            Undo / Redo
  ctrl+s                     Save
  ctrl+a                     Select all
  ctrl+f                     Find
  ctrl+w                     Close tab/window
  ctrl+t                     New tab
  ctrl+shift+t               Reopen closed tab
  alt+f4                     Close application
  alt+tab                    Switch window
  win+d                      Show desktop
  win+l                      Lock screen
  win+e                      File Explorer
  win+r                      Run dialog
  win+s                      Windows Search
  win+.                      Emoji picker
  win+shift+s                Snip & Sketch / screenshot
  ctrl+shift+esc             Task Manager
  ctrl+alt+delete            Security screen
  f5                         Refresh
  f11                        Fullscreen toggle
  printscreen                Screenshot

  Custom shortcuts are defined in config.yaml under 'custom_keys'.
  Use hotkey_list to see all defined custom shortcuts.

<a id="tools.terminal.keyboard.KeyboardMixin.hotkey_list"></a>

#### hotkey\_list

```python
@tool(name="hotkey_list",
      desc="List all custom named shortcut aliases.",
      category="Terminal")
def hotkey_list() -> str
```

List all custom named shortcut aliases defined for this session.

Shows both shortcuts loaded from config.yaml and any added via hotkey_set.

<a id="tools.terminal.keyboard.KeyboardMixin.hotkey_set"></a>

#### hotkey\_set

```python
@tool(name="hotkey_set",
      desc="Define/update a custom named shortcut (session). Args: name, keys",
      category="Terminal")
def hotkey_set(name: str, keys: str) -> str
```

Define or update a custom named shortcut alias for this session.

**Arguments**:

- `name` - Alias name for the shortcut (e.g. 'screenshot', 'emoji', 'save_all').
  Use underscores for multi-word names.
- `keys` - The key combo to bind (e.g. 'win+shift+s', 'ctrl+shift+s').


**Example**:

  hotkey_set(name='screenshot', keys='win+shift+s')
  hotkey_set(name='emoji', keys='win+.')
  hotkey_set(name='lock', keys='win+l')

- `Note` - Changes are session-only. To persist across restarts, add to
  config.yaml under the 'custom_keys' section.

<a id="tools.terminal.keyboard.KeyboardMixin.hotkey_delete"></a>

#### hotkey\_delete

```python
@tool(name="hotkey_delete",
      desc="Remove a custom named shortcut. Args: name",
      category="Terminal")
def hotkey_delete(name: str) -> str
```

Remove a custom named shortcut alias from this session.

**Arguments**:

- `name` - The alias name to remove.

<a id="tools.terminal.keyboard.KeyboardMixin.press_key"></a>

#### press\_key

```python
@tool(
    name="press_key",
    desc=
    "Press a single key N times. Args: key (enter/tab/esc/f5/up/etc), repeat(optional)",
    category="Terminal")
def press_key(key: str, repeat: int = 1) -> str
```

Press a single key (or repeat it N times).

**Arguments**:

  key   : Key name. Examples: enter, tab, esc, f5, up, down,
  left, right, home, end, delete, backspace, space,
  pageup, pagedown, capslock, f1–f24
- `repeat` - How many times to press the key (default 1).

<a id="tools.terminal.keyboard.KeyboardMixin.type_text"></a>

#### type\_text

```python
@tool(name="type_text",
      desc="Type text as keyboard input. Args: text, delay_ms(optional)",
      category="Terminal")
def type_text(text: str, delay_ms: int = 0) -> str
```

Type a string of text as keyboard input (simulates typing).

**Arguments**:

  text    : The text to type. Supports Unicode on Windows/Linux.
- `delay_ms` - Delay between keystrokes in milliseconds (0 = instant).
  Use 30–100 for more human-like typing speed.

- `Note` - Special characters (e.g. quotes, braces) are handled automatically.

<a id="tools.terminal.keyboard.KeyboardMixin.key_down"></a>

#### key\_down

```python
@tool(name="key_down",
      desc="Hold a key down. Args: key (shift/ctrl/alt/etc)",
      category="Terminal")
def key_down(key: str) -> str
```

Hold a key down (useful for drag-and-drop or sustained modifier presses).

**Arguments**:

- `key` - Key name (e.g. shift, ctrl, alt, f, a).

<a id="tools.terminal.keyboard.KeyboardMixin.key_up"></a>

#### key\_up

```python
@tool(name="key_up", desc="Release a held key. Args: key", category="Terminal")
def key_up(key: str) -> str
```

Release a previously held key.

**Arguments**:

- `key` - Key name (e.g. shift, ctrl, alt).

<a id="tools.terminal.keyboard.KeyboardMixin.mouse_click"></a>

#### mouse\_click

```python
@tool(
    name="mouse_click",
    desc=
    "Simulate mouse click. Args: button(left/right/middle), x(optional), y(optional)",
    category="Terminal")
def mouse_click(button: str = "left", x: int = -1, y: int = -1) -> str
```

Simulate a mouse click, optionally at screen coordinates.

**Arguments**:

- `button` - 'left', 'right', or 'middle' (default: left).
  x     : Screen X coordinate (-1 = current position).
  y     : Screen Y coordinate (-1 = current position).

<a id="tools.terminal.keyboard.KeyboardMixin.mouse_move"></a>

#### mouse\_move

```python
@tool(name="mouse_move",
      desc="Move mouse cursor to coordinates. Args: x, y",
      category="Terminal")
def mouse_move(x: int, y: int) -> str
```

Move the mouse cursor to absolute screen coordinates.

**Arguments**:

- `x` - Screen X coordinate in pixels.
- `y` - Screen Y coordinate in pixels.

<a id="tools.terminal.keyboard.KeyboardMixin.mouse_scroll"></a>

#### mouse\_scroll

```python
@tool(name="mouse_scroll",
      desc="Scroll mouse wheel. Args: direction(up/down), clicks(optional)",
      category="Terminal")
def mouse_scroll(direction: str = "down", clicks: int = 3) -> str
```

Scroll the mouse wheel.

**Arguments**:

- `direction` - 'up' or 'down' (default: down).
  clicks   : Number of scroll steps (default: 3).

<a id="tools.terminal.keyboard.KeyboardMixin.focus_window_and_hotkey"></a>

#### focus\_window\_and\_hotkey

```python
@tool(name="focus_window_and_hotkey",
      desc="Focus a window then send a hotkey. Args: window, keys",
      category="Terminal")
def focus_window_and_hotkey(window: str, keys: str) -> str
```

Focus a window by title and then send a hotkey.

**Arguments**:

- `window` - Partial window title to match and bring to foreground.
  keys  : Key combo to send (e.g. ctrl+s, f5).

  Useful for sending shortcuts to a specific app without clicking manually.

<a id="tools.terminal.clipboard"></a>

# tools.terminal.clipboard

Module for clipboard.py

<a id="tools.terminal.env"></a>

# tools.terminal.env

Module for env.py

<a id="tools.terminal.paths"></a>

# tools.terminal.paths

Module for paths.py

<a id="tools.terminal.system"></a>

# tools.terminal.system

Module for system.py

<a id="tools.terminal.processes"></a>

# tools.terminal.processes

Module for processes.py

<a id="tools.terminal.media"></a>

# tools.terminal.media

AgenticOs — media controls mixin
Play, pause, stop, next, previous track, seek, and volume control.

Windows: SendKeys via PowerShell (WScript.Shell) + nircmd for volume.
macOS:   osascript (AppleScript) for iTunes/Music and volume.
Linux:   playerctl (MPRIS) + pactl/amixer for volume.

<a id="tools.terminal.media.MediaMixin"></a>

## MediaMixin Objects

```python
class MediaMixin()
```

Media playback and audio control methods.

<a id="tools.terminal.media.MediaMixin.media_play_pause"></a>

#### media\_play\_pause

```python
@tool(name="media_play_pause",
      desc="Toggle play/pause for the active media player.",
      category="Terminal")
def media_play_pause() -> str
```

Toggle play/pause for the active media player.

<a id="tools.terminal.media.MediaMixin.media_play"></a>

#### media\_play

```python
@tool(name="media_play",
      desc="Resume/start media playback.",
      category="Terminal")
def media_play() -> str
```

Resume / start playback.

<a id="tools.terminal.media.MediaMixin.media_pause"></a>

#### media\_pause

```python
@tool(name="media_pause",
      desc="Pause the active media player.",
      category="Terminal")
def media_pause() -> str
```

Pause the active media player.

<a id="tools.terminal.media.MediaMixin.media_stop"></a>

#### media\_stop

```python
@tool(name="media_stop", desc="Stop media playback.", category="Terminal")
def media_stop() -> str
```

Stop media playback.

<a id="tools.terminal.media.MediaMixin.media_next"></a>

#### media\_next

```python
@tool(name="media_next", desc="Skip to the next track.", category="Terminal")
def media_next() -> str
```

Skip to the next track.

<a id="tools.terminal.media.MediaMixin.media_previous"></a>

#### media\_previous

```python
@tool(name="media_previous",
      desc="Go to the previous track.",
      category="Terminal")
def media_previous() -> str
```

Go back to the previous track.

<a id="tools.terminal.media.MediaMixin.media_status"></a>

#### media\_status

```python
@tool(name="media_status",
      desc="Get currently playing track info and playback status.",
      category="Terminal")
def media_status() -> str
```

Get currently playing track info / playback status.

<a id="tools.terminal.media.MediaMixin.media_seek"></a>

#### media\_seek

```python
@tool(name="media_seek",
      desc="Seek forward/backward by N seconds. Args: seconds (+/-)",
      category="Terminal")
def media_seek(seconds: float) -> str
```

Seek forward (positive) or backward (negative) by N seconds.

**Arguments**:

- `seconds` - Number of seconds to seek (+/-).

<a id="tools.terminal.media.MediaMixin.volume_set"></a>

#### volume\_set

```python
@tool(name="volume_set",
      desc="Set system master volume 0-100. Args: level",
      category="Terminal")
def volume_set(level: int) -> str
```

Set system master volume (0–100).

**Arguments**:

- `level` - Volume percentage (0 = mute, 100 = max).

<a id="tools.terminal.media.MediaMixin.volume_up"></a>

#### volume\_up

```python
@tool(name="volume_up",
      desc="Raise system volume by step% (default 10). Args: step(optional)",
      category="Terminal")
def volume_up(step: int = 10) -> str
```

Raise system volume by step% (default +10).

**Arguments**:

- `step` - Percentage points to increase (1–50).

<a id="tools.terminal.media.MediaMixin.volume_down"></a>

#### volume\_down

```python
@tool(name="volume_down",
      desc="Lower system volume by step% (default 10). Args: step(optional)",
      category="Terminal")
def volume_down(step: int = 10) -> str
```

Lower system volume by step% (default -10).

**Arguments**:

- `step` - Percentage points to decrease (1–50).

<a id="tools.terminal.media.MediaMixin.volume_mute"></a>

#### volume\_mute

```python
@tool(name="volume_mute",
      desc="Toggle system mute on/off.",
      category="Terminal")
def volume_mute() -> str
```

Toggle system mute on/off.

<a id="tools.terminal.media.MediaMixin.volume_get"></a>

#### volume\_get

```python
@tool(name="volume_get",
      desc="Get current system master volume level.",
      category="Terminal")
def volume_get() -> str
```

Get the current system master volume level.

<a id="tools.filesystem.mutations"></a>

# tools.filesystem.mutations

Module for mutations.py

<a id="tools.filesystem.edit"></a>

# tools.filesystem.edit

Module for edit.py

<a id="tools.filesystem.structured"></a>

# tools.filesystem.structured

Module for structured.py

<a id="tools.filesystem.bulk"></a>

# tools.filesystem.bulk

Module for bulk.py

<a id="tools.filesystem.read_write"></a>

# tools.filesystem.read\_write

Module for read_write.py

<a id="tools.filesystem.diff_stats"></a>

# tools.filesystem.diff\_stats

Module for diff_stats.py

<a id="tools.filesystem.archive"></a>

# tools.filesystem.archive

Module for archive.py

<a id="tools.filesystem"></a>

# tools.filesystem

AgenticOs — filesystem tools
Complete file-system operations: create, read, write, edit, delete, copy, move, search, grep, archive,
JSON/CSV helpers, diff, and stats.

<a id="tools.filesystem.listing"></a>

# tools.filesystem.listing

Module for listing.py

<a id="tools.filesystem.cwd"></a>

# tools.filesystem.cwd

Module for cwd.py

<a id="tools.filesystem.info"></a>

# tools.filesystem.info

Module for info.py

<a id="tools.filesystem.search"></a>

# tools.filesystem.search

Module for search.py

<a id="tools.screen_tools"></a>

# tools.screen\_tools

AgenticOs — screen tools
Cross-platform screen capture and window management.
Windows: uses Pillow + PowerShell
macOS:   uses screencapture / osascript
Linux:   uses scrot / gnome-screenshot / xdotool

<a id="tools.ocr_tools"></a>

# tools.ocr\_tools

Module for ocr_tools.py

<a id="tools.ocr_tools.OCRManager"></a>

## OCRManager Objects

```python
class OCRManager()
```

AgenticOS OCR Manager.
Supports both native Windows OCR and Tesseract-OCR.

<a id="tools.ocr_tools.OCRManager.ocr_image"></a>

#### ocr\_image

```python
@tool(name="ocr_image",
      desc=
      "Extract text from an image file using Tesseract or Native Windows OCR.",
      category="Media")
def ocr_image(path: str, engine: str = None) -> str
```

Performs OCR on a local image file.

**Arguments**:

- `path` - Absolute or workspace-relative path to the image.
- `engine` - 'tesseract', 'native', or 'auto'. Defaults to config.

<a id="tools.ocr_tools.OCRManager.ocr_screen"></a>

#### ocr\_screen

```python
@tool(name="ocr_screen",
      desc="Captures the entire screen and extracts all visible text.",
      category="Media")
def ocr_screen(engine: str = None) -> str
```

Takes a screenshot of the current screen and runs OCR on it.

**Arguments**:

- `engine` - 'tesseract', 'native', or 'auto'. Defaults to config.

<a id="tools.desktop_notifications"></a>

# tools.desktop\_notifications

AgenticOs — notification tools
Cross-platform desktop notifications, popups, and TTS.
Supports Windows, macOS, and Linux.

