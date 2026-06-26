import pytest
import yaml
import datetime
from pathlib import Path
from ops.addons.cfgcheck import validate_cfg

@pytest.fixture
def mock_fs(tmp_path, monkeypatch):
    """Fixture to setup mock cfg and workspace."""
    root_dir = tmp_path
    cfg_dir = root_dir / "cfg"
    cfg_dir.mkdir(parents=True)

    workspace_dir = root_dir / "workspace"
    workspace_dir.mkdir(parents=True)

    logs_dir = workspace_dir / "daily_logs"
    logs_dir.mkdir(parents=True)

    original_path = Path

    class MockPath(type(Path())):
        def __new__(cls, *args, **kwargs):
            if args:
                path_str = str(args[0])
                if path_str == ".":
                    return original_path(str(root_dir))
                elif path_str == "cfg":
                    return original_path(str(cfg_dir))
                elif path_str == "cfg.yaml":
                    return original_path(str(root_dir / "cfg.yaml"))
                elif path_str == "workspace/daily_logs":
                    return original_path(str(logs_dir))
                elif path_str.startswith("workspace") and "daily_logs" not in path_str:
                    return original_path(str(workspace_dir))
            return original_path(*args, **kwargs)

    monkeypatch.setattr("ops.addons.cfgcheck.Path", MockPath)

    return root_dir, cfg_dir, workspace_dir, logs_dir

def test_validate_cfg_valid(mock_fs):
    root_dir, cfg_dir, workspace_dir, logs_dir = mock_fs

    # Setup valid cfg
    cfg_yaml = {
        "agent": {
            "provider": "nvidia",
            "workspace": str(workspace_dir),
            "stream": True
        },
        "cloud": {
            "nvidia": {
                "model": "some-model"
            }
        },
        "autonomy": {
            "autopilot": True
        }
    }

    with open(root_dir / "cfg.yaml", "w") as f:
        yaml.dump(cfg_yaml, f)

    res = validate_cfg()

    assert res["agent.provider"] == "ok"
    assert res["agent.workspace"] == "ok"
    assert res["autonomy.autopilot"] == "ok"
    assert res["cloud.nvidia.model"] == "ok"
    assert res["agent.stream"] == "ok"

    # Check report
    today = datetime.date.today().isoformat()
    report_path = logs_dir / f"cfg_audit_{today}.md"
    assert report_path.exists()
    content = report_path.read_text()
    assert "| agent.provider | ok |" in content

def test_validate_cfg_missing_field(mock_fs):
    root_dir, cfg_dir, workspace_dir, logs_dir = mock_fs

    cfg_yaml = {
        "agent": {
            # missing provider
            "workspace": str(workspace_dir)
        },
        "autonomy": {} # missing autopilot
    }

    with open(root_dir / "cfg.yaml", "w") as f:
        yaml.dump(cfg_yaml, f)

    res = validate_cfg()

    assert res["agent.provider"] == "missing"
    assert res["autonomy.autopilot"] == "missing"

def test_validate_cfg_wrong_type(mock_fs):
    root_dir, cfg_dir, workspace_dir, logs_dir = mock_fs

    cfg_yaml = {
        "agent": {
            "provider": "ollama",
            "workspace": str(workspace_dir),
            "stream": "yes" # wrong type
        },
        "autonomy": {
            "autopilot": "on" # wrong type
        }
    }

    with open(root_dir / "cfg.yaml", "w") as f:
        yaml.dump(cfg_yaml, f)

    res = validate_cfg()

    assert res["agent.stream"] == "wrong_type"
    assert res["autonomy.autopilot"] == "wrong_type"

def test_validate_cfg_invalid_provider(mock_fs):
    root_dir, cfg_dir, workspace_dir, logs_dir = mock_fs

    cfg_yaml = {
        "agent": {
            "provider": "openai", # invalid value
            "workspace": str(workspace_dir),
        },
        "autonomy": {
            "autopilot": True
        }
    }

    with open(root_dir / "cfg.yaml", "w") as f:
        yaml.dump(cfg_yaml, f)

    res = validate_cfg()

    assert res["agent.provider"] == "invalid_value"

def test_validate_cfg_non_writable_workspace(mock_fs, monkeypatch):
    root_dir, cfg_dir, workspace_dir, logs_dir = mock_fs

    cfg_yaml = {
        "agent": {
            "provider": "ollama",
            "workspace": "/root/forbidden/path",
        },
        "autonomy": {
            "autopilot": True
        }
    }

    with open(root_dir / "cfg.yaml", "w") as f:
        yaml.dump(cfg_yaml, f)

    original_path = Path

    # Define a custom Path object instead of modifying __class__ on PosixPath
    class FailingPath(type(Path())):
        def touch(self, *args, **kwargs):
            if "forbidden" in str(self).replace("\\", "/"):
                raise PermissionError("Permission denied")
            super().touch(*args, **kwargs)

        def mkdir(self, *args, **kwargs):
            if "forbidden" in str(self).replace("\\", "/"):
                # Simulate mkdir working but touch failing for the inner test
                pass
            else:
                super().mkdir(*args, **kwargs)

    class MockPathWriteFail(type(Path())):
        def __new__(cls, *args, **kwargs):
            if args and str(args[0]) == "/root/forbidden/path":
                 return FailingPath(*args, **kwargs)
            elif args and str(args[0]) == ".":
                 return original_path(str(root_dir))
            elif args and str(args[0]) == "cfg":
                 return original_path(str(cfg_dir))
            elif args and str(args[0]) == "cfg.yaml":
                 return original_path(str(root_dir / "cfg.yaml"))
            elif args and str(args[0]) == "workspace/daily_logs":
                 return original_path(str(logs_dir))
            elif args and "/root/forbidden/path/daily_logs" in str(args[0]).replace("\\", "/"):
                 return original_path(str(logs_dir))
            return original_path(*args, **kwargs)

    monkeypatch.setattr("ops.addons.cfgcheck.Path", MockPathWriteFail)

    res = validate_cfg()
    assert res["agent.workspace"] == "not_writable"

def test_validate_cfg_missing_yaml(mock_fs):
    # Don't create cfg.yaml
    res = validate_cfg()
    assert res == "Error: cfg.yaml is missing."
