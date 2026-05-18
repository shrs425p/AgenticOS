## ⫸ Description
Please include a summary of the changes, the motivation behind them, and link the relevant issue being addressed.

Fixes # (issue)

---

## ⫸ Type of Change
- [ ] **Bug Fix**: Non-breaking change that resolves a bug/issue.
- [ ] **New Feature**: Non-breaking change adding new autonomous tools or core agent functionality.
- [ ] **Breaking Change**: A modification that would break existing compatibility, workflows, or APIs.
- [ ] **Code Refactor**: Code cleanup, optimization, or structured improvements with no functionality changes.
- [ ] **Documentation**: Updates to READMEs, system designs, or technical guides.

---

## ⫸ Autonomous Tool & System Safety Check
- [ ] **Tool Registry Integration**: If new tools were added, they have been properly registered in `core/tool_registry.py`.
- [ ] **Shadow Mode Validation**: Ran `tests/test_all_tools_shadow.py` successfully and verified all tools pass dry-run/shadow checks with zero failures.
- [ ] **Execution Guardrails**: Confirmed that any shell execution or OS command tool has strict validation to prevent malicious payload or command injection.
- [ ] **Cross-Platform Fallbacks**: If utilizing platform-specific features (e.g., Windows CoreAudio/PowerShell or Linux packages), verified correct OS fallback/compatibility checks.

---

## ⫸ Code Hardening & Portability
- [ ] **No Hardcoded Paths**: Dynamic path resolution is used everywhere (no hardcoded absolute directories like `/path/to/AgenticOs`).
- [ ] **Config-Driven Endpoints**: All external URLs or dynamic constants are placed inside centralized configuration YAMLs.
- [ ] **Secrets Redacted**: Audited code, scripts, and logs to ensure no private keys, OpenAI/Ollama keys, or tokens are exposed.
- [ ] **Output Telemetry**: Verified that output outputs/logs are informative but not verbose enough to block or spam core console channels.

---

## ⫸ QA & Verification Checklist
- [ ] **Unit Tests**: Executed `pytest tests/` and confirmed 100% test pass rate.
- [ ] **Coverage Rate**: Ensured test coverage did not decrease (run `pytest --cov`).
- [ ] **Developer Self-Review**: Performed a thorough line-by-line self-audit of all modifications.
- [ ] **Code Comments**: Added clear docstrings and comments for non-obvious helper logic and regex functions.
- [ ] **Linter Approved**: Ran `ruff check .` with zero errors or warnings remaining.
