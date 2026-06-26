<!-- generated-by: gsd-doc-writer -->
# Runtime Configuration

AgenticOS loads configuration parameters from environment variables (loaded via `.env`) and a structured `cfg.yaml` file located in the project root.

---

## Environment Variables

The following environment variables can be configured in your `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NVIDIA_API_KEY` | Optional | None | API key required when using the NVIDIA NIM cloud provider |
| `GEMINI_API_KEY` | Optional | None | API key required when using the Google Gemini cloud provider |
| `GROQ_API_KEY` | Optional | None | API key required when using the Groq cloud provider |
| `OPENAI_API_KEY` | Optional | None | API key required when using the OpenAI cloud provider |
| `OPENROUTER_API_KEY` | Optional | None | API key required when using OpenRouter |
| `DEEPSEEK_API_KEY` | Optional | None | API key required when using DeepSeek |
| `GITHUB_TOKEN` | Optional | None | API key/token required when using the GitHub API provider |
| `PYTHONPYCACHEPREFIX` | Optional | `data/cache/pycache` | Directory path where Python compiled bytecodes are stored |
| `PIP_CACHE_DIR` | Optional | `data/cache/pip` | Directory path where pip packages are cached |

---

## Config File Format (`cfg.yaml`)

The primary configuration is defined in `cfg.yaml`. Values in `cfg.yaml` override layered configuration defaults from `cfg/` subdirectories.

Here is a typical `cfg.yaml` example:

```yaml
agent:
  provider: nvidia          # Provider type: ollama, nvidia, gemini, groq, openai, openrouter, deepseek, github
  workspace: workspace      # Base directory for agent commands
  stream: true              # Enable streaming token output responses

cloud:
  nvidia:
    model: openai/gpt-oss-120b # Target model name for cloud provider queries

autonomy:
  autopilot: true           # Autopilot flag (reduces interactive prompt checkpoints)
  startup_provider_prompt: false # Prompt for provider selection at start
  startup_model_prompt: false    # Prompt for model selection at start
  power_mode: true          # Enable high-performance processing mode

log_level: INFO             # Console logging level (DEBUG, INFO, WARNING, ERROR)
```

---

## Required vs Optional Settings

- **Provider**: The `agent.provider` setting in `cfg.yaml` must match one of the supported model providers.
- **Provider Keys**: If `agent.provider` is set to any value other than `ollama`, the corresponding API key (e.g. `NVIDIA_API_KEY`, `GEMINI_API_KEY`) must be exported in your environment or defined in the `.env` file. The health check (`python main.py --health`) will raise a validation failure if key configurations are missing.

---

## Configuration Defaults

- **Workspace Path**: The default workspace is set to `workspace/` relative to the project root.
- **Cache Directories**: If no cache directory is specified, a unified folder is created under `data/cache` for python pycache, ruff, pip, and pytest.
- **Max Workers / Concurrency**: The default worker count is scaled based on the resource profiler metrics (low-resource environments limit workers to 2; high-resource ones scale to the CPU kernel count).
