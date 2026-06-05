# AgenticOS: Prompt Engineering and Task Optimization

While AgenticOS is highly autonomous, the quality of its output depends significantly on how you structure your requests. This document provides best practices for "Prompt Engineering" within the context of an autonomous OS agent to ensure accuracy, safety, and speed.

---

## The Anatomy of a Perfect Prompt

A high-performance prompt for AgenticOS should contain three elements: **Context**, **Objective**, and **Verification**.

### Weak Prompt:
> *"Clean up my computer."*
> **Result**: The agent might wander aimlessly, looking for temp files or large videos, wasting tokens.

### Strong Prompt:
> *"Analyze my `%USERPROFILE%\Downloads` folder. Identify any .zip or .exe files older than 30 days that are larger than 500MB. Write a list of these files to `workspace/cleanup_suggestions.md` and ask for my permission before deleting anything."*
> **Result**: The agent has a clear directory, specific criteria, a defined output format, and a safety constraint.

---

## Leveraging the Reasoning Engine

AgenticOS is designed to "Think Before Acting." You can nudge this behavior to improve success rates on complex tasks.

### 1. Chain-of-Thought (CoT)
Ask the agent to explain its plan before it starts.
-   **Prompt**: *"I want to audit my firewall. First, explain your plan step-by-step, then wait for my 'go' before running the first command."*

### 2. Multi-Step Decomposition
For massive tasks, break them down into sub-objectives.
-   **Step 1**: *"Find all duplicate images in my Photos folder."*
-   **Step 2**: *"Of those duplicates, identify which ones have the lowest resolution."*
-   **Step 3**: *"Move the low-res duplicates to a 'trash' folder in the workspace."*

---

## Avoiding Hallucination Loops

Agents can sometimes get stuck in a "hallucination loop" where they guess file paths or tool arguments repeatedly.

### Strategies to Break Loops:
1.  **Enforce Inspection**: Add *"Always call list_dir before assuming a file exists"* to your prompt.
2.  **Constraint-Based Prompting**: Add *"If you cannot find the file after 2 attempts, stop and ask me for the path."*
3.  **Self-Correction Nudge**: If you see the agent failing, tell it: *"Your last tool call failed with 'File Not Found'. Try using search_files to locate the executable first."*

---

## Performance Prompting

To make the agent work faster (and save on API costs):

### 1. Use the "Native-First" Keyword
Remind the agent to use optimized tools for heavy lifting.
-   Prompt: *"Audit my drive. **Use Fast-Path tools** for the search to ensure it runs fast."*

### 2. Batching Requests
Instead of one-by-one commands, give the agent a structured list.
-   **Prompt**: *"Perform these 3 checks: 1. Disk Health, 2. Process Count, 3. Network Usage. Write all results into a single report."*

---

## Task-Specific Prompt Templates

### For Security Audits:
> *"Act as a security researcher. Enumerate all auto-start programs. Cross-reference their names against a web search for known malware or adware. Flag any that look suspicious and provide a rationale."*

### For Code Refactoring:
> *"Analyze the 'core/runtime.py' file. Identify any functions that lack docstrings or have high cyclomatic complexity. Propose a refactor for the most complex function but do not apply changes yet."*

---

## Handling File Chunks

If you are working with a 5,000-line source file, the agent cannot read it all at once without hitting context limits.
-   **Prompt**: *"I need to fix a bug in 'main.py' around line 1200. Read lines 1150 to 1250 and explain what the logic is doing."*

---

## Prompt Engineering Best Practices

-   **Be Specific**: Use absolute paths whenever possible.
-   **Set Boundaries**: Use "Do not..." or "Avoid..." to prevent the agent from touching sensitive data.
-   **Define Output**: Ask for Markdown tables, CSVs, or specific filenames to make the results usable.
-   **Iterate**: If the first response is 80% correct, don't restart. Give a follow-up prompt: *"Great, now format that table by file size in descending order."*

---

## Summary
Think of the agent as a highly capable intern. The more context and structure you provide, the less likely it is to make a mistake. By combining **Specific Objectives** with **Native-Path Optimization**, you can unlock the full "Hardened" power of AgenticOS.

---

*Last Updated: 2026-06-03*
*Status: Developer Ready*
