import sys
import os
import time
import datetime
from pathlib import Path
import inspect

# Adjust Python path to load core
sys.path.insert(0, os.path.abspath("."))
from core.tool_registry import ToolRegistry

cfg = {
    "agent": {"workspace": "workspace"},
    "rules": {},
}


def generate_minimal_inputs(func):
    sig = inspect.signature(func)
    inputs = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.default != inspect.Parameter.empty:
            inputs[name] = param.default
            continue

        # Try to infer type
        if param.annotation is int:
            inputs[name] = 1
        elif param.annotation is float:
            inputs[name] = 1.0
        elif param.annotation is bool:
            inputs[name] = True
        elif param.annotation is list:
            inputs[name] = []
        elif param.annotation is dict:
            inputs[name] = {}

        else:
            # Fallback to string
            inputs[name] = "test"

        # Overrides for specific path parameters to avoid creating random files in root
        if name in ["path", "file", "filename"]:
            inputs[name] = "workspace/test_dummy.txt"
        elif name == "command":
            inputs[name] = "echo 1"
        elif name == "url":
            inputs[name] = "https://example.com"

    return inputs


def run_smoke_tests(registry):
    results = []
    failed_tools = []

    # 1. Identify all tool categories
    categories = {}
    for name, info in registry.registry.items():
        cat = info.get("category", "General")
        categories.setdefault(cat, []).append(name)

    # 2. Pick ONE representative tool for each category
    for category, tools in categories.items():
        # Prefer simpler tools for smoke testing
        tool_name = tools[0]
        for t in tools:
            if t in [
                "read_file",
                "run_command",
                "web_search",
                "system_info",
                "browser_read_page_text",
                "plugin_health_check",
            ]:
                tool_name = t
                break

        info = registry.registry[tool_name]
        fn = info["fn"]
        inputs = generate_minimal_inputs(fn)

        start_time = time.time()
        try:
            # Call it with minimal valid input
            out = fn(**inputs)

            end_time = time.time()
            time_ms = int((end_time - start_time) * 1000)

            # Assert return value is not None
            if out is not None:
                results.append(
                    {
                        "tool": tool_name,
                        "input": str(inputs),
                        "output_type": type(out).__name__,
                        "pass_fail": "PASS",
                        "time_ms": time_ms,
                    }
                )
            else:
                failed_tools.append((tool_name, "Returned None"))
                results.append(
                    {
                        "tool": tool_name,
                        "input": str(inputs),
                        "output_type": "None",
                        "pass_fail": "FAIL",
                        "time_ms": time_ms,
                    }
                )
        except Exception as e:
            end_time = time.time()
            time_ms = int((end_time - start_time) * 1000)
            failed_tools.append((tool_name, f"{type(e).__name__}: {str(e)}"))
            results.append(
                {
                    "tool": tool_name,
                    "input": str(inputs),
                    "output_type": type(e).__name__,
                    "pass_fail": "FAIL",
                    "time_ms": time_ms,
                }
            )

    return results, failed_tools


def run_error_recovery(registry):
    # Call one tool with invalid input via its internal fn to hit actual Python Exception (not the registry.call exception wrapper)
    fn = registry.registry["read_file"]["fn"]
    try:
        # Pass an integer instead of a string path
        fn(path=123)
        return False, "Did not raise exception"
    except AttributeError:
        # Expected from read_file when trying to call .replace or .resolve on int
        return True, "Raised specific exception: AttributeError"
    except TypeError:
        return True, "Raised specific exception: TypeError"
    except Exception as e:
        # Bare exception
        if type(e) is Exception:
            return False, "Raised bare Exception"
        return True, f"Raised specific exception: {type(e).__name__}"


def run_tool_chains(registry):
    chain_results = []
    reg = registry.registry

    # Chain 1: web_search -> fetch_url -> write_file
    if "web_search" in reg and "fetch_url" in reg and "write_file" in reg:
        try:
            registry.call("web_search", {"query": "python", "num_results": "1"})
            fetch_res = registry.call("fetch_url", {"url": "https://example.com"})
            registry.call(
                "write_file",
                {"path": "workspace/test_web.txt", "content": fetch_res[:100]},
            )

            chain_results.append(("web_search -> fetch_url -> write_file", "PASS"))
        except Exception as e:
            chain_results.append(
                ("web_search -> fetch_url -> write_file", f"FAIL ({str(e)})")
            )

    # Chain 2: read_file -> process -> write_file
    process_tool = (
        "word_count"
        if "word_count" in reg
        else ("grep_file" if "grep_file" in reg else None)
    )
    if "read_file" in reg and "write_file" in reg and process_tool:
        try:
            registry.call(
                "write_file",
                {"path": "workspace/test_dummy.txt", "content": "hello world"},
            )
            registry.call("read_file", {"path": "workspace/test_dummy.txt"})
            if process_tool == "word_count":
                process_res = registry.call(
                    process_tool, {"path": "workspace/test_dummy.txt"}
                )
            else:
                process_res = registry.call(
                    process_tool, {"path": "workspace/test_dummy.txt", "query": "hello"}
                )
            registry.call(
                "write_file",
                {"path": "workspace/test_process.txt", "content": str(process_res)},
            )

            chain_results.append((f"read_file -> {process_tool} -> write_file", "PASS"))
        except Exception as e:
            chain_results.append(
                (f"read_file -> {process_tool} -> write_file", f"FAIL ({str(e)})")
            )

    # Chain 3: terminal_command -> capture_output -> parse_result
    if "run_command" in reg:
        try:
            registry.call(
                "run_command",
                {"command": "echo 'test command output' > workspace/cmd_out.txt"},
            )
            if "grep_file" in reg:
                registry.call(
                    "grep_file", {"path": "workspace/cmd_out.txt", "query": "test"}
                )

                chain_results.append(
                    ("terminal_command -> capture_output -> grep_file", "PASS")
                )
            else:
                chain_results.append(
                    (
                        "run_command -> capture_output -> parse_result",
                        "SKIPPED (no parse tool)",
                    )
                )
        except Exception as e:
            chain_results.append(
                (
                    "terminal_command -> capture_output -> parse_result",
                    f"FAIL ({str(e)})",
                )
            )

    return chain_results


