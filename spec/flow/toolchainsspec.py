import pytest
import json
from kernel.registry import ToolRegistry

@pytest.fixture
def registry():
    cfg = {
        'agent': {'workspace': 'workspace'},
        'rules': {},
    }
    return ToolRegistry(cfg=cfg)

def test_websearch_to_write_chain(registry):
    # websearch -> fetchurl -> writejson

    search_res = registry.call("websearch", {"query": "python", "num_results": "1"})
    assert search_res is not None
    assert "Error:" not in search_res

    fetch_res = registry.call("fetchurl", {"url": "https://example.com"})
    assert fetch_res is not None
    assert "Error:" not in fetch_res

    write_res = registry.call("writejson", {"path": "workspace/test_web.json", "data": json.dumps({"content": fetch_res})})
    assert "Wrote JSON" in write_res

def test_read_process_write_chain(registry):
    # writejson -> readjson -> process -> writejson

    # ensure a file exists
    registry.call("writejson", {"path": "workspace/dummy.json", "data": '{"text": "hello world"}'})

    read_res = registry.call("readjson", {"path": "workspace/dummy.json"})
    assert "hello world" in read_res

    processed = read_res.upper()
    write_res = registry.call("writejson", {"path": "workspace/dummy_out.json", "data": '{"text": "HELLO WORLD"}'})
    assert "Wrote JSON" in write_res

    verify_res = registry.call("readjson", {"path": "workspace/dummy_out.json"})
    assert "HELLO WORLD" in verify_res

def test_runcommand_to_parse_chain(registry):
    # runcommand -> capture_output -> parse_result

    cmd_res = registry.call("runcommand", {"command": "echo chain test"})
    assert "chain test" in cmd_res

    parsed = cmd_res.strip().split()
    assert "chain" in parsed
    assert "test" in parsed
