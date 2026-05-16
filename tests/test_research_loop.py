import json
from unittest.mock import patch, MagicMock

from tools.plugins.research_loop import research_loop

@patch("tools.plugins.research_loop.WebTools")
def test_research_loop_happy_path(mock_web_tools, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Setup mock WebTools
    mock_instance = MagicMock()
    mock_web_tools.return_value = mock_instance

    # Return different results for each round
    mock_instance.search.side_effect = [
        "Results for Round 1: AI Agents are getting smarter.",
        "Results for Round 2: AI Agents now self-heal.",
        "Results for Round 3: AI Agents will code themselves."
    ]

    # Run tool
    res_str = research_loop(topic="AI Agents", rounds="3")
    result = json.loads(res_str)

    assert result["status"] == "success"
    assert result["rounds_completed"] == 3
    assert result["topic"] == "AI Agents"

    # Check if log is written
    daily_logs_dir = workspace / "daily_logs"
    assert daily_logs_dir.exists()
    log_files = list(daily_logs_dir.glob("deep_research_*.md"))
    assert len(log_files) == 1

    content = log_files[0].read_text()
    assert "## Round 1" in content
    assert "## Round 2" in content
    assert "## Round 3" in content
    assert "Results for Round 1" in content
    assert "Results for Round 2" in content
    assert "Results for Round 3" in content
    assert "Failure Summary" not in content

@patch("tools.plugins.research_loop.WebTools")
def test_research_loop_round_2_fails(mock_web_tools, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Setup mock WebTools
    mock_instance = MagicMock()
    mock_web_tools.return_value = mock_instance

    # Round 2 throws an exception
    mock_instance.search.side_effect = [
        "Results for Round 1: Good start.",
        Exception("Connection timeout"),
        "Results for Round 3: Recovered."
    ]

    # Run tool
    res_str = research_loop(topic="AI Agents", rounds="3")
    result = json.loads(res_str)

    assert result["status"] == "success"
    assert result["rounds_completed"] == 2

    daily_logs_dir = workspace / "daily_logs"
    log_files = list(daily_logs_dir.glob("deep_research_*.md"))
    content = log_files[0].read_text()

    assert "Warning: Round 2 failed with error: Connection timeout" in content
    assert "Results for Round 1: Good start." in content
    assert "Results for Round 3: Recovered." in content

@patch("tools.plugins.research_loop.WebTools")
def test_research_loop_all_rounds_fail(mock_web_tools, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Setup mock WebTools
    mock_instance = MagicMock()
    mock_web_tools.return_value = mock_instance

    # All rounds return error message string which causes raise Exception
    mock_instance.search.return_value = "Search error: Limit reached"

    # Run tool
    res_str = research_loop(topic="AI Agents", rounds="3")
    result = json.loads(res_str)

    assert result["status"] == "failure"
    assert result["reason"] == "All rounds failed"
    assert result["rounds_completed"] == 0

    daily_logs_dir = workspace / "daily_logs"
    log_files = list(daily_logs_dir.glob("deep_research_*.md"))
    content = log_files[0].read_text()

    assert "## Failure Summary" in content
    assert "All research rounds failed to produce results." in content

def test_research_loop_empty_topic(tmp_path, monkeypatch):
    res_str = research_loop(topic="", rounds="3")
    result = json.loads(res_str)
    assert result["status"] == "handled gracefully"
    assert result["reason"] == "Empty topic"

def test_research_loop_zero_rounds(tmp_path, monkeypatch):
    res_str = research_loop(topic="AI Agents", rounds="0")
    result = json.loads(res_str)
    assert result["status"] == "handled gracefully"
    assert result["reason"] == "rounds=0"
