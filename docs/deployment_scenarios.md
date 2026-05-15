# AgenticOS: Deployment Scenarios & Recipes

AgenticOS is a versatile framework that can be configured for a wide variety of operational roles. This document provides "Recipes" for the three most common deployment scenarios: The Isolated Researcher, The Enterprise Automator, and The High-Volume Data Analyst.

---

## [SECURE] Scenario A: The Isolated Researcher (Local-Only)

**Goal**: Maximum privacy and 0% data leakage. Suitable for analyzing confidential codebases or sensitive personal data.

### Configuration (`config.yaml`):
```yaml
agent:
  provider: ollama
  model: qwen2.5-coder:7b
security:
  restrict_paths: true
  enable_zone_guard: true
```

### Setup Steps:
1.  **Hardware**: Ensure you have at least 16GB of RAM and 8GB of VRAM.
2.  **Model**: Run `ollama pull qwen2.5-coder:7b`.
3.  **Isolation**: Disconnect your machine from the internet (optional, but provides a true "Air-Gapped" experience).
4.  **Workflow**: Use the agent to refactor local code or audit local system logs.

---

## [LAUNCH] Scenario B: The Enterprise Automator (Hybrid-Cloud)

**Goal**: Maximum reasoning power and speed. Suitable for complex system orchestration, large-scale audits, and technical report writing.

### Configuration (`config.yaml`):
```yaml
agent:
  provider: nvidia
  model: llama-3.1-405b
autonomy:
  autopilot: true
  active_planning: true
```

### Setup Steps:
1.  **Hardware**: Any standard workstation (8GB+ RAM).
2.  **API**: Ensure your `NVIDIA_API_KEY` is set in the `.env` file.
3.  **Guardrails**: Set `require_hitm_outside_workspace: true` to maintain oversight while allowing the agent to move quickly through its plan.
4.  **Workflow**: Use the agent to perform 96-task Crucible audits or generate weekly system health reports automatically.

---

## [DATA] Scenario C: The High-Volume Data Analyst (Web-Focus)

**Goal**: Maximum web intelligence and data extraction. Suitable for competitive research, financial analysis, and monitoring tech trends.

### Configuration (`config.yaml`):
```yaml
agent:
  provider: gemini
  model: gemini-1.5-pro
browser:
  headless: true
  browser_type: chromium
```

### Setup Steps:
1.  **Browser**: Run `playwright install chromium`.
2.  **Context**: Use the `gemini-1.5-pro` provider to leverage its massive 2-million token context window for reading large datasets.
3.  **Persistence**: Enable the `sqlite` memory backend to track long-running web crawls.
4.  **Workflow**: Use the agent to scrape ArXiv, analyze PyPI updates, or monitor cryptocurrency market shifts.

---

## [STATS] Scenario Comparison Table

| Feature | Isolated Researcher | Enterprise Automator | Data Analyst |
| :--- | :--- | :--- | :--- |
| **Privacy** |  Absolute |  API-Gated |  API-Gated |
| **Reasoning** |  Standard (7B-14B) |  Extreme (400B+) |  Extreme (Gemini) |
| **Speed** |  Hardware-Limited |  High (Cloud) |  High (Cloud) |
| **Context Size**|  4K - 16K |  128K |  1M - 2M |
| **Ideal For** | Personal Code | System SRE Tasks | Market Research |

---

## [PROVEN] Selecting Your Path

You can switch between these scenarios instantly by modifying your `config.yaml`. AgenticOS is designed to be "Mode-Agnostic"-your tools, plugins, and workspace artifacts remain consistent regardless of which deployment path you choose.

---

*Last Updated: 2026-05-14*
*Status: Scenario Verified*