def get_yesterdays_log_path():
    logs_dir = Path("docs/daily_logs")
    if not logs_dir.exists():
        return None

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    expected_path = logs_dir / f"integration_test_{yesterday.strftime('%Y-%m-%d')}.md"
    if expected_path.exists():
        return expected_path

    # Fallback: just get the latest one that is not today's
    log_files = list(logs_dir.glob("integration_test_*.md"))
    today_str = today.strftime("%Y-%m-%d")
    past_logs = [f for f in log_files if today_str not in f.name]
    if past_logs:
        return sorted(past_logs)[-1]
    return None


def compare_with_yesterday(results):
    yesterday_path = get_yesterdays_log_path()
    flags = []

    if not yesterday_path:
        return flags

    content = yesterday_path.read_text()
    yesterday_passing = set()
    for line in content.split("\n"):
        if "|" in line and "PASS" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                tool_name = parts[1]
                yesterday_passing.add(tool_name)

    for r in results:
        if r["tool"] in yesterday_passing and r["pass_fail"] == "FAIL":
            flags.append(
                f"FLAG: Tool {r['tool']} was passing yesterday but is failing today."
            )

    return flags


def generate_markdown_report(
    results, failed_tools, error_recovery_pass, chain_results, flags
):
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    report_lines = []
    report_lines.append(f"# Integration Test Report - {today_str}")
    report_lines.append("")

    if flags:
        report_lines.append("## ⚠ Regression Flags")
        for f in flags:
            report_lines.append(f"- {f}")
        report_lines.append("")

    report_lines.append("## Smoke Test Results")
    report_lines.append("| Tool | Input | Output Type | Pass/Fail | Time (ms) |")
    report_lines.append("|------|-------|-------------|-----------|-----------|")
    for r in results:
        report_lines.append(
            f"| {r['tool']} | `{r['input']}` | {r['output_type']} | {r['pass_fail']} | {r['time_ms']} |"
        )
    report_lines.append("")

    report_lines.append("## Tool Chain Results")
    if not chain_results:
        report_lines.append("- No chains executed.")
    for chain, status in chain_results:
        report_lines.append(f"- {chain}: **{status}**")
    report_lines.append("")

    report_lines.append("## Error Recovery Results")
    report_lines.append(
        f"- Missing/Invalid argument handling: **{'PASS' if error_recovery_pass else 'FAIL'}**"
    )
    report_lines.append("")

    if failed_tools:
        report_lines.append("## Failed Tools Details")
        for tool, err in failed_tools:
            report_lines.append(f"- **{tool}**: {err}")
        report_lines.append("")

    health = "GOOD"
    if (
        failed_tools
        or not error_recovery_pass
        or any("FAIL" in status for _, status in chain_results)
    ):
        health = "WARNING"
    if len(failed_tools) > len(results) / 2:
        health = "CRITICAL"

    report_lines.append("## Integration Health")
    report_lines.append(f"**{health}**")

    return "\n".join(report_lines)


def main():
    os.makedirs("docs/daily_logs", exist_ok=True)

    registry = ToolRegistry(cfg=cfg)
    print("Running smoke tests...")
    results, failed_tools = run_smoke_tests(registry)

    print("Running error recovery tests...")
    error_recovery_pass, err_msg = run_error_recovery(registry)
    print(f"Error recovery result: {err_msg}")

    print("Running tool chains...")
    chain_results = run_tool_chains(registry)

    print("Comparing with yesterday...")
    flags = compare_with_yesterday(results)

    print("Generating report...")
    report_content = generate_markdown_report(
        results, failed_tools, error_recovery_pass, chain_results, flags
    )

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    report_path = f"docs/daily_logs/integration_test_{today_str}.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
