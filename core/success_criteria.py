import re
from typing import List

class SuccessCriteria:
    """Parses success criteria from goals/prompts and verifies if they have been addressed before termination."""

    def __init__(self, goal: str):
        self.goal = goal
        self.criteria = self.parse_criteria(goal)

    def parse_criteria(self, text: str) -> List[str]:
        """Extract success criteria phrases from goal text."""
        criteria = []
        if not text:
            return criteria
        
        # Matches the prefix verbs, optional "that ", and captures the target clause.
        # Uses positive lookahead to stop at logical separators like "and", "then", other keywords, or punctuation.
        pattern = r"\b(?:verify|make\s+sure|confirm|check|ensure)\s+(?:that\s+)?([^.,;!\n]+?)(?=\s+and\s+|\s+then\s+|\s+ensure\s+|\s+make\s+sure\s+|\s+confirm\s+|\s+check\s+|\s+verify\s+|[.,;!\n]|$)"
        
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            clause = m.group(1).strip()
            if clause.lower().startswith("that "):
                clause = clause[5:].strip()
            if clause and clause not in criteria:
                criteria.append(clause)
        return criteria

    def is_met(self, conversation_history: List[dict]) -> bool:
        """Verify if all criteria are likely met by checking conversation history."""
        if not self.criteria:
            return True
            
        history_text = "\n".join([m.get("content", "") for m in conversation_history if m.get("content")]).lower()
        
        for criterion in self.criteria:
            words = [w.lower() for w in re.split(r"\W+", criterion) if len(w) > 3]
            if not words:
                continue
            if not any(word in history_text for word in words):
                return False
        return True
