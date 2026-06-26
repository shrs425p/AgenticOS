import os
import json
from kernel.sentinel import Sentinel

def test_sentinel_init_default(tmp_path):
    ws = str(tmp_path)
    s = Sentinel(ws)
    assert s.workspace == tmp_path
    assert s.blocklist == []
    assert os.path.exists(s.log_path)

def test_sentinel_load_cfg_success(tmp_path):
    ws = str(tmp_path)
    cfg_path = tmp_path / "sentinel_cfg.json"
    cfg_path.write_text(json.dumps({"blocklist": ["bad_tool", "EVIL_tool"]}))
    
    s = Sentinel(ws, cfg_path=str(cfg_path))
    assert "bad_tool" in s.blocklist
    assert "evil_tool" in s.blocklist

def test_sentinel_load_cfg_fail(tmp_path):
    ws = str(tmp_path)
    cfg_path = tmp_path / "sentinel_cfg.json"
    cfg_path.write_text("{bad json")
    
    s = Sentinel(ws, cfg_path=str(cfg_path))
    assert s.blocklist == []
    
    # Should log the failure
    with open(s.log_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Failed to load cfg" in content

def test_sentinel_pre_check_allowed(tmp_path):
    s = Sentinel(str(tmp_path))
    res = s.pre_check("good_tool", {"arg": 1})
    assert res is None

def test_sentinel_pre_check_blocked(tmp_path):
    cfg_path = tmp_path / "sentinel_cfg.json"
    cfg_path.write_text(json.dumps({"blocklist": ["bad_tool"]}))
    
    alerts = []
    def callback(msg):
        alerts.append(msg)
        
    s = Sentinel(str(tmp_path), cfg_path=str(cfg_path), alert_callback=callback)
    res = s.pre_check("bad_tool", {"arg": 1})
    
    assert res is not None
    assert "Blocked execution" in res
    assert len(alerts) == 1
    assert "bad_tool" in alerts[0]
    
    with open(s.log_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Blocked execution" in content

def test_sentinel_log_action(tmp_path):
    s = Sentinel(str(tmp_path))
    s.log_action("test_tool", {"a": 1}, "success")
    
    with open(s.log_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "test_tool" in content
        assert "success" in content

def test_sentinel_write_log_exception(tmp_path, monkeypatch):
    s = Sentinel(str(tmp_path))
    # Make log_path point to a directory so open() fails
    bad_path = tmp_path / "bad_dir"
    bad_path.mkdir()
    s.log_path = bad_path
    
    # These should not raise an exception
    s.log_action("test", {}, "res")
    s._write_log("test")
