import pytest
import json
from core.tool_registry import ToolRegistry

@pytest.fixture
def registry():
    cfg = {
        'agent': {'workspace': 'workspace'},
        'rules': {},
    }
    return ToolRegistry(cfg=cfg)

def test_web_search_to_write_chain(registry):
    # web_search -> fetch_url -> write_json

    search_res = registry.call("web_search", {"query": "python", "num_results": "1"})
    assert search_res is not None
    assert "Error:" not in search_res

    fetch_res = registry.call("fetch_url", {"url": "https://example.com"})
    assert fetch_res is not None
    assert "Error:" not in fetch_res

    write_res = registry.call("write_json", {"path": "workspace/test_web.json", "data": json.dumps({"content": fetch_res})})
    assert "Wrote JSON" in write_res

def test_read_process_write_chain(registry):
    # write_json -> read_json -> process -> write_json

    # ensure a file exists
    registry.call("write_json", {"path": "workspace/dummy.json", "data": '{"text": "hello world"}'})

    read_res = registry.call("read_json", {"path": "workspace/dummy.json"})
    assert "hello world" in read_res

    processed = read_res.upper()
    write_res = registry.call("write_json", {"path": "workspace/dummy_out.json", "data": '{"text": "HELLO WORLD"}'})
    assert "Wrote JSON" in write_res

    verify_res = registry.call("read_json", {"path": "workspace/dummy_out.json"})
    assert "HELLO WORLD" in verify_res

def test_run_command_to_parse_chain(registry):
    # run_command -> capture_output -> parse_result

    cmd_res = registry.call("run_command", {"command": "echo chain test"})
    assert "chain test" in cmd_res

    parsed = cmd_res.strip().split()
    assert "chain" in parsed
    assert "test" in parsed
