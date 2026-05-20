# AgenticOS: User Interface and User Experience (UX)

AgenticOS is designed to feel like a living part of the operating system. While it primarily operates through a CLI (Command Line Interface), its UI is optimized for real-time observability, high-speed feedback, and aesthetic appeal.

---

## Aesthetic Philosophy

AgenticOS uses a "Premium Terminal" aesthetic. It avoids plain, monochromatic text in favor of a curated, harmonious, and soft pastel 256-color palette that helps users distinguish between the agent's thoughts, its actions, and the system's responses without causing visual fatigue.

### Color Mapping:
-   **TEAL / CYAN (Soft Sage Teal)**: The agent's Internal Monologue (Thoughts, Objectives).
-   **GREEN / EMERALD (Sage Mint Green)**: Successful tool execution, successes (`✓`), and the Final Answer thin rule header.
-   **YELLOW / AMBER (Muted Pale Peach)**: Warnings (`▲`), rate-limit retries, and fallback messages.
-   **RED / ROSE (Soft Pastel Rose)**: Errors (`✗`), security blocks, and critical guardrails.
-   **MAGENTA / PURPLE (Soft Pastel Lavender)**: Tool parameters, keys, and observation highlights (`obs:`).
-   **BLUE (Soft Ice Blue)**: Diagnostic information (`◆`) and execution metadata.
-   **GRAY / SLATE (Soft Light Slate Gray)**: Observational content blocks (prefixed with `│`) and horizontal dividers (`─`).

---

## The "No-Lag" Typewriter

As of v2.0.0, AgenticOS features a highly optimized terminal rendering engine. We solved the "IPC Lag" issue where character-by-character printing would pin the CPU.

### Optimization Highlights:
-   **Block Flushing**: Text is rendered in semantic chunks rather than raw bytes.
-   **Typography & Symbol Enforcement**: The UI actively avoids noisy, colored graphical emojis that disrupt readability on Windows and modern term systems. It enforces clean, high-contrast, soft-colored geometric unicode typographic symbols (`▲`, `◆`, `✗`, `✓`, `❯`).
-   **Stream Buffering**: During high-volume outputs (e.g., long file reads), the UI dynamically adjusts the printing speed to remain readable without overwhelming the user.

---

## Desktop Notifications

AgenticOS isn't just trapped in the terminal. It can communicate with you via native Windows notifications using the `desktop_notifications` tool.

### Notification Scenarios:
1.  **Task Completion**: "Audit finished! See workspace/firewall_report.md."
2.  **Security Alerts**: "ACTION BLOCKED: Agent attempted to modify C:\Windows."
3.  **High-Value Events**: "Price Alert: NVDA has hit your target price of $140."

---

## Real-Time Charts and Visualization

The agent can generate visual data using `matplotlib`. While these charts aren't rendered *inside* the terminal, they are saved as high-resolution `.png` files in the `workspace/` folder.

### Common Visualizations:
-   **Performance Metrics**: CPU and RAM usage over time (Task 5).
-   **Network Trends**: Bandwidth spikes and top-consuming processes (Task 9).
-   **Finance Logs**: Stock price micro-trends (Task 22).

---

## Command-Line Arguments

You can control the UI behavior directly from the command line when starting the agent:

```powershell
agent --verbose     # Show all model thinking and raw tool outputs
agent --autopilot   # Reduce UI noise and run silently
agent --theme dark  # (Experimental) Toggle high-contrast modes
```

---

## Input Sanitization and Safety

The UI is the primary bridge between the user and the agent. To prevent accidental inputs or command injection:
-   **Confirmations**: Destructive actions (like `format` or `delete_dir`) are visually highlighted with a red block before asking for `y/N`.
-   **Multi-Line Inputs**: The UI handles complex, multi-line user prompts by buffering them until a termination character is received.

---

## UI Configuration (`config.yaml`)

```yaml
agent:
  # Toggle the "Typewriter" effect
  stream: true
  
  # Print verbose model thinking in the console
  verbose_thinking: false
  
  # Log level for terminal output
  log_level: INFO

logging:
  # Enable color-coded console output
  console_output: true
```

---

## UI Diagnostic: The "Crucible" Test

To verify your terminal's compatibility with AgenticOS, run the UI stress test:
```powershell
python scripts/test_ui.py
```
This will test:
1.  **Color support** (ANSI escape codes).
2.  **Unicode typographic symbol rendering** (UTF-8).
3.  **Blinking and bold text**.
4.  **Character-per-second throughput**.

---

## Summary of UI Best Practices
1.  **Keep it Focused**: If the terminal is too noisy, set `log_level: WARNING` in your config.
2.  **Use `evaluation_output.txt`**: If you miss a message in the terminal, check this file-it's a 1:1 mirror of the session.
3.  **Enable Notifications**: For long-running tasks (like a 30-minute web crawl), enable notifications so you can walk away from your desk.

---

*Last Updated: 2026-05-13*
*Status: UI/UX Hardened*
