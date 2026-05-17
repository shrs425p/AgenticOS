import datetime
import json
from pathlib import Path
from core.tool_registry import tool
import importlib
from tools.web import WebTools

@tool(name="research_loop", desc="Runs a multi-round research loop on a topic.", category="Research")
def research_loop(topic: str, rounds: str = "3") -> str:
    """Runs a multi-round research loop on a topic."""

    if not topic or not topic.strip():
        return json.dumps({"status": "handled gracefully", "reason": "Empty topic"})
    try:
        rounds_int = int(rounds)
    except ValueError:
        rounds_int = 3

    if rounds_int <= 0:
        return json.dumps({"status": "handled gracefully", "reason": "rounds=0"})

    rounds_int = min(rounds_int, 5)

    log_dir = Path("workspace/daily_logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"deep_research_{today}.md"

    # Resolve WebTools from this module's attribute so tests that patch
    # "tools.plugins.research_loop.WebTools" reliably replace the class.
    mod = importlib.import_module(__name__)
    web_tools_cls = getattr(mod, "WebTools", None)
    if web_tools_cls is None:
        from tools.web import WebTools as web_tools_cls
    web_tools = web_tools_cls()

    log_content = f"# Deep Research: {topic} ({today})\n\n"

    current_topic = topic
    all_failed = True

    result = {"topic": topic, "rounds_completed": 0, "status": "success"}

    for r in range(1, rounds_int + 1):
        log_content += f"## Round {r}: {current_topic}\n\n"
        try:
            # First, search
            search_results = web_tools.search(query=current_topic, num_results="3")
            if "Search error" in search_results or "No results found" in search_results:
                raise Exception(search_results)

            # Since WebTools.search returns a formatted string, we will just include it in the log
            log_content += "### Search Results & Key Concepts\n"
            log_content += f"{search_results}\n\n"

            # Parse out the URLs from the search_results string and use fetch_url on them
            urls_to_fetch = []
            for line in search_results.splitlines():
                if "http" in line and not line.startswith("Direct Answer:"):
                    parts = line.split("http")
                    if len(parts) > 1:
                        url = "http" + parts[1].strip()
                        urls_to_fetch.append(url)

            if urls_to_fetch:
                log_content += "### Deeper Insights from Sources\n"
                for i, url in enumerate(urls_to_fetch[:3]):
                    try:
                        page_text = web_tools.get_page_text(url=url)
                        if page_text and "Error:" not in page_text:
                            insight = page_text[:300].replace("\n", " ") + "..."
                            log_content += f"- Source {i+1} ({url}): {insight}\n"
                    except Exception as fe:
                        log_content += f"- Source {i+1} ({url}): Failed to fetch deeper insight ({fe})\n"
                log_content += "\n"

            all_failed = False
            result["rounds_completed"] += 1

            # Refine topic for next round
            current_topic = f"{topic} deeper insights round {r}"

        except Exception as e:
            # Handle failure per round: log warning, skip, continue
            warning_msg = f"Warning: Round {r} failed with error: {e}"
            print(warning_msg)
            log_content += f"**{warning_msg}**\n\n"
            continue

    if all_failed:
        log_content += "## Failure Summary\nAll research rounds failed to produce results.\n"
        result["status"] = "failure"
        result["reason"] = "All rounds failed"

    try:
        # Use UTF-8 and replace undecodable characters to avoid platform encoding errors
        log_file.write_text(log_content, encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"Failed to write log file: {e}")

    return json.dumps(result)
