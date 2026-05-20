"""Module for competitive_intel.py"""
from datetime import datetime
import logging
import re
from pathlib import Path
from core.tool_registry import tool
from core.runtime_config import DEFAULT_WORKSPACE
from tools.web import WebTools

@tool(
    name="competitive_intel",
    category="Business",
    desc="Fetches competitor intelligence matrix."
)
def competitive_intel(competitors: list | None = None) -> str:
    """
    Fetches competitor intelligence matrix.
    Args:
        competitors: Optional list of competitor names.
    """
    if competitors is None:
        competitors = ["AutoGPT", "CrewAI", "LangGraph", "OpenDevin", "Agno"]

    if not competitors:
        return "No competitors provided."

    web_tools = WebTools()

    matrix_rows = []
    matrix_rows.append("| Name | Stars | Last Commit | Core Feature Claim | Gap vs AgenticOS |")
    matrix_rows.append("|---|---|---|---|---|")

    for competitor in competitors:
        stars = "data unavailable"
        last_commit = "data unavailable"
        core_feature = "data unavailable"

        try:
            github_search = web_tools.search(f"{competitor} github", num_results="5")

            star_match = re.search(r'([\d\.]+k?)\s+stars?', github_search, re.IGNORECASE)
            if star_match:
                stars = star_match.group(1)

            commit_match = re.search(r'commit.*?on\s+([A-Z][a-z]+\s+\d{1,2}(?:,\s+\d{4})?)', github_search, re.IGNORECASE)
            if commit_match:
                last_commit = commit_match.group(1)
            else:
                commit_match2 = re.search(r'updated\s+([A-Z][a-z]+\s+\d{1,2})', github_search, re.IGNORECASE)
                if commit_match2:
                    last_commit = commit_match2.group(1)
        except Exception as e:
            logging.warning(f"Failed to fetch github info for {competitor}: {e}")

        try:
            site_search = web_tools.search(f"{competitor} AI agent official site", num_results="2")
            if site_search:
                lines = [line.strip() for line in site_search.split("\n") if line.strip() and not line.startswith("-") and not line.startswith("URL") and "http" not in line]
                if lines:
                    core_feature = lines[0][:60] + ("..." if len(lines[0]) > 60 else "")
        except Exception as e:
            logging.warning(f"Failed to fetch site info for {competitor}: {e}")

        matrix_rows.append(f"| {competitor} | {stars} | {last_commit} | {core_feature} | Needs Analysis |")

    content = "\n".join(matrix_rows)
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = str(Path(DEFAULT_WORKSPACE) / f"daily_logs/competitor_matrix_{today}.md")

    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return f"Wrote competitive matrix to {output_path}"
