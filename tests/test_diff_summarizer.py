"""Tests for the diff_summarizer plugin."""

from tools.plugins.diff_summarizer import summarize_text_diff


def test_summarize_text_diff_no_changes():
    """Verify behavior when original and updated texts are identical."""
    old_text = "This is a line of text.\nAnother line here."
    new_text = "This is a line of text.\nAnother line here."

    result = summarize_text_diff(old_text, new_text)
    assert result == "No changes detected. The original and updated texts are identical."


def test_summarize_text_diff_with_additions():
    """Verify behavior when new lines are appended."""
    old_text = "Baseline content."
    new_text = "Baseline content.\nAn appended addition."

    result = summarize_text_diff(old_text, new_text)
    assert "Overview of Differences" in result
    assert "Total additions: 1 line(s)" in result
    assert "Total deletions: 0 line(s)" in result
    assert "Added line: 'An appended addition.'" in result


def test_summarize_text_diff_with_deletions():
    """Verify behavior when lines are removed."""
    old_text = "First line.\nSecond line.\nThird line."
    new_text = "First line.\nThird line."

    result = summarize_text_diff(old_text, new_text)
    assert "Overview of Differences" in result
    assert "Total additions: 0 line(s)" in result
    assert "Total deletions: 1 line(s)" in result
    assert "Removed line: 'Second line.'" in result
