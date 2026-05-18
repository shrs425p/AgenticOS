"""Cost & token budget tracking for AgenticOs.

Records prompt/completion token counts per API call and computes USD cost
using per-provider pricing tables defined in ``config/providers.yaml``
(under a ``pricing:`` key).  Persists usage to ``data/usage.sqlite``.

Pricing tables example (providers.yaml)::

    pricing:
      nvidia:
        prompt_per_1k: 0.002
        completion_per_1k: 0.006
      openai:
        prompt_per_1k: 0.0005
        completion_per_1k: 0.0015
      groq:
        prompt_per_1k: 0.0001
        completion_per_1k: 0.0002
      gemini:
        prompt_per_1k: 0.00025
        completion_per_1k: 0.0005
      ollama:
        prompt_per_1k: 0.0
        completion_per_1k: 0.0
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


# Default pricing (USD per 1 000 tokens) used when config is absent.
_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "nvidia": {"prompt_per_1k": 0.002, "completion_per_1k": 0.006},
    "openai": {"prompt_per_1k": 0.0005, "completion_per_1k": 0.0015},
    "groq": {"prompt_per_1k": 0.0001, "completion_per_1k": 0.0002},
    "gemini": {"prompt_per_1k": 0.00025, "completion_per_1k": 0.0005},
    "openrouter": {"prompt_per_1k": 0.001, "completion_per_1k": 0.002},
    "github": {"prompt_per_1k": 0.0, "completion_per_1k": 0.0},
    "deepseek": {"prompt_per_1k": 0.00014, "completion_per_1k": 0.00028},
    "ollama": {"prompt_per_1k": 0.0, "completion_per_1k": 0.0},
}


class CostTracker:
    """Records token usage and computes USD cost per API call.

    Args:
        data_dir: Directory where ``usage.sqlite`` will be stored.
        cfg: Agent configuration dict (for pricing tables and budget).
        session_id: Current session identifier.
    """

    DB_FILE = "usage.sqlite"

    def __init__(
        self,
        data_dir: str,
        cfg: Optional[Dict] = None,
        session_id: str = "",
    ):
        self.cfg = cfg or {}
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        data_path = Path(data_dir).resolve()
        data_path.mkdir(parents=True, exist_ok=True)

        db_path = data_path / self.DB_FILE
        self._conn = sqlite3.connect(str(db_path), timeout=10, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

        budget_cfg = self.cfg.get("budget", {}) or {}
        self.max_usd = float(budget_cfg.get("max_usd_per_session", 0) or 0)
        self._session_cost: float = 0.0

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self):
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              prompt_tokens INTEGER NOT NULL DEFAULT 0,
              completion_tokens INTEGER NOT NULL DEFAULT 0,
              cost_usd REAL NOT NULL DEFAULT 0.0,
              created_at TEXT NOT NULL
            );
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_session ON usage(session_id);"
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Pricing helpers
    # ------------------------------------------------------------------

    def _get_pricing(self, provider: str) -> Dict[str, float]:
        config_pricing = self.cfg.get("pricing", {}) or {}
        if provider in config_pricing:
            return config_pricing[provider]
        return _DEFAULT_PRICING.get(provider, {"prompt_per_1k": 0.0, "completion_per_1k": 0.0})

    def compute_cost(
        self, provider: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """Compute USD cost for a single API call."""
        pricing = self._get_pricing(provider)
        prompt_cost = (prompt_tokens / 1000.0) * pricing.get("prompt_per_1k", 0.0)
        completion_cost = (completion_tokens / 1000.0) * pricing.get("completion_per_1k", 0.0)
        return prompt_cost + completion_cost

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Record a usage event and return the cost for this call in USD."""
        cost = self.compute_cost(provider, prompt_tokens, completion_tokens)
        self._conn.execute(
            """
            INSERT INTO usage(session_id, provider, model, prompt_tokens, completion_tokens, cost_usd, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                self.session_id,
                provider,
                model,
                prompt_tokens,
                completion_tokens,
                cost,
                _now_iso(),
            ),
        )
        self._conn.commit()
        self._session_cost += cost
        logger.debug(
            "CostTracker: %s/%s prompt=%d completion=%d cost=$%.6f session_total=$%.6f",
            provider,
            model,
            prompt_tokens,
            completion_tokens,
            cost,
            self._session_cost,
        )
        return cost

    # ------------------------------------------------------------------
    # Budget enforcement
    # ------------------------------------------------------------------

    def is_over_budget(self) -> bool:
        """Return True if the session cost has exceeded the configured max."""
        if self.max_usd <= 0:
            return False
        return self._session_cost >= self.max_usd

    @property
    def session_cost(self) -> float:
        """Running session cost in USD."""
        return self._session_cost

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_report(self, period: str = "session") -> Dict:
        """Return a usage summary.

        Args:
            period: One of ``"session"`` (current session only), ``"today"``,
                    or ``"all"`` (lifetime).
        """
        filters = []
        params: list = []

        if period == "session":
            filters.append("session_id = ?")
            params.append(self.session_id)
        elif period == "today":
            today = datetime.now().strftime("%Y-%m-%d")
            filters.append("created_at LIKE ?")
            params.append(f"{today}%")

        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        cur = self._conn.execute(
            f"""
            SELECT
              provider,
              SUM(prompt_tokens)     AS prompt_total,
              SUM(completion_tokens) AS completion_total,
              SUM(cost_usd)          AS cost_total,
              COUNT(*)               AS calls
            FROM usage
            {where}
            GROUP BY provider
            ORDER BY cost_total DESC
            """,
            params,
        )
        rows = cur.fetchall()

        summary = {}
        total_cost = 0.0
        total_calls = 0
        for provider, pt, ct, cost, calls in rows:
            summary[provider] = {
                "prompt_tokens": pt,
                "completion_tokens": ct,
                "cost_usd": round(cost, 6),
                "calls": calls,
            }
            total_cost += cost
            total_calls += calls

        return {
            "period": period,
            "session_id": self.session_id,
            "session_cost_usd": round(self._session_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "total_calls": total_calls,
            "budget_usd": self.max_usd,
            "over_budget": self.is_over_budget(),
            "by_provider": summary,
        }

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
