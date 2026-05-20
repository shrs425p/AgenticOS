"""Unit tests for the data analysis plugin."""

import os
import json
import pytest
import tempfile
import csv

from tools.plugins.data_analysis import (
    data_summarize_csv,
    data_generate_chart,
    HAS_PANDAS,
    HAS_MATPLOTLIB
)


@pytest.fixture
def temp_csv():
    """Fixture to create a temporary CSV file with sample data."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Sales", "Expenses"])
        writer.writerow(["2023-01", 1000, 800])
        writer.writerow(["2023-02", 1500, 850])
        writer.writerow(["2023-03", 1200, 900])
        writer.writerow(["2023-04", 1800, 1000])
    
    yield path
    
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def temp_output():
    """Fixture for a temporary output image path."""
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    
    yield path
    
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.mark.skipif(not HAS_PANDAS, reason="pandas is not installed")
def test_data_summarize_csv(temp_csv):
    result = data_summarize_csv(temp_csv)
    
    assert "Error" not in result
    data = json.loads(result)
    
    assert data["row_count"] == 4
    assert "Date" in data["columns"]
    assert "Sales" in data["columns"]
    
    # Should have computed statistics for the numeric columns (Sales, Expenses)
    assert "numeric_statistics" in data
    assert "Sales" in data["numeric_statistics"]
    assert data["numeric_statistics"]["Sales"]["count"] == 4.0
    assert data["numeric_statistics"]["Sales"]["max"] == 1800.0


@pytest.mark.skipif(not HAS_PANDAS, reason="pandas is not installed")
def test_data_summarize_not_found():
    result = data_summarize_csv("nonexistent_file.csv")
    assert "Error: CSV file not found" in result


@pytest.mark.skipif(not HAS_PANDAS or not HAS_MATPLOTLIB, reason="pandas/matplotlib not installed")
def test_data_generate_chart_line(temp_csv, temp_output):
    result = data_generate_chart(
        temp_csv, 
        x_column="Date", 
        y_columns=["Sales", "Expenses"], 
        chart_type="line", 
        output_image=temp_output
    )
    
    assert "Success" in result
    assert os.path.exists(temp_output)
    # File should not be empty
    assert os.path.getsize(temp_output) > 100


@pytest.mark.skipif(not HAS_PANDAS or not HAS_MATPLOTLIB, reason="pandas/matplotlib not installed")
def test_data_generate_chart_bar(temp_csv, temp_output):
    result = data_generate_chart(
        temp_csv, 
        x_column="Date", 
        y_columns=["Sales"], 
        chart_type="bar", 
        output_image=temp_output
    )
    
    assert "Success" in result
    assert os.path.exists(temp_output)
    assert os.path.getsize(temp_output) > 100


@pytest.mark.skipif(not HAS_PANDAS or not HAS_MATPLOTLIB, reason="pandas/matplotlib not installed")
def test_data_generate_chart_invalid_column(temp_csv, temp_output):
    result = data_generate_chart(
        temp_csv, 
        x_column="InvalidCol", 
        y_columns=["Sales"], 
        chart_type="line", 
        output_image=temp_output
    )
    
    assert "Error: X column 'InvalidCol' not found" in result


@pytest.mark.skipif(not HAS_PANDAS or not HAS_MATPLOTLIB, reason="pandas/matplotlib not installed")
def test_data_generate_chart_invalid_type(temp_csv, temp_output):
    result = data_generate_chart(
        temp_csv, 
        x_column="Date", 
        y_columns=["Sales"], 
        chart_type="pie", 
        output_image=temp_output
    )
    
    assert "Error: Unsupported chart_type" in result
