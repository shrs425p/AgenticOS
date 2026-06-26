"""Tests for FallbackRouter and TokenBudgetChecker (Plan 02-03)."""

import pytest
from unittest.mock import MagicMock, patch

from kernel.models import FallbackRouter, TokenBudgetChecker, build_fallback_router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(name="primary", model="model-x", provider="test", response="ok"):
    """Return a mock client that returns *response* from .chat()."""
    client = MagicMock()
    client.model = model
    client.provider = provider
    client.chat.return_value = response
    return client


def _make_failing_client(error_msg: str, provider="bad"):
    """Return a mock client whose .chat() raises RuntimeError with *error_msg*."""
    client = MagicMock()
    client.model = "bad-model"
    client.provider = provider
    client.chat.side_effect = RuntimeError(error_msg)
    return client


# ---------------------------------------------------------------------------
# FallbackRouter spec
# ---------------------------------------------------------------------------

class TestFallbackRouter:

    def test_fallback_router_primary_success(self):
        """Primary succeeds — fallback must not be called."""
        primary = _make_client(response="hello from primary")
        fallback = _make_client(provider="fallback")

        router = FallbackRouter(primary, [fallback], cfg={})
        result = router.chat([{"role": "user", "content": "hi"}])

        assert result == "hello from primary"
        fallback.chat.assert_not_called()

    def test_fallback_router_context_exceeded_fallback(self):
        """Primary raises 'context length exceeded', router falls back to secondary."""
        primary = _make_failing_client("context length exceeded")
        fallback = _make_client(response="fallback response", provider="fallback")

        router = FallbackRouter(primary, [fallback], cfg={})
        result = router.chat([{"role": "user", "content": "big message"}])

        assert result == "fallback response"
        fallback.chat.assert_called_once()

    def test_fallback_router_rate_limit_fallback(self):
        """Primary raises 'rate limit 429', router sleeps then falls back."""
        primary = _make_failing_client("rate limit 429 exceeded")
        fallback = _make_client(response="fallback ok", provider="fallback")

        cfg = {"performance": {"fallback_throttle_seconds": 0}}  # 0 so test doesn't actually sleep

        with patch("time.sleep") as mock_sleep:
            router = FallbackRouter(primary, [fallback], cfg=cfg)
            result = router.chat([{"role": "user", "content": "hi"}])

        assert result == "fallback ok"
        mock_sleep.assert_called_once_with(0)

    def test_fallback_router_auth_error_skip(self):
        """Primary raises '401 unauthorized', router skips to next immediately (no sleep)."""
        primary = _make_failing_client("401 unauthorized")
        fallback = _make_client(response="auth fallback", provider="fallback")

        with patch("time.sleep") as mock_sleep:
            router = FallbackRouter(primary, [fallback], cfg={})
            result = router.chat([{"role": "user", "content": "hi"}])

        assert result == "auth fallback"
        mock_sleep.assert_not_called()

    def test_fallback_router_all_fail(self):
        """All clients fail — RuntimeError is raised."""
        primary = _make_failing_client("context length exceeded", provider="a")
        fb1 = _make_failing_client("context length exceeded", provider="b")
        fb2 = _make_failing_client("context length exceeded", provider="c")

        router = FallbackRouter(primary, [fb1, fb2], cfg={})
        with pytest.raises(RuntimeError, match="All clients exhausted"):
            router.chat([{"role": "user", "content": "hi"}])

    def test_fallback_router_model_property(self):
        """router.model returns primary's model name."""
        primary = _make_client(model="gpt-4-turbo", provider="openai")
        router = FallbackRouter(primary, [], cfg={})
        assert router.model == "gpt-4-turbo"

    def test_fallback_router_provider_property(self):
        """router.provider returns primary's provider name."""
        primary = _make_client(provider="openai")
        router = FallbackRouter(primary, [], cfg={})
        assert router.provider == "openai"

    def test_fallback_router_unexpected_error_reraises(self):
        """Primary raises a ValueError (not context/rate/auth) — it is re-raised immediately."""
        primary = MagicMock()
        primary.model = "some-model"
        primary.provider = "test"
        primary.chat.side_effect = ValueError("something completely unexpected")

        fallback = _make_client(response="should not reach here", provider="fallback")

        router = FallbackRouter(primary, [fallback], cfg={})
        with pytest.raises(ValueError, match="something completely unexpected"):
            router.chat([{"role": "user", "content": "hi"}])

        # The fallback must not have been called
        fallback.chat.assert_not_called()


