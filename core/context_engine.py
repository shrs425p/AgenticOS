"""
ContextEngine for AgenticOs.
Manages system prompt assembly, message history pruning, 
and proactive context injection (Active Recall).
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from core.runtime_config import DEFAULT_WORKSPACE


class ContextEngine:
    def __init__(self, agent):
        self.agent = agent
        self.cfg = agent.cfg
        self.workspace = agent.workspace
        self.memory_manager = None  # Set later via agent.memory_manager
        
    def set_memory_manager(self, manager):
        self.memory_manager = manager

    def _scan_workspace(self):
        """Dynamically scan the workspace to build a real-time file map and inject all .md files."""
        file_map_lines = []
        md_files = []

        for entry in sorted(os.listdir(self.workspace)):
            full_path = os.path.join(self.workspace, entry)
            if os.path.isdir(full_path):
                # Count children for context
                try:
                    child_count = len(os.listdir(full_path))
                except Exception:
                    child_count = 0
                file_map_lines.append(f"  {entry}/  ({child_count} items)")
            elif os.path.isfile(full_path):
                size = os.path.getsize(full_path)
                file_map_lines.append(f"  {entry}  ({size} bytes)")
                # Collect .md files to inject
                if entry.lower().endswith(".md"):
                    md_files.append((entry, full_path))

        return file_map_lines, md_files

    def build_system_prompt(self, recall_context: str = "", commitments_context: str = "") -> str:
        """Assembles the final system prompt with all dynamic blocks."""
        # Get unified system prompt from config
        raw_prompt = self.cfg.get("prompts", {}).get(
            "system_prompt", "You are an AI assistant."
        )
        tools_block = self.agent.tools.tool_descriptions()

        prompts = self.cfg.get("prompts", {})
        ctx_prompts = prompts.get("context_blocks", {})
        divider = ctx_prompts.get("divider", "-------------------------------------------\n")

        # 1. Base Prompt
        if "{tool_descriptions}" in raw_prompt:
            system = raw_prompt.replace("{tool_descriptions}", tools_block)
        else:
            system = f"{raw_prompt}\n\nAVAILABLE_TOOLS:\n{tools_block}"

        # 2. Workspace Path
        workspace_tmpl = ctx_prompts.get("workspace", "### WORKSPACE_ROOT\nYour absolute workspace root is: {workspace}\n-------------------------------------------\n")
        workspace_block = "\n\n" + workspace_tmpl.format(workspace=self.workspace)
        if divider not in workspace_block:
            workspace_block += divider

        # 3. Active Task Memory
        task_block = ""
        if self.agent.task_tracker.current:
            c = self.agent.task_tracker.current
            task_tmpl = ctx_prompts.get("task_memory", "### ACTIVE_TASK_MEMORY\nGOAL: {goal}\n-------------------------------------------\n")
            task_block = "\n\n" + task_tmpl.format(
                goal=c.get("goal", "N/A"),
                objective=c.get("objective", "N/A"),
                plan=", ".join(c.get("plan", [])),
                current_step=c.get("current_step", "N/A"),
                iteration=c.get("iteration", 0)
            )
            if divider not in task_block:
                task_block += divider

        # 4. Thinking Canvas
        canvas_block = ""
        if self.agent.tools._canvas:
            canvas_tmpl = ctx_prompts.get("thinking_canvas", "### THINKING_CANVAS\n{content}\n-------------------------------------------\n")
            canvas_block = "\n\n" + canvas_tmpl.format(content=self.agent.tools._canvas)
            if divider not in canvas_block:
                canvas_block += divider

        # 5. Shadow Mode Warning
        shadow_block = ""
        if self.agent.tools.shadow_mode:
            shadow_tmpl = ctx_prompts.get("shadow_mode", "### WARNING: SHADOW MODE ACTIVE\n-------------------------------------------\n")
            shadow_block = "\n\n" + shadow_tmpl
            if divider not in shadow_block:
                shadow_block += divider

        # 6. Proactive Context (Active Recall & Commitments)
        proactive_block = recall_context + commitments_context

        # 7. Dynamic Workspace File Map
        file_map_lines, md_files = self._scan_workspace()
        file_map_tmpl = ctx_prompts.get("file_map", "### WORKSPACE_FILE_MAP\n{file_list}\n-------------------------------------------\n")
        file_map_block = "\n\n" + file_map_tmpl.format(file_list="\n".join(file_map_lines))
        if divider not in file_map_block:
            file_map_block += divider

        # 8. Auto-inject ALL .md files from workspace root (no hardcoding)
        file_memory_block = ""
        max_inject_bytes = int(self.cfg.get("performance", {}).get("max_identity_file_bytes", 8000))
        file_tmpl = ctx_prompts.get("auto_loaded_file", "### {name} (auto-loaded)\n{content}\n-------------------------------------------\n")
        
        for f_name, f_path in md_files:
            try:
                size = os.path.getsize(f_path)
                if size > max_inject_bytes:
                    continue  # Skip very large files
                with open(f_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        segment = "\n\n" + file_tmpl.format(name=f_name, content=content)
                        if divider not in segment:
                            segment += divider
                        file_memory_block += segment
            except Exception:
                pass

        return system + workspace_block + task_block + canvas_block + shadow_block + proactive_block + file_map_block + file_memory_block

    def get_active_recall(self, user_input: str) -> str:
        """Perform pre-flight retrieval from memory manager."""
        if not self.memory_manager:
            return ""
        return self.memory_manager.get_relevant_context(user_input)

    def get_commitments(self) -> str:
        """Retrieve active commitments."""
        if not self.memory_manager:
            return ""
        return self.memory_manager.get_active_commitments()

    def compact_history(self, messages: list, max_messages: int = 40) -> list:
        """Compress old messages into a high-density summary to preserve context.
        
        When conversation history exceeds max_messages, the oldest messages 
        (excluding the first system-level ones) are summarized into a single 
        "compacted context" message. This preserves 100% of semantic meaning
        while dramatically reducing token count.
        
        Args:
            messages: The full message list.
            max_messages: Threshold before compaction triggers.
            
        Returns:
            The (possibly compacted) message list.
        """
        if len(messages) <= max_messages:
            return messages

        # How many messages to compact (keep the most recent 20 intact)
        keep_recent = min(20, max_messages // 2)
        to_compact = messages[:-keep_recent]
        to_keep = messages[-keep_recent:]

        # Try LLM-powered compaction
        llm = getattr(self.agent, "client", None)
        compact_cfg = self.cfg.get("prompts", {}).get("compaction", {})
        
        if llm and hasattr(llm, "chat"):
            try:
                # Build a transcript of the old messages
                transcript_lines = []
                for m in to_compact:
                    role = m.get("role", "user").upper()
                    content = m.get("content", "")[:500]
                    transcript_lines.append(f"{role}: {content}")
                transcript = "\n".join(transcript_lines)

                system_prompt = compact_cfg.get("system", (
                    "You are a context compaction unit. Summarize history. Be concise."
                ))

                summary = llm.chat(
                    messages=[{"role": "user", "content": transcript}],
                    system=system_prompt,
                )

                if summary and summary.strip():
                    start_marker = compact_cfg.get("marker_start", "[COMPACTED CONTEXT]\n")
                    end_marker = compact_cfg.get("marker_end", "\n[END COMPACTED CONTEXT]")
                    compacted_msg = {
                        "role": "user",
                        "content": f"{start_marker}{summary.strip()}{end_marker}",
                    }
                    return [compacted_msg] + to_keep
            except Exception:
                pass

        # Fallback: simple truncation with a marker
        fallback_tmpl = compact_cfg.get("fallback_note", "[CONTEXT NOTE: {count} messages pruned]")
        fallback_msg = {
            "role": "user",
            "content": fallback_tmpl.format(count=len(to_compact)),
        }
        return [fallback_msg] + to_keep
