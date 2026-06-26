"""Module for structured.py"""
from __future__ import annotations

import csv
import json


from kernel.base import tool
class StructuredMixin:
    @tool(name="readjson", desc="Read and parse JSON file. Args: path", category="Files")
    def readjson(self, path: str) -> str:
        """readjson function."""
        p = self._resolve(path)
        try:
            data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            return json.dumps(data, indent=2)
        except Exception as e:
            return f"Error: {e}"

    @tool(name="writejson", desc="Write JSON file. Args: path, data (JSON string)", category="Files")
    def writejson(self, path: str, data: str) -> str:
        """writejson function."""
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            obj = json.loads(data) if data else {}
            formatted = json.dumps(obj, indent=2)
            line_count = len(formatted.splitlines())
            if line_count >= 200:
                return (
                    f"Error: The JSON you are trying to write has {line_count} lines, which is 200 or more lines. "
                    "To prevent generating excessively large files at once, you must work in parts."
                )
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(formatted, encoding="utf-8")
            return f"Wrote JSON to {path}"
        except Exception as e:
            return f"Error: {e}"

    @tool(name="readcsv", desc="Read CSV as text table. Args: path", category="Files")
    def readcsv(self, path: str, max_rows: str = "50") -> str:
        """readcsv function."""
        p = self._resolve(path)
        try:
            limit = max(1, int(max_rows))
            with open(p, "r", encoding="utf-8", errors="replace", newline="") as f:
                rdr = csv.reader(f)
                rows = []
                for i, row in enumerate(rdr):
                    rows.append(row)
                    if i + 1 >= limit:
                        break
            return json.dumps(rows, indent=2)
        except Exception as e:
            return f"Error: {e}"

    @tool(name="writecsv", desc="Write CSV (JSON array of arrays). Args: path, data", category="Files")
    def writecsv(self, path: str, data: str) -> str:
        """writecsv function."""
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            rows = json.loads(data) if data else []
            if not isinstance(rows, list):
                return "Error: data must be a JSON array."
            line_count = len(rows)
            if line_count >= 200:
                return (
                    f"Error: The CSV you are trying to write has {line_count} rows, which is 200 or more lines/rows. "
                    "To prevent generating excessively large files at once, you must work in parts."
                )
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                for row in rows:
                    w.writerow(row if isinstance(row, list) else [row])
            return f"Wrote CSV to {path}"
        except Exception as e:
            return f"Error: {e}"
