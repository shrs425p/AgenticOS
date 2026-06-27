# Security Policy for AgenticOS

At AgenticOS, we take the security of our users and the systems they inhabit seriously. As an autonomous AI agent framework with system-level capabilities, we recognize our unique responsibility to maintain strict guardrails while enabling powerful automation.

---

## Security Philosophy

AgenticOS is built on a **Zero-Trust Runtime Model**. Our security architecture is designed to fail safely:
1.  **Isolation by Design**: Path-based restrictions (PathGuard) isolate the agent's write-access to the `workspace/` directory by default.
2.  **Human-In-The-Middle (HITM)**: High-risk operations (such as outside-workspace writes in Green Zone) require explicit human approval via the terminal.
3.  **Command Validation**: All shell commands are sanitized and checked against a strict blacklist (no formatting, user management, or system shutdowns).

---

## Supported Versions

We actively provide security updates for the following versions of AgenticOS:

| Version | Supported          | Status             |
| ------- | ------------------ | ------------------ |
| 2.x     | Yes                | Active Development |
| 1.x     | No                 | End of Life (EOL)  |

---

## Reporting a Vulnerability

**Please DO NOT report security vulnerabilities through public GitHub issues or pull requests.**

If you discover a potential security vulnerability in AgenticOS, please report it via the **GitHub Security Advisory** system or contact the lead maintainers privately.

### What to Report:
- Remote Code Execution (RCE) vulnerabilities.
- Path traversal/guardrail bypasses.
- Credential exfiltration via prompt injection.
- Failures in the Secret Redaction Engine.

### Note on "Hallucinations"
Inaccurate responses or "hallucinations" by the underlying LLM are not considered security vulnerabilities unless they result in an actual bypass of the AgenticOS runtime guardrails.

---

## Disclosure and Response Process

When we receive a vulnerability report, we follow a strict Coordinated Vulnerability Disclosure (CVD) process:

1.  **Acknowledgment**: You will receive an initial response within **24-48 hours**.
2.  **Verification**: Our team will attempt to reproduce the issue and assess the severity using CVSS metrics.
3.  **Fixing**: We aim to provide a resolution within **30 days** of verification.
4.  **Disclosure**: We will coordinate with the reporter to release a security advisory and credit the researcher for their contribution.

---

## Security Research Guidelines

We encourage responsible security research. We ask that researchers:
- Do not attempt to access or damage any user data.
- Avoid performing any destructive actions on the host machine.
- Provide a clear Proof-of-Concept (PoC) to help us understand the impact.

---

## Security Documentation Catalog

For implementation details and operator safety practices, review:
- [Security Guardrails Manual](manuals/guard.md)
- [Safety Guide](manuals/safety.md)
- [Privacy & Data Policy](manuals/privacy.md)
- [Documentation Catalog](manuals/CATALOG.md)

Thank you for helping us keep the future of autonomous agents safe and secure!
