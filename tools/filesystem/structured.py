"""Module for structured.py"""
from __future__ import annotations

import csv
import json


from core.tool_base import tool
class StructuredMixin:
    @tool(name="read_json", desc="Read and parse JSON file. Args: path", category="Files")
    def read_json(self, path: str) -> str:
        """read_json function."""
        p = self._resolve(path)
        try:
            data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            return json.dumps(data, indent=2)
        except Exception as e:
            return f"Error: {e}"

    @tool(name="write_json", desc="Write JSON file. Args: path, data (JSON string)", category="Files")
    def write_json(self, path: str, data: str) -> str:
        """write_json function."""
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            obj = json.loads(data) if data else {}
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(obj, indent=2), encoding="utf-8")
            return f"Wrote JSON to {path}"
        except Exception as e:
            return f"Error: {e}"

    @tool(name="read_csv", desc="Read CSV as text table. Args: path", category="Files")
    def read_csv(self, path: str, max_rows: str = "50") -> str:
        """read_csv function."""
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

    @tool(name="write_csv", desc="Write CSV (JSON array of arrays). Args: path, data", category="Files")
    def write_csv(self, path: str, data: str) -> str:
        """write_csv function."""
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            rows = json.loads(data) if data else []
            if not isinstance(rows, list):
                return "Error: data must be a JSON array."
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                for row in rows:
                    w.writerow(row if isinstance(row, list) else [row])
            return f"Wrote CSV to {path}"
        except Exception as e:
            return f"Error: {e}"
