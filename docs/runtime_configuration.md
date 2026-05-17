# AgenticOS: Layered Runtime Configuration Guide

AgenticOS uses a high-performance, layered configuration system. Instead of a single monolithic file, configuration is split across specialized YAML files in the `config/` directory. These files are merged at runtime, allowing for clean separation between system logic, security policy, and environment-specific paths.

---

## [ARCH] The `config/` Directory Structure

The system loads and merges these files in the following order:

| File | Purpose | Key Responsibilities |
| :--- | :--- | :--- |
| **`runtime.yaml`** | Environment Setup | Base paths, magic numbers, iteration limits. |
| **`policy.yaml`** | Security & Compliance | Secret redaction, destructive tool lists, PathGuard regex. |
| **`endpoints.yaml`**| External Services | API URLs, search endpoints, service presets. |
| **`providers.yaml`**| AI Model Config | Ollama, Nvidia, Gemini, and OpenAI settings. |
| **`prompts.yaml`**  | Intelligence | System prompts, CoV templates, and agent "nudges." |
| **`storage.yaml`**  | Persistence | SQLite paths, memory summarization thresholds. |
| **`tools.yaml`**    | Capability Toggles | Enabling/disabling specific tool categories. |
| **`url_presets.yaml`**| URL Templates | Predefined URLs and shortcuts. |

---

## [SYNC] Core Configuration Files

### 1. `runtime.yaml` (The "Nervous System")
Controls the basic heuristics of the agent execution loop.
- **`workspace`**: The primary root for agent operations (defaults to `./workspace`).
- **`iteration_warning_threshold`**: Number of steps before warning the user.
- **`max_observation_chars`**: Truncates massive tool outputs (default: 12,000) to save context.

### 2. `policy.yaml` (The "Shield")
Defines the security posture of the OS.
- **`redaction_patterns`**: Regex list for masking keys and tokens in all logs.
- **`destructive_tools`**: List of tools that *always* require user confirmation (e.g., `delete_dir`).
- **`path_keys`**: List of argument names that `PathGuard` should treat as file paths.

### 3. `endpoints.yaml` (The "Connector")
Centralizes all hardcoded URLs to ensure portability.
- **`search_providers`**: URLs for DuckDuckGo, Bing, and Google.
- **`system_services`**: Endpoints for IP check (`ipify`), Spotify, and WhatsApp Web.

---

## [SECURE] Zero-Hardcoding Policy

Developers must **never** hardcode absolute paths (e.g., `C:\`) or URLs in the Python source code. All environment-specific values must be fetched via the config system:

```python
# GOOD: Configuration-driven
url = self.cfg.get("endpoints", {}).get("google_search")

# BAD: Hardcoded (Blocked by CI)
url = "https://www.google.com/search?q="
```

---

## [STATS] Hot-Reloading

AgenticOS supports **Hot-Reloading**. If you modify any YAML file in the `config/` directory while the agent is running, the changes are detected and applied instantly to the next iteration without requiring a restart.

---

## [LOGIC] Configuration Merging Logic

When a key is requested (e.g., `self.cfg.get("security")`), the `ConfigLoader`:
1. Checks the merged global dictionary.
2. If multiple files define the same top-level key (rare), the last loaded file (alphabetical) wins.
3. For nested dictionaries (like `rules`), the system performs a deep merge.

---

*Last Updated: 2026-05-15*
*Status: Architecture Hardened*
