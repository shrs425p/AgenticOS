# AgenticOS Core

The Runtime Engine, Tool Registry, Memory, and Security Guardrails.

Key internals:

- `core/retry.py`: Centralized retry/backoff helper (`retry_call`) used by provider clients to handle rate-limits and transient API errors.
- Plugin loading: Modules under `tools/plugins/` are imported under the `tools.plugins.<module_name>` namespace and registered by `ToolRegistry` by scanning for callables decorated with `@tool`.
