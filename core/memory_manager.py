
"""
Enhanced memory management system for AgenticOs.
Provides long-term memory consolidation, daily logging, and knowledge retention.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading
from core.logger import get_logger
logger = get_logger(__name__)



logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages long-term memory consolidation and daily logging for AgenticOs."""
    
    def __init__(self, workspace_root: str, llm_client: Optional[Any] = None, cfg: Optional[Dict] = None):
        self.workspace_root = Path(workspace_root).resolve()
        self.cfg = cfg or {}
        self.memory_dir = self.workspace_root / "memory"
        self.memory_dir.mkdir(exist_ok=True)
        
        self.long_term_memory_file = self.workspace_root / "MEMORY.md"
        self.daily_memory_dir = self.memory_dir
        self.llm_client = llm_client
        
        # Configuration
        self.max_daily_entries = 50
        self.memory_consolidation_threshold = 5  # Consolidate after 5 completed tasks
        
        self.commitments_file = self.memory_dir / "commitments.json"
        self._lock = threading.RLock()  # Add lock for thread safety
        self.commitments = self._load_commitments()
        
    def _load_commitments(self) -> List[Dict[str, Any]]:
        """Load pending commitments from disk."""
        if self.commitments_file.exists():
            try:
                with self._lock:
                    with open(self.commitments_file, "r", encoding="utf-8") as f:
                        return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load commitments: {e}")
                return []
        return []

    def _save_commitments(self):
        """Save commitments to disk with thread safety."""
        try:
            with self._lock:
                with open(self.commitments_file, "w", encoding="utf-8") as f:
                    json.dump(self.commitments, f, indent=2)
        except (IOError, OSError) as e:
            logger.error(f"Failed to save commitments: {e}")

    def register_commitment(self, text: str, due_date: Optional[str] = None):
        """Register a new commitment/follow-up."""
        import secrets
        commitment = {
            "id": secrets.token_hex(4),
            "text": text,
            "created_at": datetime.now().isoformat(),
            "due_date": due_date,
            "status": "pending"
        }
        self.commitments.append(commitment)
        self._save_commitments()
        self.log_daily_event("COMMITMENT_REGISTERED", f"New commitment: {text}", {"due": due_date})
        return f"Commitment registered: {text}"

    def get_active_commitments(self) -> str:
        """Get all pending commitments formatted for system prompt."""
        active = [c for c in self.commitments if c.get("status") == "pending"]
        if not active:
            return ""
        
        header = self.cfg.get("prompts", {}).get("memory_blocks", {}).get("commitments_header", "### ACTIVE_COMMITMENTS (Follow-ups)")
        lines = [header]
        for c in active:
            due = f" [Due: {c['due_date']}]" if c.get('due_date') else ""
            lines.append(f"- {c['text']}{due} (ID: {c['id']})")
        return "\n".join(lines) + "\n-------------------------------------------\n"

    def complete_commitment(self, commitment_id: str):
        """Mark a commitment as completed."""
        for c in self.commitments:
            if c["id"] == commitment_id:
                c["status"] = "completed"
                c["completed_at"] = datetime.now().isoformat()
                self._save_commitments()
                return f"Commitment {commitment_id} marked as completed."
        return f"Error: Commitment {commitment_id} not found."

    def get_relevant_context(self, query: str, limit: int = 3) -> str:
        """Retrieve relevant snippets from long-term memory for pre-flight injection (Active Recall)."""
        if not query or len(query) < 4:
            return ""
            
        q = query.lower().strip()
        results = []
        
        # 1. Search MEMORY.md
        if self.long_term_memory_file.exists():
            try:
                with open(self.long_term_memory_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if q in line.lower():
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            snippet = "".join(lines[start:end]).strip()
                            results.append(f"[MEMORY.md] ...{snippet}...")
                            if len(results) >= limit:
                                break
            except (IOError, OSError) as e:
                logger.debug(f"Failed to search MEMORY.md: {e}")

        # 2. Search recent daily logs (last 3 days)
        if len(results) < limit:
            for i in range(3):
                date = datetime.now() - timedelta(days=i)
                daily_file = self.get_daily_memory_file(date)
                if daily_file.exists():
                    try:
                        with open(daily_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            if q in content.lower():
                                results.append(f"[LOG {date.strftime('%Y-%m-%d')}] Relevant context found.")
                                if len(results) >= limit:
                                    break
                    except (IOError, OSError) as e:
                        logger.debug(f"Failed to search daily log {date}: {e}")
        
        if not results:
            return ""
            
        header = "\n### ACTIVE_RECALL (Relevant Context Found from Memory)\n"
        return header + "\n".join(results) + "\n-------------------------------------------\n"
        
    def get_daily_memory_file(self, date: Optional[datetime] = None) -> Path:
        """Get the memory file for a specific date (defaults to today)."""
        if date is None:
            date = datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        return self.daily_memory_dir / f"memory-{date_str}.md"
    
    def log_daily_event(self, event_type: str, description: str, metadata: Optional[Dict] = None):
        """Log an event to the daily memory file."""
        daily_file = self.get_daily_memory_file()
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format the log entry
        log_entry = f"## [{timestamp}] {event_type}\n"
        log_entry += f"{description}\n"
        
        if metadata:
            log_entry += "\n**Metadata:**\n"
            for key, value in metadata.items():
                log_entry += f"- {key}: {value}\n"
        
        log_entry += "\n---\n\n"
        
        # Append to daily file
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
            
        # Check if we need to consolidate memory
        self._check_consolidation_needed()
    
    def log_task_completion(self, task_goal: str, final_answer: str, tools_used: List[str], 
                           success: bool, duration: float, metadata: Optional[Dict] = None):
        """Log a completed task to daily memory and prepare for consolidation."""
        event_description = f"""
**Goal:** {task_goal}

**Result:** {'SUCCESS' if success else 'FAILED'}
**Duration:** {duration:.2f}s
**Tools Used:** {', '.join(tools_used) if tools_used else 'None'}

**Final Answer:**
{final_answer[:500]}{'...' if len(final_answer) > 500 else ''}
""".strip()
        
        task_metadata = {
            "success": success,
            "duration_seconds": duration,
            "tools_count": len(tools_used),
            "answer_length": len(final_answer)
        }
        
        if metadata:
            task_metadata.update(metadata)
            
        self.log_daily_event("TASK_COMPLETION", event_description, task_metadata)
        
        # Track for consolidation
        self._track_completed_task({
            "goal": task_goal,
            "result": final_answer,
            "tools_used": tools_used,
            "success": success,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })
    
    def _track_completed_task(self, task_info: Dict[str, Any]):
        """Track completed tasks for memory consolidation."""
        tracking_file = self.memory_dir / "task_tracking.json"
        
        # Load existing tracking data
        if tracking_file.exists():
            with open(tracking_file, "r", encoding="utf-8") as f:
                tracking_data = json.load(f)
        else:
            tracking_data = {"completed_tasks": [], "last_consolidation": None}
        
        # Add new task
        tracking_data["completed_tasks"].append(task_info)
        
        # Keep only recent tasks to prevent file from growing too large
        tracking_data["completed_tasks"] = tracking_data["completed_tasks"][-100:]
        
        # Save back
        with open(tracking_file, "w", encoding="utf-8") as f:
            json.dump(tracking_data, f, indent=2)
    
    def _check_consolidation_needed(self):
        """Check if memory consolidation should be triggered."""
        tracking_file = self.memory_dir / "task_tracking.json"
        
        if not tracking_file.exists():
            return
            
        try:
            with open(tracking_file, "r", encoding="utf-8") as f:
                tracking_data = json.load(f)
            
            completed_tasks = tracking_data.get("completed_tasks", [])
            last_consolidation = tracking_data.get("last_consolidation")
            
            # Consolidate if we have enough new tasks since last consolidation
            if len(completed_tasks) >= self.memory_consolidation_threshold:
                # Check if we've already consolidated these tasks
                if last_consolidation:
                    last_consolidation_time = datetime.fromisoformat(last_consolidation)
                    recent_tasks = [
                        t for t in completed_tasks 
                        if datetime.fromisoformat(t["timestamp"]) > last_consolidation_time
                    ]
                    if len(recent_tasks) < self.memory_consolidation_threshold:
                        return
                else:
                    # No previous consolidation, check if we have enough total tasks
                    if len(completed_tasks) < self.memory_consolidation_threshold:
                        return
                
                # Trigger consolidation
                self.consolidate_long_term_memory()
                
        except Exception as e:
            # Don't let memory errors break the system
            logger.info(f"Warning: Memory consolidation check failed: {e}")
    
    def consolidate_long_term_memory(self):
        """Consolidate recent task experiences into long-term memory."""
        try:
            tracking_file = self.memory_dir / "task_tracking.json"
            
            if not tracking_file.exists():
                return
                
            with open(tracking_file, "r", encoding="utf-8") as f:
                tracking_data = json.load(f)
            
            completed_tasks = tracking_data.get("completed_tasks", [])
            if not completed_tasks:
                return
            
            # Generate insights from recent tasks
            insights = self._generate_insights_from_tasks(completed_tasks[-10:])  # Last 10 tasks
            
            # Update long-term memory
            self._update_long_term_memory(insights, completed_tasks[-10:])
            
            # Mark consolidation as done
            tracking_data["last_consolidation"] = datetime.now().isoformat()
            with open(tracking_file, "w", encoding="utf-8") as f:
                json.dump(tracking_data, f, indent=2)
                
            logger.info(f"✓ Memory consolidation completed. Processed {len(completed_tasks[-10:])} recent tasks.")
            
        except Exception as e:
            logger.info(f"Warning: Memory consolidation failed: {e}")
    
    def _generate_insights_from_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insights from a set of completed tasks using the LLM if available."""
        if not tasks:
            return {}
        
        successful_tasks = [t for t in tasks if t.get("success", False)]
        failed_tasks = [t for t in tasks if not t.get("success", True)]
        
        # Tool usage analysis
        tool_usage = {}
        for task in tasks:
            for tool in task.get("tools_used", []):
                tool_usage[tool] = tool_usage.get(tool, 0) + 1
        most_used_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        success_rate = len(successful_tasks) / len(tasks) if tasks else 0
        
        # LLM-Powered Semantic Patterns
        semantic_patterns = []
        if self.llm_client and hasattr(self.llm_client, "chat"):
            try:
                task_summaries = []
                for i, t in enumerate(tasks):
                    status = "SUCCESS" if t.get("success") else "FAILED"
                    goal = t.get("goal", "")
                    ans = t.get("result", "")[:300]
                    task_summaries.append(f"Task {i+1} ({status}): {goal}\nResult: {ans}\n")
                
                workspace_path = str(self.workspace_root)
                system_prompt = (
                    "You are the memory consolidation unit of an AI agent. "
                    "Review the following recent tasks and extract 3 brief, highly semantic rules, facts, or lessons learned "
                    "that will help the agent succeed in the future. "
                    "Focus on persistent facts like 'The database is at port 5432' or 'User prefers Python'. "
                    "Do NOT output generic advice. Output exactly 3 bullet points.\n\n"
                    f"IMPORTANT CONTEXT: The agent's workspace root is: {workspace_path}\n"
                    "All workspace files (MEMORY.md, AGENTS.md, USERINFO.md, etc.) are inside this workspace folder. "
                    "When referencing file paths, use paths relative to the workspace root (e.g., just 'MEMORY.md' not a full absolute path). "
                    "Do NOT hallucinate file paths."
                )
                
                response = self.llm_client.chat(
                    messages=[{"role": "user", "content": "\n".join(task_summaries)}],
                    system=system_prompt
                )
                
                if response:
                    lines = [line.strip().lstrip('-').lstrip('*').strip() for line in response.split('\n') if line.strip()]
                    semantic_patterns = [line for line in lines if line and len(line) > 5][:3]
                    
                    # Post-process: generically strip absolute paths back to relative
                    
                    fixed = []
                    for pattern in semantic_patterns:
                        # Replace full workspace paths with relative
                        pattern = re.sub(
                            re.escape(str(self.workspace_root)).replace("\\\\", r"[/\\]") + r"[/\\]?",
                            "", pattern
                        )
                        # Replace project root paths (e.g. <REPO_ROOT>\MEMORY.md -> MEMORY.md)
                        pattern = re.sub(
                            re.escape(str(self.workspace_root.parent)).replace("\\\\", r"[/\\]") + r"[/\\]?",
                            "", pattern
                        )
                        # Clean up any leftover backslash-only fragments
                        pattern = pattern.replace("``", "`").strip()
                        fixed.append(pattern)
                    semantic_patterns = fixed


            except Exception as e:
                logger.info(f"Warning: LLM memory consolidation failed: {e}")
                
        # Fallback to old string-matching logic if LLM fails or is missing
        if not semantic_patterns:
            semantic_patterns.extend(self._extract_patterns(successful_tasks))
            semantic_patterns.extend(self._extract_patterns(failed_tasks))
        
        return {
            "period": {
                "start": min(t.get("timestamp", "") for t in tasks if t.get("timestamp")),
                "end": max(t.get("timestamp", "") for t in tasks if t.get("timestamp")),
                "task_count": len(tasks)
            },
            "success_rate": success_rate,
            "most_used_tools": most_used_tools,
            "success_patterns": semantic_patterns,
            "failure_patterns": [],
            "avg_duration": sum(t.get("duration", 0) for t in tasks) / len(tasks) if tasks else 0
        }
    
    def _extract_patterns(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """Extract common patterns from task goals or descriptions."""
        patterns = []
        
        # Simple keyword extraction from goals
        goals = [t.get("goal", "").lower() for t in tasks if t.get("goal")]
        
        # Common action verbs
        action_verbs = ["create", "write", "read", "analyze", "search", "find", "build", "make", "fix", "update"]
        found_verbs = []
        for goal in goals:
            for verb in action_verbs:
                if verb in goal:
                    found_verbs.append(verb)
        
        if found_verbs:
            from collections import Counter
            verb_counts = Counter(found_verbs)
            top_verbs = [verb for verb, count in verb_counts.most_common(3)]
            patterns.append(f"Common actions: {', '.join(top_verbs)}")
        
        # Object/noun patterns (simplified)
        nouns = ["file", "directory", "web", "api", "data", "code", "script", "config", "system", "network"]
        found_nouns = []
        for goal in goals:
            for noun in nouns:
                if noun in goal:
                    found_nouns.append(noun)
        
        if found_nouns:
            from collections import Counter
            noun_counts = Counter(found_nouns)
            top_nouns = [noun for noun, count in noun_counts.most_common(3)]
            patterns.append(f"Common objects: {', '.join(top_nouns)}")
        
        return patterns
    
    def _update_long_term_memory(self, insights: Dict[str, Any], recent_tasks: List[Dict[str, Any]]):
        """Update the MEMORY.md file with new insights and experiences."""
        # Read existing long-term memory
        existing_content = ""
        if self.long_term_memory_file.exists():
            with open(self.long_term_memory_file, "r", encoding="utf-8") as f:
                existing_content = f.read()
        
        # Generate new content section
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_section = f"\n## ▪ SAVE — Memory Consolidation - {timestamp}\n\n"
        
        # Add insights
        if insights:
            new_section += f"**Period:** {insights.get('period', {}).get('start', 'Unknown')} to {insights.get('period', {}).get('end', 'Unknown')}\n"
            new_section += f"**Tasks Processed:** {insights.get('period', {}).get('task_count', 0)}\n"
            new_section += f"**Success Rate:** {insights.get('success_rate', 0):.1%}\n"
            new_section += f"**Average Duration:** {insights.get('avg_duration', 0):.2f}s\n\n"
            
            if insights.get('most_used_tools'):
                new_section += f"**Most Used Tools:** {', '.join([tool for tool, count in insights['most_used_tools']])}\n\n"
            
            if insights.get('success_patterns'):
                new_section += f"**Success Patterns:** {'; '.join(insights['success_patterns'])}\n\n"
            
            if insights.get('failure_patterns'):
                new_section += f"**Failure Patterns:** {'; '.join(insights['failure_patterns'])}\n\n"
        
        # Add notable recent tasks
        new_section += "**Notable Recent Tasks:**\n"
        for i, task in enumerate(recent_tasks[-5:], 1):  # Last 5 tasks
            status = "✓" if task.get("success") else "✗"
            goal = task.get("goal", "Unknown goal")[:100]
            new_section += f"{i}. {status} {goal}...\n"
        
        new_section += "\n---\n"
        
        # Combine with existing content (keep recent content at top)
        if existing_content:
            # Extract header and footer if they exist
            lines = existing_content.split('\n')
            header_lines = []
            content_start = 0
            
            # Look for typical header patterns
            for i, line in enumerate(lines):
                if line.startswith('# ') or line.startswith('## ') or i > 10:  # Reasonable limit
                    content_start = i
                    break
                header_lines.append(line)
            
            # Reconstruct
            if header_lines:
                updated_content = '\n'.join(header_lines) + '\n' + new_section + '\n'.join(lines[content_start:])
            else:
                updated_content = new_section + existing_content
        else:
            # Create new MEMORY.md with standard header
            updated_content = f"""# AgenticOs Long-Term Memory

Curated knowledge, insights, and learned patterns from agent experiences.

*This file is automatically updated through experience consolidation.*
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

{new_section}
"""
        
        # Write back to file
        with open(self.long_term_memory_file, "w", encoding="utf-8") as f:
            f.write(updated_content)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system."""
        stats = {
            "daily_files": 0,
            "long_term_memory_exists": self.long_term_memory_file.exists(),
            "long_term_memory_size": 0,
            "total_logged_events": 0
        }
        
        # Count daily memory files
        if self.memory_dir.exists():
            daily_files = list(self.memory_dir.glob("memory-*.md"))
            stats["daily_files"] = len(daily_files)
            
            # Count events in daily files (rough estimate)
            for daily_file in daily_files:
                try:
                    with open(daily_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Count sections (lines starting with ## [timestamp])
                        events = len(re.findall(r'^## \[', content, re.MULTILINE))
                        stats["total_logged_events"] += events
                except Exception:
                    pass  # Skip unreadable files
        
        # Get long-term memory size
        if self.long_term_memory_file.exists():
            stats["long_term_memory_size"] = self.long_term_memory_file.stat().st_size
        
        return stats
    
    def cleanup_old_memories(self, days_to_keep: int = 30):
        """Clean up memory files older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        if not self.memory_dir.exists():
            return 0
        
        cleaned_count = 0
        for memory_file in self.memory_dir.glob("memory-*.md"):
            try:
                # Extract date from filename
                date_str = memory_file.stem.replace("memory-", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    memory_file.unlink()
                    cleaned_count += 1
            except Exception:
                # Skip files that don't match expected format
                continue
        
        return cleaned_count


# Global memory manager instance (will be initialized in runtime)
_memory_manager: Optional[MemoryManager] = None


def initialize_memory_manager(workspace_root: str, llm_client: Optional[Any] = None, cfg: Optional[Dict] = None) -> MemoryManager:
    """Initialize the global memory manager."""
    global _memory_manager
    _memory_manager = MemoryManager(workspace_root, llm_client, cfg)
    return _memory_manager


def get_memory_manager() -> Optional[MemoryManager]:
    """Get the global memory manager instance."""
    return _memory_manager


def log_task_completion(goal: str, final_answer: str, tools_used: List[str], 
                       success: bool, duration: float, metadata: Optional[Dict] = None):
    """Convenience function to log task completion."""
    if _memory_manager:
        _memory_manager.log_task_completion(goal, final_answer, tools_used, success, duration, metadata)


def log_daily_event(event_type: str, description: str, metadata: Optional[Dict] = None):
    """Convenience function to log daily events."""
    if _memory_manager:
        _memory_manager.log_daily_event(event_type, description, metadata)


def get_memory_stats() -> Dict[str, Any]:
    """Get memory system statistics."""
    if _memory_manager:
        return _memory_manager.get_memory_stats()
    return {}


def consolidate_memory():
    """Trigger manual memory consolidation."""
    if _memory_manager:
        _memory_manager.consolidate_long_term_memory()


def cleanup_old_memories(days_to_keep: int = 30) -> int:
    """Clean up old memory files."""
    if _memory_manager:
        return _memory_manager.cleanup_old_memories(days_to_keep)
    return 0