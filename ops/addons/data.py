"""Data Analysis and Charting Plugin using pandas and matplotlib."""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List

from kernel.registry import tool

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import matplotlib.pyplot as plt
    import matplotlib
    # Use non-interactive backend to avoid blocking or requiring a display
    matplotlib.use("Agg")
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


@tool(name="datasummarizecsv", category="Data", desc="Load a CSV and return its schema and statistical summary.")
def datasummarizecsv(csv_path: str) -> str:
    """Reads a CSV file using pandas and returns a JSON summary of its columns and numeric statistics.

    Args:
        csv_path: Absolute or relative path to the CSV file.
    """
    if not HAS_PANDAS:
        return "Error: pandas library is not installed. Add pandas to requirements.txt."

    if not os.path.exists(csv_path):
        return f"Error: CSV file not found at {csv_path}"

    try:
        df = pd.read_csv(csv_path)
        
        summary: Dict[str, Any] = {
            "row_count": len(df),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_values": df.isnull().sum().to_dict()
        }
        
        # Include describe() for numeric columns
        numeric_df = df.select_dtypes(include=["number"])
        if not numeric_df.empty:
            summary["numeric_statistics"] = numeric_df.describe().to_dict()
            
        return json.dumps(summary, indent=2)
    except Exception as e:
        return f"Error processing CSV: {e}"


@tool(name="datageneratechart", category="Data", desc="Generate a chart from a CSV file and save it as an image.")
def datageneratechart(csv_path: str, x_column: str, y_columns: List[str], chart_type: str, output_image: str) -> str:
    """Generates a chart using matplotlib and pandas, and saves it to a file.

    Args:
        csv_path: Path to the source CSV file.
        x_column: The column to use for the X-axis.
        y_columns: A list of columns to plot on the Y-axis.
        chart_type: The type of chart to generate ('line', 'bar', 'scatter').
        output_image: Path to save the generated image (e.g. 'chart.png').
    """
    if not HAS_PANDAS or not HAS_MATPLOTLIB:
        return "Error: pandas or matplotlib library is not installed."

    if not os.path.exists(csv_path):
        return f"Error: CSV file not found at {csv_path}"

    if chart_type.lower() not in ["line", "bar", "scatter"]:
        return f"Error: Unsupported chart_type '{chart_type}'. Use 'line', 'bar', or 'scatter'."

    if not y_columns:
        return "Error: You must provide at least one y_column."

    try:
        df = pd.read_csv(csv_path)
        
        if x_column not in df.columns:
            return f"Error: X column '{x_column}' not found in CSV."
            
        for y_col in y_columns:
            if y_col not in df.columns:
                return f"Error: Y column '{y_col}' not found in CSV."

        plt.figure(figsize=(10, 6))
        
        ctype = chart_type.lower()
        if ctype == "line":
            for y_col in y_columns:
                plt.plot(df[x_column], df[y_col], marker='o', label=y_col)
        elif ctype == "bar":
            # For multiple y_columns, pandas plot wrapper handles grouping better
            df.plot(x=x_column, y=y_columns, kind='bar', ax=plt.gca())
        elif ctype == "scatter":
            for y_col in y_columns:
                plt.scatter(df[x_column], df[y_col], label=y_col)
                
        plt.title(f"{chart_type.capitalize()} Chart")
        plt.xlabel(x_column)
        plt.ylabel(", ".join(y_columns))
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.tight_layout()
        
        plt.savefig(output_image)
        plt.close()
        
        return f"Success: Chart generated and saved to {output_image}"
    except Exception as e:
        return f"Error generating chart: {e}"
