import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class RetryDecision:
    action: str  # "retry", "abandon", "escalate"
    reason: str
    max_retries: int

class RetryClassifier:
    """Classifies tool execution errors into retries, abandonment, or escalation."""
    
    TRANSIENT_KEYWORDS = [
        "timeout", "network", "connection reset", "locked", "temporarily",
        "retry", "503", "429", "etimedout", "econnrefused"
    ]
    
    PERMANENT_KEYWORDS = [
        "permission denied", "not found", "syntax error", "invalid argument",
        "enoent", "eperm", "eacces"
    ]
    
    PERMANENT_EXIT_CODES = {1, 2, 127, 128, 130}

    def classify(self, error_msg: str, exit_code: Optional[int] = None) -> RetryDecision:
        """Analyze exit code and error message to determine the retry action."""
        error_msg_lower = (error_msg or "").lower()
        
        # 1. Permanent exit codes
        if exit_code is not None and exit_code in self.PERMANENT_EXIT_CODES:
            return RetryDecision(
                action="abandon",
                reason=f"Permanent exit code {exit_code} detected",
                max_retries=0
            )
            
        # 2. Permanent keywords
        for kw in self.PERMANENT_KEYWORDS:
            if kw in error_msg_lower:
                return RetryDecision(
                    action="abandon",
                    reason=f"Permanent error keyword '{kw}' found in error message",
                    max_retries=0
                )
                
        # 3. Transient keywords
        for kw in self.TRANSIENT_KEYWORDS:
            if kw in error_msg_lower:
                return RetryDecision(
                    action="retry",
                    reason=f"Transient error keyword '{kw}' found in error message",
                    max_retries=3
                )
                
        # 4. Ambiguous errors (neither transient nor permanent keywords matched)
        return RetryDecision(
            action="retry",  # Retry up to 2 times, then escalate
            reason="Ambiguous error detected, attempting limited retry",
            max_retries=2
        )
