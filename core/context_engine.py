"""
ContextEngine for AgenticOs.
Manages system prompt assembly, message history pruning, 
and proactive context injection (Active Recall).
"""
import os
from typing import TYPE_CHECKING, Any, Optional, Tuple, List, Dict

from core.runtime_config import DEFAULT_SCAN_EXCLUDED_DIRS

if TYPE_CHECKING:
    from core.runtime import Agent


class ContextEngine:
    def __init__(self, agent: "Agent") -> None:
        """Initialize the context engine.
        
        Args:
            agent: The agent instance containing configuration and runtime state.
        """
        self.agent = agent
        self.cfg = agent.cfg
        self.workspace = agent.workspace
        self.memory_manager: Optional[Any] = None  # Set later via agent.memory_manager
        self.max_messages: Optional[int] = None
        
    def set_compact_threshold(self, n: int) -> None:
        """Set the history compaction threshold limit (max_messages)."""
        self.max_messages = n
        
    def set_memory_manager(self, manager: Any) -> None:
        """Set the memory manager instance.
        
        Args:
            manager: The memory manager instance to use for context retrieval.
        """
        self.memory_manager = manager

    def _scan_workspace(self) -> Tuple[List[str], List[Tuple[str, str]]]:
        """Dynamically scan the workspace to build a real-time file map and inject all .md files.
        
        Returns:
            A tuple of (file_map_lines, md_files) where file_map_lines is a list of formatted
            file descriptions and md_files is a list of (filename, path) tuples for markdown files.
        """
        file_map_lines = []
        md_files = []
        ignore_dirs = set(
            self.cfg.get("context", {}).get(
                "workspace_ignore_dirs", DEFAULT_SCAN_EXCLUDED_DIRS
            )
        )

        try:
            for entry in sorted(os.listdir(self.workspace)):
                if entry in ignore_dirs or entry.startswith("."):
                    continue
                full_path = os.path.join(self.workspace, entry)
                if os.path.isdir(full_path):
                    # Count children for context
                    try:
                        child_count = len(os.listdir(full_path))
                    except OSError:
                        child_count = 0
                    file_map_lines.append(f"  {entry}/  ({child_count} items)")
                elif os.path.isfile(full_path):
                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        size = 0
                    file_map_lines.append(f"  {entry}  ({size} bytes)")
                    # Collect .md files to inject
                    if entry.lower().endswith(".md"):
                        md_files.append((entry, full_path))
        except OSError:
            pass

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
            except OSError as e:
                from core.logger import get_logger
                get_logger("context_engine").warning("Failed to auto-inject file %s: %s", f_name, e)

        return system + workspace_block + task_block + canvas_block + shadow_block + proactive_block + file_map_block + file_memory_block

    def get_active_recall(self, user_input: str) -> str:
        """Perform pre-flight retrieval from memory manager.
        
        Args:
            user_input: The user's input query to retrieve relevant context for.
            
        Returns:
            A string containing relevant context from the memory manager, or an empty
            string if no memory manager is available.
        """
        if not self.memory_manager:
            return ""
        return self.memory_manager.get_relevant_context(user_input)

    def get_commitments(self) -> str:
        """Retrieve active commitments.
        
        Returns:
            A string containing active commitments from the memory manager, or an empty
            string if no memory manager is available.
        """
        if not self.memory_manager:
            return ""
        return self.memory_manager.get_active_commitments()

    def collapse_large_messages(self, messages: List[Dict[str, str]], threshold: int = 4000) -> List[Dict[str, str]]:
        """Scan messages and collapse those exceeding threshold by truncating the middle."""
        collapsed_messages = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role != "system" and len(content) > threshold:
                keep_size = threshold // 2
                first_part = content[:keep_size]
                last_part = content[-keep_size:]
                collapsed_count = len(content) - (keep_size * 2)
                new_content = f"{first_part}\n\n[... COLLAPSED {collapsed_count} CHARACTERS ...]\n\n{last_part}"
                collapsed_messages.append({"role": role, "content": new_content})
            else:
                collapsed_messages.append(msg)
        return collapsed_messages

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count based on a 4 characters per token heuristic."""
        return len(text or "") // 4

    def get_max_context_tokens(self) -> int:
        """Retrieve maximum context window limit for the active model."""
        client = getattr(self.agent, "client", None)
        if client:
            ctx = getattr(client, "ctx", None)
            if ctx is not None and isinstance(ctx, (str, int, float)) and not isinstance(ctx, bool):
                try:
                    return int(ctx)
                except (ValueError, TypeError):
                    pass
        
        ollama_ctx = self.cfg.get("ollama", {}).get("num_ctx")
        if ollama_ctx:
            try:
                return int(ollama_ctx)
            except (ValueError, TypeError):
                pass
                
        return int(self.cfg.get("performance", {}).get("max_context_tokens", 32000))

    def calculate_total_tokens(self, messages: List[Dict[str, str]], system_prompt: str = "") -> int:
        """Calculate total estimated tokens of the conversation context."""
        total = self.estimate_tokens(system_prompt)
        for msg in messages:
            total += self.estimate_tokens(msg.get("content", ""))
        return total

    def compact_history(self, messages: List[Dict[str, str]], max_messages: int = 40) -> List[Dict[str, str]]:
        """Compress old messages into a high-density summary to preserve context.
        
        When conversation history exceeds max_messages or approaching token limit, 
        the oldest chat messages are summarized.
        """
        if self.max_messages is not None:
            max_messages = self.max_messages

        # 1. Collapse individual messages exceeding the character limit (PERF-01)
        threshold = int(self.cfg.get("performance", {}).get("max_message_char_threshold", 4000))
        messages = self.collapse_large_messages(messages, threshold=threshold)

        # 2. Get context token limits
        max_tokens = self.get_max_context_tokens()
        trigger_tokens = int(max_tokens * 0.8)
        
        # Build system prompt context for token estimation
        system_prompt = self.build_system_prompt()
        total_tokens = self.calculate_total_tokens(messages, system_prompt)
        
        # Check if we should trigger compaction
        should_compact = len(messages) > max_messages or total_tokens > trigger_tokens
        
        if not should_compact:
            return messages

        # Separate system instructions from interactive chat messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        chat_msgs = [m for m in messages if m.get("role") != "system"]

        # If we don't have enough chat messages to warrant compaction, just return original messages
        if len(chat_msgs) <= 4:
            return messages

        # Determine how many recent chat messages to keep intact
        if total_tokens > trigger_tokens:
            budget = int(max_tokens * 0.4)
            current_tokens = self.estimate_tokens(system_prompt)
            keep_count = 0
            for msg in reversed(chat_msgs):
                msg_tokens = self.estimate_tokens(msg.get("content", ""))
                if current_tokens + msg_tokens > budget:
                    break
                current_tokens += msg_tokens
                keep_count += 1
            keep_recent = max(2, keep_count)
        else:
            keep_recent = max(10, min(20, (max_messages - len(system_msgs)) // 2))

        if len(chat_msgs) <= keep_recent:
            return messages

        to_compact = chat_msgs[:-keep_recent]
        to_keep = chat_msgs[-keep_recent:]

        # Try LLM-powered compaction
        llm = getattr(self.agent, "client", None)
        compact_cfg = self.cfg.get("prompts", {}).get("compaction", {})
        
        compacted_msg = None
        if llm and hasattr(llm, "chat"):
            try:
                # Build a transcript of the old messages
                transcript_lines = []
                for m in to_compact:
                    role = m.get("role", "user").upper()
                    content = m.get("content", "")[:500]
                    transcript_lines.append(f"{role}: {content}")
                transcript = "\n".join(transcript_lines)

                system_prompt_comp = compact_cfg.get("system", (
                    "You are a context compaction unit. Summarize history. Be concise."
                ))

                summary = llm.chat(
                    messages=[{"role": "user", "content": transcript}],
                    system=system_prompt_comp,
                )

                if summary and summary.strip():
                    start_marker = compact_cfg.get("marker_start", "[COMPACTED CONTEXT]\n")
                    end_marker = compact_cfg.get("marker_end", "\n[END COMPACTED CONTEXT]")
                    compacted_msg = {
                        "role": "user",
                        "content": f"{start_marker}{summary.strip()}{end_marker}",
                    }
            except Exception as e:
                from core.logger import get_logger
                get_logger("context_engine").warning("LLM context compaction failed, falling back to truncation: %s", e)

        # Fallback to simple truncation if LLM compaction is unavailable or failed
        if not compacted_msg:
            fallback_tmpl = compact_cfg.get("fallback_note", "[CONTEXT NOTE: {count} messages pruned]")
            compacted_msg = {
                "role": "user",
                "content": fallback_tmpl.format(count=len(to_compact)),
            }

        return system_msgs + [compacted_msg] + to_keep
