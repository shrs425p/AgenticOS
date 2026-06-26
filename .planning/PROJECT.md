# AgenticOS

## What This Is

AgenticOS is an autonomous agentic operating system control framework. It empowers AI agents with direct, secure, and robust execution capabilities on local OS runtimes (Windows, macOS, Linux) to perform complex development, scripting, and system management tasks.

## Core Value

Enable agents to achieve 100% task completion rates on the user's OS runtime with maximum autonomy and complete security, without ever unnecessarily saying "no."

## Requirements

### Validated

- [x] **SEC-01**: Unicode & encoding escape sequence detection in command execution. (Phase 1)
- [x] **SEC-02**: Intercept dynamic code generation commands writing shell/Python scripts to disk. (Phase 1)
- [x] **SEC-03**: Fine-grained registry key policy controls (allowed, blocked, and approval-required paths). (Phase 1)
- [x] **SEC-04**: Symlink path resolution depth validation to prevent symlink traversal attacks. (Phase 1)
- [x] **QUAL-01**: Pydantic validation models for actions and system configurations. (Phase 1)
- [x] **QUAL-02**: Modularize large functions in `core/runtime.py` into distinct domains (orchestrator, dispatcher, memory, error). (Phase 1)
- [x] **QUAL-03**: Implement Type-safe Tool Registry using a standard `Tool` protocol. (Phase 1)
- [x] **QUAL-04**: Unified `AgentError` class with error codes and recovery suggestions. (Phase 1)
- [x] **DOC-02**: Threat model document mapping security mitigations to residual risks. (Phase 1)
- [x] **TEST-05**: Security regression test suite checking bypass payloads. (Phase 1)
- [x] **PERF-01**: Adaptive context window engine adjusting history length dynamically. (Phase 2)
- [x] **PERF-02**: Streaming JSON action parsing for concurrent execution streams. (Phase 2)
- [x] **PERF-03**: Semantic indexed tool discovery using vector similarity lookup. (Phase 2)
- [x] **PERF-04**: Parallel tool execution for independent steps in action graphs. (Phase 2)
- [x] **INTEG-01**: Smart fallback routing based on model errors (timeouts vs JSON parsing issues). (Phase 2)
- [x] **INTEG-02**: Cost-aware LLM routing prioritizing cheaper local models for basic tasks. (Phase 2)
- [x] **INTEG-03**: Model-specific prompt templates to optimize responses. (Phase 2)
- [x] **INTEG-04**: Structured JSON output guarantee with schema-based retry loops. (Phase 2)
- [x] **INTEG-05**: Pre-flight token and cost estimation warnings. (Phase 2)
- [x] **DOC-03**: Cost and token estimation guide for predicting execution expenses. (Phase 2)
- [x] **DOC-01**: Production deployment playbook (Docker, Windows Service, Kubernetes, Serverless). (Phase 3)
- [x] **OS-01**: macOS deep integration via AppleScript and accessibility APIs. (Phase 3)
- [x] **OS-02**: Linux desktop-agnostic support (Wayland/X11, KDE/GNOME/i3) and custom screenshot helpers. (Phase 3)
- [x] **OS-03**: Embedded and resource-constrained environment hardware tuning (Pi, ARM, IoT). (Phase 3)
- [x] **AUTO-01**: Smart repetition analyzer allowing retries only on transient errors or modified arguments. (Phase 3)
- [x] **AUTO-02**: Success criteria extraction and automated verification before final completion. (Phase 3)
- [x] **AUTO-03**: Adaptive task duration estimation and stall warning thresholds. (Phase 3)
- [x] **AUTO-04**: Long-term task orchestrator with phase splitting and state checkpoints. (Phase 3)
- [x] **AUTO-05**: Opportunity scanner recommending faster alternatives mid-task. (Phase 3)

### Active

- [ ] **EXT-01**: Async tool support using asynchronous streaming iterators.
- [ ] **EXT-02**: Streaming tool output protocol for large file/text streams.
- [ ] **EXT-03**: Remote plugin registry for downloading and installing community tools.
- [ ] **EXT-04**: Tool dependency resolution and compatibility checking.
- [ ] **EXT-05**: Tool composition and piping protocol.
- [ ] **TEST-01**: End-to-end multi-step workflow integration tests.
- [ ] **TEST-02**: Mutation testing to verify test assertion quality.
- [ ] **TEST-03**: Performance regression benchmarks to track speed.
- [ ] **TEST-04**: Chaos Monkey harness simulating LLM delays, DB corruption, and network dropouts.
- [ ] **MEM-01**: Semantic memory search using FAISS or similar vector matching.
- [ ] **MEM-02**: Time-based memory decay using mathematical half-life calculations.
- [ ] **MEM-03**: Episodic memory clustering to group similar past actions.
- [ ] **MEM-04**: Validated memory storage requiring supporting evidence.
- [ ] **MEM-05**: Distributed memory synchronization across multiple agents.

### Out of Scope

- **BIOS/firmware control** — outside the operating system runtime boundaries.

## Context

The framework is being updated to support production-grade deployments, requiring maximum reliability, strict security boundary enforcement, high-throughput tool execution, and robust fallback behaviors when accessing remote LLMs.

## Constraints

- **Compatibility**: Codebase must remain compatible with Windows, macOS, and Linux.
- **Safety**: Security validations must not block valid administration or development tasks (must never say "no").
- **Dependencies**: New features (e.g., semantic memory, encryption) must be optionally loadable to maintain a lightweight core.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Initialize v1.0 Milestone | Start a structured roadmap to transition AgenticOS to a production-ready 10/10 platform | — Pending |

## Current Milestone: v1.0 Comprehensive 10/10 Rating Analysis

**Goal:** Address key gaps to elevate AgenticOS's capabilities to a 10/10 across all 10 critical dimensions.

**Target features:**
- Security Enhancements (Unicode, code-gen intercept, registry, symlink)
- Code Quality & Type Safety (Pydantic models, modularization, Tool protocol)
- Advanced Documentation (deployment, threat model, cost estimator)
- Performance Optimizations (adaptive context, streaming, indexing, parallelization)
- OS Control & Tuning (macOS system access, Linux desktop env, embedded optimization)
- Enhanced Autonomy (smart retry, success criteria, stall detection, long-term orchestrator)
- Rich Extensibility (async tool, streaming tool, remote plugin registry, tool composer)
- Testing & Resiliency (E2E, mutation, performance benchmarks, chaos monkey)
- Smart Memory/Context (semantic memory FAISS, decaying memory, episodic clustering, validated memory)
- LLM Integration (fallback routing, cost optimizer, model-specific prompts, structured output)

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-26 after Phase 3 completion*
