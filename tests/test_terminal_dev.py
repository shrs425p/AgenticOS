import pytest
from unittest import mock
from tools.terminal.dev import DevToolsMixin

class MockDevTools(DevToolsMixin):
    def __init__(self):
        self.ran_cmds = []

    def _run(self, cmd: str, timeout: int = 60) -> str:
        self.ran_cmds.append((cmd, timeout))
        return f"Executed: {cmd}"

    def _quote_arg(self, arg: str) -> str:
        return f'"{arg}"'

def test_pip_install():
    tool = MockDevTools()
    res = tool.pip_install("requests")
    assert "pip install requests" in res
    assert tool.ran_cmds == [("pip install requests", 600)]

def test_pip_list():
    tool = MockDevTools()
    res = tool.pip_list()
    assert "pip list" in res
    assert tool.ran_cmds == [("pip list", 120)]

def test_npm_install():
    tool = MockDevTools()
    res_local = tool.npm_install("express")
    assert "npm install express" in res_local
    
    res_global = tool.npm_install("express", global_flag="true")
    assert "npm install -g express" in res_global
    
    assert tool.ran_cmds == [
        ("npm install express", 600),
        ("npm install -g express", 600)
    ]

def test_git():
    tool = MockDevTools()
    res = tool.git("commit", "-m", "hello")
    assert "git commit -m hello" in res
    assert tool.ran_cmds == [("git commit -m hello", 120)]

def test_git_status():
    tool = MockDevTools()
    res = tool.git_status("my_dir")
    assert 'git -C "my_dir" status' in res
    assert tool.ran_cmds == [('git -C "my_dir" status', 60)]

def test_git_log():
    tool = MockDevTools()
    # Standard call
    res = tool.git_log("my_dir", "5")
    assert 'git -C "my_dir" log -n 5 --oneline' in res
    
    # Non-integer fallback
    res_fallback = tool.git_log("my_dir", "invalid")
    assert 'git -C "my_dir" log -n 10 --oneline' in res_fallback
    
    assert tool.ran_cmds == [
        ('git -C "my_dir" log -n 5 --oneline', 60),
        ('git -C "my_dir" log -n 10 --oneline', 60)
    ]
