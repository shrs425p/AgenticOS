import json
from pathlib import Path
from tools.filesystem.structured import StructuredMixin

class MockStructuredTools(StructuredMixin):
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)

    def _resolve(self, path: str) -> Path:
        return (self.base_dir / path).resolve()

    def _deny_file_modify(self):
        pass

    def _deny_internal_writes(self, p):
        pass

def test_json_tools(tmp_path):
    tool = MockStructuredTools(tmp_path)
    
    # 1. Test write_json
    res_write = tool.write_json("test.json", '{"a": 1, "b": 2}')
    assert "Wrote JSON" in res_write
    assert (tmp_path / "test.json").exists()
    
    # 2. Test read_json
    res_read = tool.read_json("test.json")
    data = json.loads(res_read)
    assert data["a"] == 1
    assert data["b"] == 2
    
    # 3. Test read_json error (invalid json or missing file)
    assert "Error:" in tool.read_json("nonexistent.json")
    
    # 4. Test write_json error (invalid json string)
    assert "Error:" in tool.write_json("test.json", "{invalid json")
    
    # 5. Test empty write_json
    res_empty = tool.write_json("empty.json", "")
    assert "Wrote JSON" in res_empty
    assert json.loads((tmp_path / "empty.json").read_text()) == {}

def test_csv_tools(tmp_path):
    tool = MockStructuredTools(tmp_path)
    
    # 1. Test write_csv (list of lists)
    csv_data = '[["Name", "Age"], ["Alice", 30], ["Bob", 25]]'
    res_write = tool.write_csv("test.csv", csv_data)
    assert "Wrote CSV" in res_write
    assert (tmp_path / "test.csv").exists()
    
    # 2. Test read_csv
    res_read = tool.read_csv("test.csv")
    rows = json.loads(res_read)
    assert len(rows) == 3
    assert rows[0] == ["Name", "Age"]
    assert rows[1] == ["Alice", "30"]
    
    # 3. Test read_csv with custom max_rows
    res_read_limit = tool.read_csv("test.csv", max_rows="1")
    rows_limit = json.loads(res_read_limit)
    assert len(rows_limit) == 1
    
    # 4. Test read_csv with invalid max_rows (returns Error)
    res_read_invalid_limit = tool.read_csv("test.csv", max_rows="invalid")
    assert "Error:" in res_read_invalid_limit
    
    # 5. Test write_csv with list of scalars
    res_scalar = tool.write_csv("scalar.csv", '["row1", "row2"]')
    assert "Wrote CSV" in res_scalar
    
    # 6. Test write_csv errors
    assert "data must be a JSON array" in tool.write_csv("error.csv", '{"not": "array"}')
    assert "Error:" in tool.write_csv("error.csv", "{invalid csv json")
    
    # 7. Test empty write_csv
    res_empty = tool.write_csv("empty.csv", "")
    assert "Wrote CSV" in res_empty
    
    # 8. Test read_csv error
    assert "Error:" in tool.read_csv("nonexistent.csv")


def test_structured_write_limits(tmp_path):
    tool = MockStructuredTools(tmp_path)
    
    # 1. JSON under limit (formatted JSON will have ~100 lines)
    res_json_under = tool.write_json("under.json", json.dumps({"list": [1] * 40}))
    assert "Wrote JSON" in res_json_under
    
    # JSON over/at limit (formatted JSON will have > 200 lines)
    res_json_over = tool.write_json("over.json", json.dumps({"list": [1] * 200}))
    assert "Error: The JSON you are trying to write has" in res_json_over
    assert "200 or more lines" in res_json_over

    # 2. CSV under limit
    res_csv_under = tool.write_csv("under.csv", json.dumps([[1, 2]] * 199))
    assert "Wrote CSV" in res_csv_under
    
    # CSV over/at limit (200 rows)
    res_csv_over = tool.write_csv("over.csv", json.dumps([[1, 2]] * 200))
    assert "Error: The CSV you are trying to write has" in res_csv_over
    assert "200 or more lines/rows" in res_csv_over
