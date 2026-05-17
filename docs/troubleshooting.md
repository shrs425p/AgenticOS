# AgenticOS: Troubleshooting and Diagnostic Guide

AgenticOS is a complex system interacting with multiple APIs and the local operating system. This guide covers common errors, performance issues, and recovery strategies for high-intensity environments.

---

## Common Error Codes

### 1. `Error: 429 Too Many Requests`
-   **Symptom**: The agent pauses and displays a rate-limit warning.
-   **Cause**: You have exceeded your API provider's rate limit (RPM/TPM).
-   **Fix**: AgenticOS has a built-in **Exponential Backoff Shield**. It will automatically retry. If this happens frequently, consider switching to a provider with higher limits or upgrading your plan.

### 2. `'Logger' object has no attribute 'isatty'`
-   **Symptom**: The script crashes immediately after starting.
-   **Cause**: You replaced `sys.stdout` with a custom logger that doesn't implement the full terminal interface.
-   **Fix**: Ensure your `Logger` class in `run_eval.py` has an `isatty()` method and an `encoding` property. (This was fixed in v2.0.0).

### 3. `UnicodeEncodeError: 'charmap' codec can't encode character...`
-   **Symptom**: The agent crashes when printing symbols (e.g., [LAUNCH]) to the Windows console.
-   **Cause**: The Windows CMD/PowerShell encoding is not set to UTF-8.
-   **Fix**: Run `sys.stdout.reconfigure(encoding='utf-8')` at the top of your script, or use the AgenticOS built-in `runtime_ui` which handles this automatically.

---

## Performance Issues

### 1. "My system is lagging when the agent scans the drive."
-   **Cause**: The agent is using a slow Python-based recursive search (e.g., `grep_dir` on `C:\`).
-   **Fix**: Use the `find_large_files` tool. We implemented **Performance Guardrails** that should now block these slow scans and suggest the faster native method.

### 2. "The terminal UI is flickering or slow."
-   **Cause**: Typewriter lag from character-by-character flushing.
-   **Fix**: Ensure `agent.stream` is configured correctly. In v2.0.0, we optimized `typewriter_print` to use block-level output, which removes this lag.

### 3. "Agent is stuck in a loop (repeating the same action)."
-   **Cause**: The model doesn't understand the tool output or thinks the task isn't done.
-   **Fix**: 
    -   Increase `max_iterations` to give it more room.
    -   Enable `think_before_act` to force it to explain its reasoning.
    -   Check if the tool is actually failing silently (check `agent.log`).

---

## Security and Access Denied

### 1. `PermissionError: [WinError 5] Access is denied`
-   **Cause**: The agent is trying to modify a file that is protected or in use by another process.
-   **Fix**:
    -   Ensure the terminal is running with appropriate permissions (though Admin is rarely required).
    -   Check the `PathGuard` settings in `config.yaml` to ensure the path isn't in the **Red Zone**.

### 2. `CRITICAL: Recursive content grep on C:\ is forbidden`
-   **Cause**: You triggered a security guardrail designed to prevent SSD thrashing.
-   **Fix**: This is intended behavior. Narrow your search to a specific folder (e.g., `C:\Users\shrs\Downloads`) or use the `search_files` tool for filename searches.

---

## Model Reasoning Issues

### 1. "The agent is ignoring my instructions."
-   **Cause**: System prompt fatigue or context window saturation.
-   **Fix**: 
    -   Clear the `data/memory.sqlite3` file to start a fresh session.
    -   Use a more powerful model (e.g., `gpt-oss-120b` or `gemini-1.5-pro`) for complex tasks.

### 2. "The agent generates invalid JSON actions."
-   **Cause**: Smaller models (like 7B or 8B) can sometimes struggle with strict JSON formatting.
-   **Fix**: Enable `self_healing: true` in `config.yaml`. The system will detect the invalid JSON and ask the model to re-format it.

---

## Diagnostic Tools

AgenticOS includes several built-in tools to help you diagnose its health:

| Tool | Purpose |
| :--- | :--- |
| `system_health` | Full report on CPU, RAM, Disk, and Agent process stats. |
| `validate_config` | Verifies the runtime configuration is correctly formed. |
| `system_info` | Provides overall system diagnostics. |
| `self_process_info` | Shows the agent's own PID, memory, and handles. |

---

## Cross-Platform OS Automation Issues

### 1. "Volume controls or windows listings fail on Windows."
-   **Cause**: The audio service endpoint enumerator or PowerShell execution policy blocks C# compilation block loads.
-   **Fix**: Ensure your PowerShell execution policy allows local scripts (e.g. `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`) or run `Restart-Service Audiosrv` to reset the Windows Audio service.

### 2. "Minimize or Maximize fails with accessibility errors on macOS."
-   **Cause**: The active terminal running AgenticOS lacks Accessibility control permissions in macOS System Events.
-   **Fix**: Navigate to `System Settings` -> `Privacy & Security` -> `Accessibility`, and ensure your terminal app (e.g., Terminal, iTerm2, or VS Code) is explicitly toggled **ON** to authorize OS-level System Events commands.

### 3. "Wallpaper changes fail silently on Linux."
-   **Cause**: Modern GNOME ignores standard `picture-uri` modifications if System Dark Mode is active.
-   **Fix**: AgenticOS automatically sets both the `picture-uri` and `picture-uri-dark` keys in v2.1.0 to ensure comprehensive compatibility.

---

## Still Having Issues?

1.  **Check the Logs**: Open `agent.log` and search for `ERROR`.
2.  **Audit the SQLite DB**: Use a tool like SQLite Browser to view the `tool_events` table in `data/memory.sqlite3`.
3.  **Reset Config**: Delete `config.yaml` and restart; the system will generate a fresh copy with safe defaults.

---

*Last Updated: 2026-05-13*
*Status: Troubleshooting Guide*
