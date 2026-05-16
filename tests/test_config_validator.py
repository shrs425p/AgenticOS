import pytest
import yaml
import datetime
import os
from pathlib import Path
from tools.plugins.config_validator import validate_config

@pytest.fixture
def mock_fs(tmp_path, monkeypatch):
    """Fixture to setup mock config and workspace."""
    root_dir = tmp_path
    config_dir = root_dir / "config"
    config_dir.mkdir(parents=True)

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
                elif path_str == "config":
                    return original_path(str(config_dir))
                elif path_str == "config.yaml":
                    return original_path(str(root_dir / "config.yaml"))
                elif path_str == "workspace/daily_logs":
                    return original_path(str(logs_dir))
                elif path_str.startswith("workspace") and "daily_logs" not in path_str:
                    return original_path(str(workspace_dir))
            return original_path(*args, **kwargs)

    monkeypatch.setattr("tools.plugins.config_validator.Path", MockPath)

    return root_dir, config_dir, workspace_dir, logs_dir

def test_validate_config_valid(mock_fs):
    root_dir, config_dir, workspace_dir, logs_dir = mock_fs

    # Setup valid config
    config_yaml = {
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

    with open(root_dir / "config.yaml", "w") as f:
        yaml.dump(config_yaml, f)

    res = validate_config()

    assert res["agent.provider"] == "ok"
    assert res["agent.workspace"] == "ok"
    assert res["autonomy.autopilot"] == "ok"
    assert res["cloud.nvidia.model"] == "ok"
    assert res["agent.stream"] == "ok"

    # Check report
    today = datetime.date.today().isoformat()
    report_path = logs_dir / f"config_audit_{today}.md"
    assert report_path.exists()
    content = report_path.read_text()
    assert "| agent.provider | ok |" in content

def test_validate_config_missing_field(mock_fs):
    root_dir, config_dir, workspace_dir, logs_dir = mock_fs

    config_yaml = {
        "agent": {
            # missing provider
            "workspace": str(workspace_dir)
        },
        "autonomy": {} # missing autopilot
    }

    with open(root_dir / "config.yaml", "w") as f:
        yaml.dump(config_yaml, f)

    res = validate_config()

    assert res["agent.provider"] == "missing"
    assert res["autonomy.autopilot"] == "missing"

def test_validate_config_wrong_type(mock_fs):
    root_dir, config_dir, workspace_dir, logs_dir = mock_fs

    config_yaml = {
        "agent": {
            "provider": "ollama",
            "workspace": str(workspace_dir),
            "stream": "yes" # wrong type
        },
        "autonomy": {
            "autopilot": "on" # wrong type
        }
    }

    with open(root_dir / "config.yaml", "w") as f:
        yaml.dump(config_yaml, f)

    res = validate_config()

    assert res["agent.stream"] == "wrong_type"
    assert res["autonomy.autopilot"] == "wrong_type"

def test_validate_config_invalid_provider(mock_fs):
    root_dir, config_dir, workspace_dir, logs_dir = mock_fs

    config_yaml = {
        "agent": {
            "provider": "openai", # invalid value
            "workspace": str(workspace_dir),
        },
        "autonomy": {
            "autopilot": True
        }
    }

    with open(root_dir / "config.yaml", "w") as f:
        yaml.dump(config_yaml, f)

    res = validate_config()

    assert res["agent.provider"] == "invalid_value"

def test_validate_config_non_writable_workspace(mock_fs, monkeypatch):
    root_dir, config_dir, workspace_dir, logs_dir = mock_fs

    config_yaml = {
        "agent": {
            "provider": "ollama",
            "workspace": "/root/forbidden/path",
        },
        "autonomy": {
            "autopilot": True
        }
    }

    with open(root_dir / "config.yaml", "w") as f:
        yaml.dump(config_yaml, f)

    # Define a custom Path object instead of modifying __class__ on PosixPath
    class FailingPath(type(Path())):
        def touch(self, *args, **kwargs):
            if "/root/forbidden/path" in str(self):
                raise PermissionError("Permission denied")
            super().touch(*args, **kwargs)

    original_path = Path

    class MockPathWriteFail(type(Path())):
        def __new__(cls, *args, **kwargs):
            if args and str(args[0]) == "/root/forbidden/path":
                 return FailingPath(*args, **kwargs)
            elif args and str(args[0]) == ".":
                 return original_path(str(root_dir))
            elif args and str(args[0]) == "config":
                 return original_path(str(config_dir))
            elif args and str(args[0]) == "config.yaml":
                 return original_path(str(root_dir / "config.yaml"))
            elif args and str(args[0]) == "workspace/daily_logs":
                 return original_path(str(logs_dir))
            return original_path(*args, **kwargs)

    monkeypatch.setattr("tools.plugins.config_validator.Path", MockPathWriteFail)

    res = validate_config()
    assert res["agent.workspace"] == "not_writable"

def test_validate_config_missing_yaml(mock_fs):
    # Don't create config.yaml
    res = validate_config()
    assert res == "Error: config.yaml is missing."
