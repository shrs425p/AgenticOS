# Roadmap: AgenticOS

## Overview

This roadmap defines the 4-phase execution plan for the AgenticOS v1.0 milestone. The goal is to address all core security, quality, performance, and control gaps systematically, transforming the codebase from its current state into a production-grade, highly autonomous, and secure local OS command execution framework.

## Phases

- [x] **Phase 1: Core Security and Code Quality Foundation** - Solidify runtime against exploits and modularize codebase structure.
- [ ] **Phase 2: Performance and LLM Integration Layer** - Enhance processing speed, concurrency, and remote LLM communication resilience.
- [ ] **Phase 3: Platform OS Control and Autonomy Framework** - Expand native desktop controls, hardware auto-tuning, and robust agent retry loops.
- [ ] **Phase 4: Memory, Extensibility, and Resiliency Harness** - Implement local FAISS vector indexing, async/streaming plugin pipelines, and chaos test suites.

## Phase Details

### Phase 1: Core Security and Code Quality Foundation

**Goal**: Build AST unicode guards, Pydantic action models, modularize runtime, and establish security regression tests.
**Depends on**: Nothing
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, QUAL-01, QUAL-02, QUAL-03, QUAL-04, DOC-02, TEST-05
**Success Criteria** (what must be TRUE):

  1. The system blocks PowerShell cast payloads (`$([char]0x73)`) and unicode escapes before execution.
  2. The system intercepts and blocks shell-redirection code-gen (`echo payload > script.sh`).
  3. Action parameter execution payloads are validated via Pydantic model schemas.
  4. Large functions in `core/runtime.py` are cleanly separated into orchestrator, dispatcher, memory, and error files.

**Plans**: 4/4 plans executed

Plans:

- [x] 01-01-PLAN.md: AST validator and unicode/character cast escape guard.
- [x] 01-02-PLAN.md: Symlink resolution canonicalizer and path traversal block.
- [x] 01-03-PLAN.md: Pydantic configuration schemas and runtime sub-module refactoring.
- [x] 01-04-PLAN.md: Security threat model and test-suite regression coverage.

---

### Phase 2: Performance and LLM Integration Layer

**Goal**: Add adaptive context windows, streaming action parsers, parallel execution, and resilient routing fallback strategies.
**Depends on**: Phase 1
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, INTEG-01, INTEG-02, INTEG-03, INTEG-04, INTEG-05, DOC-03
**Success Criteria** (what must be TRUE):

  1. Context window history compactor compresses middle logs when history exceeds token limits.
  2. Action dispatcher parses and yields JSON chunks from LLM streaming stream.
  3. Independent tools in execution dependency graphs run concurrently.
  4. Structured schema retries and smart LLM fallback routing are active.

**Plans**: 3 plans

Plans:

- [x] 02-01: Adaptive context sliding window and compression manager.
- [x] 02-02: Streaming JSON parser and parallel execution action graph scheduler.
- [x] 02-03: Cost-aware LLM fallback router, model-specific templates, and token estimators.

---

### Phase 3: Platform OS Control and Autonomy Framework

**Goal**: Integrate deep macOS/Wayland support, ARM hardware tuning, multi-session checkpoint loops, and smart retries.
**Depends on**: Phase 2
**Requirements**: OS-01, OS-02, OS-03, AUTO-01, AUTO-02, AUTO-03, AUTO-04, AUTO-05, DOC-01
**Success Criteria** (what must be TRUE):

  1. macOS accessibility client lists active windows and interacts with Cocoa apps.
  2. Wayland session detects desktop environment and captures screenshots natively.
  3. The system scales context window parameters dynamically based on local CPU/RAM size.
  4. Execution loops analyze error logs, retry transient errors, and verify success criteria.

**Plans**: 3 plans

Plans:

- [ ] 03-01: macOS system events client and Wayland screenshot integration.
- [ ] 03-02: System resource profiler tuner and multi-session phase/checkpoint manager.
- [ ] 03-03: Smart repetition transient error analyzer and duration stall alarms.

---

### Phase 4: Memory, Extensibility, and Resiliency Harness

**Goal**: Implement FAISS vector memory decay, async streaming plugins, dependency checking, and E2E/chaos testing.
**Depends on**: Phase 3
**Requirements**: MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, EXT-01, EXT-02, EXT-03, EXT-04, EXT-05, TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):

  1. FAISS memory lookup retrieves relevant contexts weighted with a 30-day exponential half-life decay.
  2. The system executes async tools and pipes output streams sequentially.
  3. Remote plugin registry downloads and installs compatible custom tools.
  4. Chaos monkey harness tests framework resiliency under API failure and database corruption scenarios.

**Plans**: 4 plans

Plans:

- [ ] 04-01: FAISS vector storage memory module with mathematical time-decay and episodic clustering.
- [ ] 04-02: Async tool execution protocols and piping composers.
- [ ] 04-03: Remote plugin registry installer and package dependency compatibility resolver.
- [ ] 04-04: Multi-step E2E integration test suite, mutation test framework, and chaos monkey harness.

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Security & Code Quality | 4/4 | Complete    | 2026-06-26 |
| 2. Performance & LLM | 3/3 | Complete    | 2026-06-26 |
| 3. OS Control & Autonomy | 0/3 | Planned | - |
| 4. Memory & Resiliency | 0/4 | Planned | - |
