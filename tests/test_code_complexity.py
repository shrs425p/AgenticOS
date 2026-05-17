"""Tests for the code_complexity plugin."""
import os
from unittest.mock import MagicMock, patch
from tools.plugins.code_complexity import (
    _ensure_radon_installed,
    code_complexity,
)


def test_ensure_radon_installed_import():
    """Verify package import verification helper."""
    with patch("sys.modules", {}):
        # Even if radon is missing, the installer fallback works or returns correctly
        installed = _ensure_radon_installed()
        assert isinstance(installed, bool)


def test_code_complexity_invalid_file():
    """Verify error returns for missing or non-Python files."""
    # Test missing file
    result = code_complexity("missing_file.py")
    assert "Error: Target file not found" in result

    # Test non-Python file
    with open("temp_test.txt", "w") as f:
        f.write("test")
    try:
        result = code_complexity("temp_test.txt")
        assert "Error: Target file must be a Python (.py) file" in result
    finally:
        if os.path.exists("temp_test.txt"):
            os.remove("temp_test.txt")


@patch("tools.plugins.code_complexity._ensure_radon_installed")
@patch("radon.visitors.ComplexityVisitor.from_code")
def test_code_complexity_analysis(mock_visitor_from_code, mock_installed):
    """Verify cyclomatic complexity report parsing and rank evaluations."""
    mock_installed.return_value = True

    # 1. Mock radon blocks returned by visitor
    mock_block1 = MagicMock()
    mock_block1.name = "calculate_sum"
    mock_block1.complexity = 3
    mock_block1.lineno = 10
    mock_block1.is_method = False

    mock_block2 = MagicMock()
    mock_block2.name = "process_payload"
    mock_block2.complexity = 12
    mock_block2.lineno = 25
    mock_block2.is_method = True

    mock_visitor = MagicMock()
    mock_visitor.blocks = [mock_block1, mock_block2]
    mock_visitor_from_code.return_value = mock_visitor

    # 2. Write temp python file
    temp_py = "temp_code.py"
    with open(temp_py, "w") as f:
        f.write("def calculate_sum(): pass\n")

    try:
        # Run analyzer
        report = code_complexity(temp_py)

        assert "# Cyclomatic Complexity Report: temp_code.py" in report
        # Grade A for complexity 3
        assert "calculate_sum" in report
        assert "Excellent (Simple, low risk block)" in report
        # Grade C or D for complexity 12
        assert "process_payload" in report
        assert "Summary Analytics" in report
        assert "Average Cyclomatic Complexity" in report
    finally:
        if os.path.exists(temp_py):
            os.remove(temp_py)
