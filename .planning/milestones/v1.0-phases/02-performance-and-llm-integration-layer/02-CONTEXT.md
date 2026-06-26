---
phase: 2
phase_name: Performance and LLM Integration Layer
slug: 02-performance-and-llm-integration-layer
date: 2026-06-26
status: context_gathered
requirements: [PERF-01, PERF-02, PERF-03, PERF-04, INTEG-01, INTEG-02, INTEG-03, INTEG-04, INTEG-05, DOC-03]
---

# Phase 2 Context: Performance and LLM Integration Layer

## Domain

This phase delivers three performance and LLM-communication capability clusters:

1. **Adaptive Context Compaction** — middle-truncation/collapsing of large observation texts and sliding-window compaction to prevent context window overflows.
2. **Streaming & Concurrency** — incremental JSON action parser yielding tool calls from the LLM stream and parallel tool execution via topological dependency sorting.
3. **Resilient Routing & Budgeting** — fallback router cascading on rate-limits, auth errors, and context limits, alongside pre-flight token budgeting checks.

---

## Decisions

### Adaptive Context Window (PERF-01)
- **Mechanism:** Implement message history log scanner. For any observation content exceeding 4000 characters, collapse the middle portion with `[... COLLAPSED X CHARACTERS ...]` while preserving the first and last 2000 characters.
- **Compaction:** Implement sliding-window history compactor that triggers LLM-powered summarization of older history once message count exceeds memory limits, falling back gracefully to text truncation if the compaction API fails.

### Streaming JSON Parser (PERF-02)
- **Parser:** Implement `StreamingActionParser` that feeds streaming chunks and incrementally yields fully-parsed action pairs `(tool_name, args)`.
- **Termination:** Recognize termination keywords (`OBSERVATION:`, `FINAL ANSWER:`, etc.) or valid closing braces to flush complete blocks.

### Concurrency Action Scheduler (PERF-04)
- **Mechanism:** Implement `ParallelScheduler` which builds dependency graphs for batched actions and executes independent waves of actions concurrently via `ThreadPoolExecutor`.
- **Fallback:** Fall back to sequential execution if parallel mode is disabled or there is only a single action.

### Semantic Tool Index (PERF-03)
- **Discovery:** Implement `SemanticToolIndex` utilizing TF-IDF vector similarity over tool descriptors to fetch only relevant tools, reducing system prompt token size.

### Fallback Router & Estimators (INTEG-01 to INTEG-05, DOC-03)
- **Fallback Router:** Implement `FallbackRouter` wrapping primary and secondary clients. Categorize exceptions (rate-limit, context limit, auth failure) and handle with custom strategies (throttling, model upgrading, key switching).
- **Token Budget Checker:** Implement pre-flight budget calculations warning users if tokens exceed 85% of active model context window thresholds.
