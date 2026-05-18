# AgenticOS: Visual Index and Flowcharts

This document serves as a central hub for all technical diagrams and architectural flowcharts within AgenticOS. It provides a visual representation of how the agent thinks, acts, and maintains system safety.

---

## The System Macro-Architecture

This diagram shows the high-level relationship between the user, the core orchestrator, and the host operating system.

```mermaid
graph TD
    User([User Request]) --> Main[main.py]
    Main --> Orchestrator[Runtime Orchestrator]
    Orchestrator --> Agent[Autonomous Agent]
    Agent --> Memory[Session Memory / SQLite]
    Agent --> Registry[Tool Registry]
    Registry --> Files[Filesystem Tools]
    Registry --> Terminal[Terminal & OS Tools]
    Registry --> Web[Web & API Tools]
    Registry --> Browser[Playwright Automation]
    Registry --> Plugins[Dynamic Plugins]
    
    Orchestrator --> UI[Typewriter UI / Notifications]
    Orchestrator --> Guard[PathGuard / Security]
```

---

## The Reasoning Cycle (Cortex Engine)

The internal logic flow of a single agent iteration.

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant M as LLM Provider
    participant R as Tool Registry
    participant S as System/OS

    O->>M: Send Context (Plan + History + Metrics)
    M-->>O: Return Thought + Action JSON
    O->>R: Validate Action & Security Check
    R->>S: Execute Native Command (PS/Bash/Python)
    S-->>R: Return Raw Output
    R-->>O: Return Observation
    O->>O: Re-evaluate Plan & Summarize
```

---

## Zone-Based Security (PathGuard)

How AgenticOS categorizes your filesystem and enforces safety.

```mermaid
graph LR
    subgraph "Green Zone (Full Autonomy)"
        W[workspace/]
    end
    subgraph "Yellow Zone (Read-Only / HITM)"
        U[Users/]
        D[Data/]
    end
    subgraph "Red Zone (Strictly Blocked)"
        Win[Windows/]
        PF[Program Files/]
    end
    
    Agent -->|Free Access| W
    Agent -->|HITM Prompt| U
    Agent -->|BLOCKED| Win
```

---

## The "Fast-Path" Optimization Flow

How the system switches between slow Python processing and high-speed PowerShell pipelines.

```mermaid
graph TD
    A[Agent Requests File Audit] --> B{Path is Root C:?}
    B -- Yes --> C[Trigger Fast-Path Optimization]
    B -- No --> D[Use Standard Python Walker]
    C --> E[Spawn Native PowerShell Pipeline]
    E --> F[Streaming Result to CSV]
    F --> G[Summarize Results for Agent]
    D --> G
```

---

## Persistent Memory Layers

The relationship between short-term context and long-term SQLite storage.

```mermaid
graph TD
    subgraph "In-Memory (Ephemeral)"
        C[Active Conversation History]
    end
    subgraph "On-Disk (Persistent)"
        S[SQLite: Event Log]
        J[JSONL: Audit Trace]
        M[Markdown: Task Artifacts]
    end
    
    C <-->|Sync| S
    S -->|Backup| J
    Agent -->|Produce| M
```

---

## Summary
These diagrams represent the "Hardened" v2.1.0 architecture. For deeper technical details, use the [Documentation Catalog](CATALOG.md) or the links in the [README](../README.md).

---

*Last Updated: 2026-05-14*
*Status: Visual Index Verified*
