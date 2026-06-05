# Codebase Concerns

**Analysis Date:** 2026-06-05

## Tech Debt

**Duplicate Config Parsing:**
- Issue: `main.py` manually opens and parses `config.yaml` to extract the cache root path before the rest of the runtime is imported.
- Files: `main.py` (lines 30-54) and `core/runtime_config.py`.
- Why: Done to establish bytecode (`pycache`), pytest, and ruff cache environment variables early in the booting phase before any Python packages are loaded.
- Impact: Code duplication and minor maintenance overhead if the YAML structure of cache configuration changes.
- Fix approach: Centralize early config bootstrapping into a lightweight helper module in `core/` that can be imported by both `main.py` and `runtime_config.py`.

**Monolithic Runtime Module:**
- Issue: `core/runtime.py` contains the entire thought-action-observation loop and is extremely large (over 100KB, ~3000 lines).
- Files: `core/runtime.py`.
- Why: Framework evolved incrementally, accumulating retry handlers, tool dispatches, and human-in-the-loop (HITM) CLI features.
- Impact: Increased cognitive load for development; higher risk of side effects when editing loop logic.
- Fix approach: Refactor the monolithic runner class by extracting sub-modules (e.g., `core/runtime/hitm.py` for user prompts, `core/runtime/loop.py` for the core engine loop).

## Security Considerations

**Regex-Based Command Blacklist:**
- Issue: Command validation and blocking rely on regex patterns to intercept dangerous execution arguments.
- Files: `core/guardrails.py`.
- Risk: Potential bypasses via shell encoding, custom environment expansion, or nested command executions.
- Current mitigation: Static regex blocks for patterns like `rm -rf`, `format`, or `net user`.
- Recommendations: Implement a AST-based shell parser or structural command token analyzer instead of raw regex matching.

**Dynamic C# Code Compilation:**
- Issue: Native audio volume controls on Windows dynamically compile C# code via PowerShell.
- Files: `core/platform/windows_audio.py` (or system audio controllers in `tools/system_tools.py`).
- Risk: Windows execution policies (`ExecutionPolicy Bypass`) can be locked down on corporate-managed machines, causing audio tools to crash.
- Current mitigation: Executes PowerShell with bypass flags.
- Recommendations: Provide pre-compiled fallbacks or utilize python-native ctypes to call Windows COM APIs directly.

## Performance Bottlenecks

**Serial LLM Request Latency:**
- Problem: Model queries and tool calls run sequentially in the main thread of the loop.
- Files: `core/runtime.py`.
- Measurement: Loop iterations take seconds to complete, blocking task progress.
- Cause: Thread blocking during LLM inference calls or remote API request roundtrips.
- Improvement path: Leverage async-await patterns for model completions and parallel tool queries where appropriate.

## Fragile Areas

**YAML Configuration Schema Rigidity:**
- Files: `config/`, `core/config_validator.py`.
- Why fragile: Config schema validator causes the engine to fail-fast and abort boot if any user configuration keys are missing or malformed.
- Common failures: Typos in `config.yaml` prevent the agent from starting entirely.
- Safe modification: Relax the validation parameters to log warnings and apply default schema values rather than aborting boot immediately.

**macOS/AppleScript Accessibility Dependability:**
- Files: `core/platform/macos_window.py` (or system window accessibility controllers).
- Why fragile: AppleScript requires explicit system Accessibility authorization from the host operating system.
- Common failures: Silent command failures or UI timeouts if AppleScript execution permission is revoked.
- Safe modification: Wrap Accessibility calls with safety timeout limits and offer lightweight process-level enumeration fallbacks.

## Scaling Limits

**Context Window Exhaustion:**
- System: LLM Context Budget.
- Limit: Standard model token constraints (8k to 128k depending on model selection).
- Symptoms at limit: Model starts forgetting early tasks or errors out with token limits.
- Scaling path: Implement active context compaction, sliding message history windows, and database-archived long-term memory retrieval.

## Test Coverage Gaps

**Interactive UI / Typewriter Simulation:**
- What's not tested: Real terminal typewriter delay rendering across multiple terminal sizes/emulators.
- Risk: Formatting anomalies or terminal typewriter freezing.
- Priority: Medium.
- Difficulty to test: Requires mocking system standard stdout streams and terminal resize actions.

---

*Concerns audit: 2026-06-05*
*Update as issues are fixed or new ones discovered*
