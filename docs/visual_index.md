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

How AgenticOS categorizes your filesystem and enforces safety across all four security zones.

```mermaid
graph LR
    subgraph "Green Zone (Workspace Isolation)"
        W[workspace/]
    end
    subgraph "Yellow Zone (System-Wide Autonomy)"
        U[Users/]
        D[Data/]
    end
    subgraph "Red Zone (Strictly Blocked)"
        Win[Windows/]
        PF[Program Files/]
    end
    subgraph "Blue Zone (Read-Only / Audit)"
        RO[Entire Filesystem]
    end
    
    Agent -->|Free Access| W
    Agent -->|HITM Prompt / Allowed| U
    Agent -->|BLOCKED| Win
    Agent -->|Read-Only / Writes Blocked| RO
```

---

## The "Fast-Path" Optimization Flow

How the system scans filesystems at high speed using an optimized native Python depth-first search (DFS) stack.

```mermaid
graph TD
    A[Agent Requests File Audit] --> B[Initialize DFS Stack with Path]
    B --> C{Stack Empty?}
    C -- Yes --> D[Filter, Sort and Format Results]
    C -- No --> E[Pop Directory from Stack]
    E --> F[Scan Directory using os.scandir]
    F --> G{Loop Entries}
    G --> H{Is Symlink or NTFS Junction?}
    H -- Yes --> G
    H -- No --> I{Is File?}
    I -- Yes --> J[Check Selection Criteria]
    I -- No --> K{Is Dir?}
    K -- Yes --> L[Push Dir to Stack]
    L --> G
    J --> G
    K -- No --> G
    G -- Loop Finished --> C
    D --> M[Return Result Report to Agent]
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
These diagrams represent the "Hardened" v2.1.1 architecture. For deeper technical details, use the [Documentation Catalog](CATALOG.md) or the links in the [README](../README.md).

---

*Last Updated: 2026-05-14*
*Status: Visual Index Verified*
