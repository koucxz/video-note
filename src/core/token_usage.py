"""Daily token budget shared by every LLM / VLM call.

VideoNote and SignalDock run on the same box and spend from the same provider
account, so the limit is counted from real provider usage (``usage.total_tokens``)
instead of an estimate, and it resets by calendar day.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DAILY_TOKEN_LIMIT = 3_000_000


class TokenBudgetExceeded(RuntimeError):
    """Raised when today's token budget is already spent."""


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _env_limit(default: int = DEFAULT_DAILY_TOKEN_LIMIT) -> int:
    raw = os.getenv("DAILY_TOKEN_LIMIT", "")
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class TokenBudget:
    """Thin wrapper over the checkpoint's ``token_usage`` table."""

    def __init__(self, store: Any, limit: Optional[int] = None):
        self._store = store
        self._limit = max(1, int(limit if limit is not None else _env_limit()))

    @property
    def limit(self) -> int:
        return self._limit

    def set_limit(self, value: int) -> int:
        self._limit = max(1, int(value))
        return self._limit

    def used(self, day: Optional[str] = None) -> int:
        try:
            return int(self._store.get_token_usage(day).get("tokens", 0))
        except Exception as exc:  # a broken counter must not break note generation
            logger.warning("Failed to read token usage: %s", exc)
            return 0

    def calls(self, day: Optional[str] = None) -> int:
        try:
            return int(self._store.get_token_usage(day).get("calls", 0))
        except Exception:
            return 0

    def remaining(self) -> int:
        return max(0, self._limit - self.used())

    def ensure(self, estimate: int = 0) -> None:
        used = self.used()
        if used >= self._limit:
            raise TokenBudgetExceeded(
                f"今日 AI token 用量已达上限（{self._limit:,}），明天自动恢复；"
                "需要继续处理可在设置里调大每日上限")
        if estimate > 0 and estimate > max(0, self._limit - used):
            raise TokenBudgetExceeded(
                f"今日 AI token 只剩 {max(0, self._limit - used):,}，不够本次预计的 {estimate:,}；"
                "明天自动恢复或在设置里调大每日上限")

    def record(self, tokens: int, estimate: int = 0) -> int:
        amount = int(tokens or 0)
        if amount <= 0:
            amount = int(estimate or 0)
        if amount <= 0:
            return self.used()
        try:
            return int(self._store.add_token_usage(amount))
        except Exception as exc:
            logger.warning("Failed to record token usage: %s", exc)
            return self.used()

    def snapshot(self, history_days: int = 7) -> Dict[str, Any]:
        used = self.used()
        history: List[Dict[str, Any]] = []
        try:
            history = self._store.get_token_usage_history(history_days)
        except Exception:
            history = []
        return {
            "day": _today(),
            "tokens": used,
            "limit": self._limit,
            "remaining": max(0, self._limit - used),
            "calls": self.calls(),
            "history": history,
        }


_budget: Optional[TokenBudget] = None


def configure(store: Any, limit: Optional[int] = None) -> TokenBudget:
    """Bind the process-wide budget to the engine's checkpoint and limit."""
    global _budget
    _budget = TokenBudget(store, limit)
    logger.info("Daily token limit: %s", f"{_budget.limit:,}")
    return _budget


def current() -> Optional[TokenBudget]:
    return _budget


def ensure_budget(estimate: int = 0) -> None:
    if _budget is not None:
        _budget.ensure(estimate)


def record_tokens(tokens: int, estimate: int = 0) -> int:
    if _budget is None:
        return 0
    return _budget.record(tokens, estimate)


def usage_snapshot(history_days: int = 7) -> Dict[str, Any]:
    if _budget is None:
        return {"day": _today(), "tokens": 0, "limit": _env_limit(),
                "remaining": _env_limit(), "calls": 0, "history": []}
    return _budget.snapshot(history_days)


def set_limit(value: int) -> int:
    if _budget is None:
        return _env_limit(value)
    return _budget.set_limit(value)
