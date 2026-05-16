class RateLimitExhausted(Exception):
    """Raised when a model provider rate limit is exhausted after all retries."""
    pass
