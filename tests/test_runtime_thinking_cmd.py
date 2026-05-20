import pytest
from core.runtime import CLI

def test_thinking_command_toggle():
    cli = CLI.__new__(CLI)
    cli.cfg = {
        "agent": {"provider": "ollama", "workspace": "workspace", "verbose_thinking": False},
        "prompts": {},
    }
    cli.running = True
    cli.verbose = False

    # Toggle from False to True
    cli.handle_command("/thinking")
    assert cli.cfg["agent"]["verbose_thinking"] is True
    assert cli.verbose is True

    # Toggle from True to False
    cli.handle_command("/thinking")
    assert cli.cfg["agent"]["verbose_thinking"] is False
    assert cli.verbose is False

    # Set explicitly via argument "show"
    cli.handle_command("/thinking show")
    assert cli.cfg["agent"]["verbose_thinking"] is True

    # Set explicitly via argument "hide"
    cli.handle_command("/thinking hide")
    assert cli.cfg["agent"]["verbose_thinking"] is False

    # Set explicitly via argument "on"
    cli.handle_command("/thinking on")
    assert cli.cfg["agent"]["verbose_thinking"] is True

    # Set explicitly via argument "off"
    cli.handle_command("/thinking off")
    assert cli.cfg["agent"]["verbose_thinking"] is False

