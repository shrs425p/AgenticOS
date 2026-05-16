import pytest
from core.tool_registry import ToolRegistry
import os

@pytest.fixture
def registry():
    cfg = {
        'agent': {'workspace': 'workspace'},
        'rules': {},
    }
    return ToolRegistry(cfg=cfg)

def test_web_search_to_write_chain(registry):
    # web_search -> fetch_url -> write_file

    search_res = registry.call("web_search", {"query": "python", "num_results": "1"})
    assert search_res is not None
    assert "Error:" not in search_res

    fetch_res = registry.call("fetch_url", {"url": "https://example.com"})
    assert fetch_res is not None
    assert "Error:" not in fetch_res

    write_res = registry.call("write_file", {"path": "workspace/test_web.txt", "content": fetch_res})
    assert "Successfully wrote" in write_res

def test_read_process_write_chain(registry):
    # read_file -> process -> write_file

    # ensure a file exists
    registry.call("write_file", {"path": "workspace/dummy.txt", "content": "hello world"})

    read_res = registry.call("read_file", {"path": "workspace/dummy.txt"})
    assert "hello world" in read_res

    processed = read_res.upper()
    write_res = registry.call("write_file", {"path": "workspace/dummy_out.txt", "content": processed})
    assert "Successfully wrote" in write_res

    verify_res = registry.call("read_file", {"path": "workspace/dummy_out.txt"})
    assert "HELLO WORLD" in verify_res

def test_run_command_to_parse_chain(registry):
    # run_command -> capture_output -> parse_result

    cmd_res = registry.call("run_command", {"command": "echo 'chain test'"})
    assert "chain test" in cmd_res

    parsed = cmd_res.strip().split()
    assert "chain" in parsed
    assert "test" in parsed
