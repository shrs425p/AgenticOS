# AgenticOS: Privacy & Data Security Policy

AgenticOS is built on a "Privacy-First" architecture. Unlike centralized AI assistants that process all data in the cloud, AgenticOS gives you granular control over where your data is processed and how it is stored. This document details our data handling practices and how to configure the system for maximum privacy.

---

## [SECURE] The Local-First Philosophy

The core design of AgenticOS prioritizes local execution. All system interactions, file reads, and OS-level commands happen natively on your machine. No raw file contents or system logs are ever transmitted to a third party unless you explicitly choose a cloud-based model provider.

### Data Residency:
-   **Conversation History**: Stored in a local SQLite database (`data/memory.sqlite3`).
-   **Audit Logs**: Stored in local JSONL files (`data/logs/`).
-   **Task Artifacts**: Saved exclusively in your local `workspace/` folder.
-   **Model Weights**: If using Ollama, model weights are stored on your local disk and never leave your network.

---

## [SYNC] Cloud vs. Local Processing

AgenticOS allows you to switch between model providers. Your choice of provider determines the "Data Privacy Level" of your session.

### Level 1: Zero-Cloud (Air-Gapped)
-   **Provider**: Ollama.
-   **Behavior**: 100% of the intelligence is local. Your prompts and file data never leave your computer.
-   **Recommendation**: Use this for sensitive codebase refactoring, personal document analysis, and confidential research.

### Level 2: Hybrid (Cloud-Reasoning)
-   **Providers**: Nvidia NIM, Google Gemini, Groq, OpenAI.
-   **Behavior**: Prompts and relevant context (e.g., file snippets) are sent to the provider's API for processing.
-   **Privacy Note**: These providers generally have "Zero Data Retention" policies for API-based traffic (unlike their consumer chat interfaces), but data does leave your machine.

---

## 🔒 Data Minimization & Redaction

Even when using cloud providers, AgenticOS implements "Context Pruning" to minimize the amount of data transmitted.

### 1. Smart Truncation
Instead of sending a whole 50MB log file, the agent is instructed to read only the relevant lines. This reduces both API costs and data exposure.

### 2. Secret Redaction (Experimental)
The system can be configured to scan tool outputs for common patterns (API keys, SSH keys, passwords) and redact them before they are stored in the persistent SQLite memory or sent to a model.

---

## [SECURE] PathGuard & Information Siloing

The **PathGuard** system serves as a privacy barrier. By blocking the agent from accessing directories like `C:\Windows` or `C:\Users\Admin\Documents`, we ensure that the agent cannot "casually" read sensitive files into its context window, even if it is asked to do so by a model.

### Forbidden Paths:
The following paths are blocked by default to prevent accidental data leakage:
-   System registry hives.
-   Browser credential stores (Cookies/Login Data).
-   OS system configuration files.

---

## 📁 Persistent Memory Privacy

The SQLite database (`data/memory.sqlite3`) contains a record of your interactions. To ensure this data remains secure:
1.  **Local Encryption**: We recommend running AgenticOS on an encrypted drive (e.g., BitLocker or FileVault).
2.  **Manual Purge**: You can delete the `data/` folder at any time to "factory reset" the agent's memory.
3.  **Audit Logs**: Audit logs do **not** contain the text of your conversations; they only record "What tool was used" and "When," making them safe for administrative review.

---

## [CONFIG] Privacy Configuration (`config.yaml`)

You can harden your privacy settings using the following keys:

```yaml
agent:
  # Force all reasoning to stay on your machine
  provider: ollama

security:
  # Block the agent from reading anything outside the project
  restrict_paths: true
  
memory:
  # Redact obvious secrets before saving to DB
  redact_secrets: true
```

---

## [TEST] Verification of Privacy

You can audit the agent's network activity to verify that no unauthorized data is being sent:
1.  Run the agent in `autopilot: false` mode.
2.  Use a network monitor (like Wireshark or GlassWire).
3.  Observe that requests are only made to `localhost:11434` (Ollama) or your specifically configured cloud endpoints.

---

## [END] Summary for Enterprise Users
AgenticOS is designed to be **SOC2-Compliant Friendly**. By using the local SQLite backend and an air-gapped Ollama instance, you can satisfy the most stringent data residency requirements while still leveraging the power of autonomous agentic reasoning.

---

*Last Updated: 2026-05-14*
*Status: Privacy Hardened*
