# AgenticOS: Model Integration & Provider Guide

AgenticOS is provider-agnostic, supporting a hybrid ecosystem of local "Edge" models (Ollama) and high-performance "Cloud" models (Nvidia, Google, OpenAI). This document explains how to configure providers and how the system handles API resilience.

---

## [ARCH] Supported Providers

AgenticOS natively supports the following providers through the `core/model_clients.py` interface:

### 1. Ollama (Local / Private)
-   **Best for**: Privacy-sensitive tasks, local code editing, and offline work.
-   **Recommended Model**: `qwen2.5-coder:7b` or `llama-3.1:8b`.
-   **Requirement**: `ollama serve` must be running.

### 2. Nvidia NIM (High Performance)
-   **Best for**: Complex reasoning, long-context window tasks, and multi-step planning.
-   **Recommended Model**: `openai/gpt-oss-120b` or `meta/llama-3.1-405b`.
-   **Requirement**: An API key from the Nvidia build platform.

### 3. Google Gemini (Native Multimodal)
-   **Best for**: Image analysis, long context (1M+ tokens), and rapid tool-use.
-   **Requirement**: Google AI Studio API Key.

---

## [SECURE] API Resilience & The 429 Shield

In production, API rate limits are the most common cause of agent failure. AgenticOS v2.0.0 features a custom **Exponential Backoff & Retry** system built directly into the client layer.

### How it Works:
If a provider returns a `429 Too Many Requests` (Rate Limit) error:
1.  **Intercept**: The client catches the error before it reaches the main agent loop.
2.  **Wait**: The system pauses for a calculated duration (starting at 1s).
3.  **Backoff**: If it fails again, the wait time doubles (2s, 4s, 8s...).
4.  **Max Retries**: The system attempts up to 5 retries by default before reporting a failure.

### Configuration (`config.yaml`):
```yaml
agent:
  auto_retry: true
  max_retries: 5
  retry_delay: 2 # Initial delay in seconds
```

---

## [CONFIG] Provider Configuration Details

### Ollama Setup
Ollama is the heart of the local-first philosophy.
```yaml
ollama:
  base_url: http://localhost:11434
  default_model: qwen2.5-coder:7b
  num_ctx: 32768      # Expand context for large files
  num_predict: 8192   # Max generation length
  temperature: 0.7
```

### Nvidia NIM Setup
Leverage world-class models through the OpenAI-compatible NIM interface.
```yaml
cloud:
  nvidia:
    base_url: https://integrate.api.nvidia.com/v1
    model: openai/gpt-oss-120b
    max_tokens: 8192
```

---

##  Dynamic Model Switching & Fallbacks

AgenticOS supports **Self-Healing Fallbacks**. If a primary model fails to generate valid JSON or hits a persistent error, the orchestrator can automatically switch to a fallback model to complete the turn.

### The "Thinking" Model Pattern
For high-complexity tasks, you can configure a separate model for "Mental Simulation" (Chain-of-Verification):
```yaml
heuristics:
  cov_model: "meta/llama-3.1-70b" # Use a smarter model just for planning
```

---

## [DATA] Performance Benchmarks (Tokens/Sec)

| Provider | Model | Latency (First Token) | Throughput |
| :--- | :--- | :--- | :--- |
| **Ollama** | qwen2.5-coder:7b | ~100ms | 45-60 t/s |
| **Nvidia** | gpt-oss-120b | ~400ms | 80-120 t/s |
| **Gemini** | gemini-2.0-flash | ~250ms | 150+ t/s |

---

## [TEST] Token Management & Context Pruning

To keep costs low and performance high, AgenticOS implements several token-saving strategies:

1.  **Observation Truncation**: Tool outputs are capped at `max_observation_chars` (default: 4,000).
2.  **History Trimming**: Only the last 500 messages are kept in active context; older messages are summarized.
3.  **Prompt Optimization**: The system prompt is designed to be concise, with tool definitions injected only when necessary.

---

## [TOOL] Troubleshooting API Issues

### 1. Connection Refused (Ollama)
-   **Cause**: Ollama is not running or is bound to the wrong port.
-   **Fix**: Run `ollama serve` and verify `http://localhost:11434` is accessible in your browser.

### 2. Context Window Exceeded
-   **Cause**: Reading too many large files at once.
-   **Fix**: Increase `num_ctx` in `config.yaml` or use the `read_file` line-range parameters to read smaller chunks.

### 3. Invalid API Key
-   **Cause**: Missing or expired cloud key in `.env`.
-   **Fix**: Check your `.env` file and ensure `NVIDIA_API_KEY` or `GOOGLE_API_KEY` is correct.

---

*Last Updated: 2026-05-13*
*Status: Verified*
