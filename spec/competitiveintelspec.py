from unittest.mock import patch
from ops.addons.intel import competitiveintel
import os
from datetime import datetime

class TestCompetitiveIntel:
    @patch('ops.addons.intel.WebTools.search')
    def test_valid_data_generates_matrix(self, mock_search):
        # Mock web search responses
        def mock_search_side_effect(query, num_results):
            if "github" in query.lower():
                return "Fake github page. AutoGPT has 150k stars. updated Oct 5."
            else:
                return "AutoGPT is an autonomous AI agent."

        mock_search.side_effect = mock_search_side_effect

        result = competitiveintel(["AutoGPT"])

        from kernel.settings import DEFAULT_WORKSPACE
        from pathlib import Path
        today = datetime.now().strftime("%Y-%m-%d")
        expected_path = str(Path(DEFAULT_WORKSPACE) / f"daily_logs/competitor_matrix_{today}.md")
        assert result == f"Wrote competitive matrix to {expected_path}"
        assert os.path.exists(expected_path)

        with open(expected_path, "r") as f:
            content = f.read()

        assert "AutoGPT" in content
        assert "150k" in content
        assert "Oct 5" in content
        assert "autonomous" in content

        # Cleanup
        os.remove(expected_path)

    @patch('ops.addons.intel.WebTools.search')
    def test_fetch_fails_no_crash(self, mock_search, caplog):
        mock_search.side_effect = Exception("Simulated network error")

        result = competitiveintel(["CrewAI"])

        from kernel.settings import DEFAULT_WORKSPACE
        from pathlib import Path
        today = datetime.now().strftime("%Y-%m-%d")
        expected_path = str(Path(DEFAULT_WORKSPACE) / f"daily_logs/competitor_matrix_{today}.md")
        assert result == f"Wrote competitive matrix to {expected_path}"

        with open(expected_path, "r") as f:
            content = f.read()

        assert "CrewAI" in content
        assert "data unavailable" in content

        assert "Failed to fetch github info for CrewAI" in caplog.text
        assert "Failed to fetch site info for CrewAI" in caplog.text

        if os.path.exists(expected_path):
            os.remove(expected_path)

    def test_empty_list_no_crash(self):
        result = competitiveintel([])
        assert result == "No competitors provided."