# ---------------------------------------------------------------------------
# TokenBudgetChecker spec
# ---------------------------------------------------------------------------

class TestTokenBudgetChecker:

    def test_token_budget_checker_estimate(self):
        """estimate_tokens('hello world') returns > 0."""
        checker = TokenBudgetChecker(cfg={})
        result = checker.estimate_tokens("hello world")
        assert result > 0

    def test_token_budget_checker_estimate_empty(self):
        """estimate_tokens with empty string returns minimum 1."""
        checker = TokenBudgetChecker(cfg={})
        assert checker.estimate_tokens("") == 1
        assert checker.estimate_tokens(None) == 1

    def test_token_budget_checker_messages(self):
        """Estimate a list of messages returns a positive int."""
        checker = TokenBudgetChecker(cfg={})
        messages = [
            {"role": "user", "content": "Hello there, how are you doing today?"},
            {"role": "assistant", "content": "I am doing well, thank you for asking!"},
        ]
        total = checker.estimate_messages_tokens(messages, system="You are a helpful assistant.")
        assert total > 0

    def test_token_budget_checker_over_limit(self):
        """Large message count with limit=100 → over_limit=True and warning contains 'EXCEEDED'."""
        checker = TokenBudgetChecker(cfg={})
        # ~500 chars of content → ~125 tokens >> 100 limit
        messages = [{"role": "user", "content": "x" * 500}]
        result = checker.check(messages, model_max_tokens=100)
        assert result["over_limit"] is True
        assert "EXCEEDED" in result["warning"]

    def test_token_budget_checker_warning_threshold(self):
        """Message at ~90% of limit triggers a WARNING (not EXCEEDED)."""
        checker = TokenBudgetChecker(cfg={"performance": {"token_warn_threshold": 0.85}})
        # 360 chars → 90 tokens; limit=100 → ratio=0.90 which is >= 0.85 but < 1.0
        messages = [{"role": "user", "content": "a" * 360}]
        result = checker.check(messages, model_max_tokens=100)
        assert result["over_limit"] is False
        assert result["warning"] is not None
        assert "WARNING" in result["warning"]

    def test_token_budget_checker_under_threshold(self):
        """Tiny message well below threshold → warning is None."""
        checker = TokenBudgetChecker(cfg={})
        messages = [{"role": "user", "content": "hi"}]
        result = checker.check(messages, model_max_tokens=10000)
        assert result["warning"] is None
        assert result["over_limit"] is False

    def test_token_budget_checker_result_keys(self):
        """check() returns all required keys."""
        checker = TokenBudgetChecker(cfg={})
        result = checker.check([], system="test")
        assert set(result.keys()) == {"estimated_tokens", "limit", "usage_ratio", "warning", "over_limit"}

    def test_token_budget_checker_default_limit(self):
        """Default limit is 32000 when no override is provided."""
        checker = TokenBudgetChecker(cfg={})
        result = checker.check([])
        assert result["limit"] == 32000


# ---------------------------------------------------------------------------
# build_fallback_router spec
# ---------------------------------------------------------------------------

class TestBuildFallbackRouter:

    def test_build_fallback_router_no_fallbacks(self):
        """cfg with no fallback_clients returns primary unchanged."""
        primary = _make_client()
        cfg = {"performance": {}}  # no fallback_clients key
        result = build_fallback_router(cfg, primary)
        assert result is primary

    def test_build_fallback_router_empty_list(self):
        """cfg with empty fallback_clients list returns primary unchanged."""
        primary = _make_client()
        cfg = {"performance": {"fallback_clients": []}}
        result = build_fallback_router(cfg, primary)
        assert result is primary

    def test_build_fallback_router_unknown_provider_returns_primary(self):
        """Unknown provider names are silently skipped; if all fail, returns primary."""
        primary = _make_client()
        cfg = {"performance": {"fallback_clients": ["nonexistent_provider_xyz"]}}
        result = build_fallback_router(cfg, primary)
        assert result is primary

    def test_build_fallback_router_known_provider_returns_router(self):
        """If a known provider builds successfully, returns a FallbackRouter."""
        primary = _make_client()
        mock_fallback_client = _make_client(provider="ollama")

        cfg = {"performance": {"fallback_clients": ["ollama"]}}

        with patch("kernel.models.OllamaClient", return_value=mock_fallback_client):
            result = build_fallback_router(cfg, primary)

        assert isinstance(result, FallbackRouter)
        assert result.primary is primary
        assert mock_fallback_client in result.fallbacks
