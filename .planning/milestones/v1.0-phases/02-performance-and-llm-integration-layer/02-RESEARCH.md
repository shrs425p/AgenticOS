---
phase: 2
phase_name: Performance and LLM Integration Layer
slug: 02-performance-and-llm-integration-layer
date: 2026-06-26
status: research_complete
---

# Phase 2 Research: Performance and LLM Integration Layer

## Orientation

This phase implements performance enhancements, concurrency capabilities, and API-resilient routing strategies:
- **Adaptive Context Window:** `kernel/context.py` (collapse message details and compact message histories).
- **Streaming Parser & Concurrency:** `kernel/dispatch.py` (`StreamingActionParser` and `ParallelScheduler`).
- **Semantic Tool Index:** `kernel/discovery.py` (`SemanticToolIndex` TF-IDF search).
- **Resilient Routing & Token Budgets:** `kernel/models.py` (`FallbackRouter` and `TokenBudgetChecker`).

---

## Area 1: Context Engine Compaction (`kernel/context.py`)

### Compaction Details
- `collapse_large_messages(messages)`: scans log history, targeting observations exceeding 4000 chars. Collapses middle text with `[... COLLAPSED X CHARACTERS ...]` while preserving the first and last 2000 characters.
- `compact_history(messages)`: triggers sliding window compaction by prompting the LLM client to summarize oldest logs when history length exceeds limits. Falls back to text pruning notices on failure.

---

## Area 2: Streaming Parser & Scheduler (`kernel/dispatch.py`)

### Streaming JSON Parser
- `StreamingActionParser`:
  - `feed(chunk: str) -> list[tuple[str, dict]]`: accumulates chunks in `self._buf` and extracts matches via regex or JSON block extraction.
  - `flush() -> list[tuple[str, dict]]`: parses any remaining partial buffer text.
  - `reset()`: resets buffer string.

### Parallel Execution Scheduler
- `ParallelScheduler`:
  - Kahn's algorithm topological sort grouping independent actions into concurrent execution waves.
  - `execute(actions, executor_fn)`: runs independent waves concurrently using a `ThreadPoolExecutor` (default worker size = 4).
- `execute_actions_parallel(actions, executor_fn)`: wraps scheduler execution, falling back to sequential execution on single-action batches or if parallel mode is disabled.

---

## Area 3: Semantic Tool Index (`kernel/discovery.py`)

### Similarity Search
- `SemanticToolIndex`:
  - Indexes tool names, category headers, and description blocks using TF-IDF term representation.
  - cosine similarity queries returns top-k matching tool descriptors.

---

## Area 4: Fallback Router & Budgets (`kernel/models.py`)

### Model fallback routing
- `FallbackRouter`:
  - Cascades model prompts across a list of fallback providers on exceptions.
  - Exception classes matching: rate limits (throttles and waits), context limits (upgrades to next model), authentication failures (skips to next provider).
- `TokenBudgetChecker`:
  - pre-flight calculator checking projected token costs against active context parameters.
  - Triggers warning alerts if total projection exceeds 85% threshold of limits.
