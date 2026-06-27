"""Unit spec for the /zone CLI command."""

from unittest.mock import MagicMock, patch, mock_open
from kernel.cli import CLI
from kernel.version import DEFAULT_VERSION


# ── Shared fixture helpers ─────────────────────────────────────────────────────

def _make_cli(enabled: bool = True, require_hitm: bool = True, read_only: bool = False):
    """Build a minimal CLI instance with a mocked agent/guard."""
    cli = CLI.__new__(CLI)

    # Minimal cfg so CLI.__init__ is bypassed
    cli.cfg = {
        "agent": {"provider": "ollama", "workspace": "workspace"},
        "prompts": {},
    }
    cli.running = True
    cli.dry_run = False

    # Create a mock PathGuard that tracks attribute mutations
    mock_guard = MagicMock()
    mock_guard.enabled = enabled
    mock_guard.require_hitm = require_hitm
    mock_guard.read_only = read_only

    # Wire the guard into a mock agent / ops
    mock_ops = MagicMock()
    mock_ops.guard = mock_guard
    cli.agent = MagicMock()
    cli.agent.ops = mock_ops

    return cli, mock_guard


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_zone_switch_green_to_yellow():
    """'/zone yellow' from green → switches to yellow (enabled, no hitm)."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone yellow")

    assert guard.enabled is True
    assert guard.require_hitm is False


def test_zone_switch_yellow_to_red():
    """'/zone red' from yellow → red (disabled)."""
    cli, guard = _make_cli(enabled=True, require_hitm=False)
    cli.handle_command("/zone red")

    assert guard.enabled is False
    assert guard.require_hitm is False


def test_zone_switch_red_to_blue():
    """'/zone blue' from red → blue (read-only)."""
    cli, guard = _make_cli(enabled=False, require_hitm=False, read_only=False)
    cli.handle_command("/zone blue")

    assert guard.enabled is True
    assert guard.require_hitm is False
    assert guard.read_only is True


def test_zone_switch_blue_to_green():
    """'/zone green' from blue wraps back to green."""
    cli, guard = _make_cli(enabled=True, require_hitm=False, read_only=True)
    cli.handle_command("/zone green")

    assert guard.enabled is True
    assert guard.require_hitm is True
    assert guard.read_only is False


def test_zone_no_arg_does_not_change_guard():
    """'/zone' with no argument shows status and does NOT modify the guard."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone")

    # Guard must be completely untouched
    assert guard.enabled is True
    assert guard.require_hitm is True


def test_zone_direct_switch_to_green():
    """'/zone green' switches directly to green regardless of current state."""
    cli, guard = _make_cli(enabled=False, require_hitm=False)
    cli.handle_command("/zone green")

    assert guard.enabled is True
    assert guard.require_hitm is True


def test_zone_direct_switch_to_yellow():
    """'/zone yellow' switches directly to yellow."""
    cli, guard = _make_cli(enabled=False, require_hitm=False)
    cli.handle_command("/zone yellow")

    assert guard.enabled is True
    assert guard.require_hitm is False


def test_zone_direct_switch_to_red():
    """'/zone red' disables PathGuard entirely."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone red")

    assert guard.enabled is False
    assert guard.require_hitm is False


def test_zone_numeric_alias_1_red():
    """'/zone 1' is an alias for red."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone 1")

    assert guard.enabled is False
    assert guard.require_hitm is False


def test_zone_numeric_alias_2_green():
    """'/zone 2' is an alias for green."""
    cli, guard = _make_cli(enabled=False, require_hitm=False)
    cli.handle_command("/zone 2")

    assert guard.enabled is True
    assert guard.require_hitm is True


def test_zone_numeric_alias_3_yellow():
    """'/zone 3' is an alias for yellow."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone 3")

    assert guard.enabled is True
    assert guard.require_hitm is False


def test_zone_direct_switch_to_black():
    """'/zone black' disables PathGuard and all security (god mode)."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone black")

    assert guard.enabled is False
    assert guard.require_hitm is False
    assert guard.zone_name == "black"


def test_zone_numeric_alias_5_black():
    """'/zone 5' is an alias for black."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone 5")

    assert guard.enabled is False
    assert guard.require_hitm is False
    assert guard.zone_name == "black"


def test_zone_switch_black_to_green():
    """'/zone green' from black restores full security."""
    cli, guard = _make_cli(enabled=False, require_hitm=False)
    guard.zone_name = "black"
    cli.handle_command("/zone green")

    assert guard.enabled is True
    assert guard.require_hitm is True
    assert guard.zone_name == "green"


def test_zone_invalid_argument_does_not_change_guard():
    """Invalid zone name should not modify the guard state."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)

    # Record state before
    original_enabled = guard.enabled
    original_hitm = guard.require_hitm

    cli.handle_command("/zone purple")

    # Guard should be completely untouched
    assert guard.enabled == original_enabled
    assert guard.require_hitm == original_hitm


def test_zone_no_guard_does_not_crash():
    """If ops.guard is None, the command prints an error but doesn't crash."""
    cli, _guard = _make_cli()
    cli.agent.ops.guard = None  # Simulate missing guard

    # Should not raise
    cli.handle_command("/zone")


# ── Blue Zone CLI command spec ────────────────────────────────────────────────

def test_zone_direct_switch_to_blue():
    """'/zone blue' enables read_only and keeps PathGuard active."""
    cli, guard = _make_cli(enabled=False, require_hitm=True, read_only=False)
    cli.handle_command("/zone blue")

    assert guard.enabled is True
    assert guard.require_hitm is False
    assert guard.read_only is True


def test_zone_numeric_alias_4_blue():
    """'/zone 4' is an alias for blue."""
    cli, guard = _make_cli(enabled=True, require_hitm=True, read_only=False)
    cli.handle_command("/zone 4")

    assert guard.enabled is True
    assert guard.read_only is True
    assert guard.require_hitm is False


def test_zone_switch_from_blue_to_green_directly():
    """Direct '/zone green' from blue clears read_only and sets HITM."""
    cli, guard = _make_cli(enabled=True, require_hitm=False, read_only=True)
    cli.handle_command("/zone green")

    assert guard.enabled is True
    assert guard.require_hitm is True
    assert guard.read_only is False


def test_zone_green_to_yellow_clears_read_only():
    """Switching from green to yellow must set read_only=False."""
    cli, guard = _make_cli(enabled=True, require_hitm=True, read_only=False)
    cli.handle_command("/zone yellow")

    assert guard.read_only is False
    assert guard.require_hitm is False


def test_zone_red_does_not_set_read_only():
    """Red zone disables the guard entirely and must NOT set read_only."""
    cli, guard = _make_cli(enabled=True, require_hitm=True, read_only=False)
    cli.handle_command("/zone red")

    assert guard.enabled is False
    assert guard.read_only is False


# ── Config CLI command spec ──────────────────────────────────────────────────

@patch("os.path.exists")
@patch("os.startfile", create=True)
def test_cfg_cmd_windows(mock_startfile, mock_exists):
    """/cfg command on Windows invokes os.startfile."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    with patch("sys.platform", "win32"):
        cli.handle_command("/cfg")

    mock_exists.assert_called_once()
    mock_startfile.assert_called_once()


@patch("os.path.exists")
@patch("subprocess.Popen")
def test_cfg_cmd_darwin(mock_popen, mock_exists):
    """/cfg command on macOS (darwin) invokes open via subprocess."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    with patch("sys.platform", "darwin"):
        cli.handle_command("/cfg")

    mock_exists.assert_called_once()
    mock_popen.assert_called_once_with(["open", unittest_cfg_dir_match()])


@patch("os.path.exists")
@patch("subprocess.Popen")
def test_cfg_cmd_linux(mock_popen, mock_exists):
    """/cfg command on Linux invokes xdg-open via subprocess."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    with patch("sys.platform", "linux"):
        cli.handle_command("/cfg")

    mock_exists.assert_called_once()
    mock_popen.assert_called_once_with(["xdg-open", unittest_cfg_dir_match()])


@patch("os.path.exists")
@patch("kernel.cli.print_error")
def test_cfg_cmd_not_exists(mock_print_error, mock_exists):
    """/cfg command prints an error if the directory does not exist."""
    cli, _ = _make_cli()
    mock_exists.return_value = False

    cli.handle_command("/cfg")

    mock_exists.assert_called_once()
    mock_print_error.assert_called_once()


class unittest_cfg_dir_match:
    """Helper to check if a path matches cfg_dir."""
    def __eq__(self, other):
        return isinstance(other, str) and other.endswith("cfg")


# ── Version CLI command spec ─────────────────────────────────────────────────

@patch("os.path.exists")
@patch("kernel.cli.logger.info")
def test_version_cmd_dynamic_parsing(mock_logger_info, mock_exists):
    """/version command dynamically parses version from CHANGELOG.md."""
    cli, _ = _make_cli()
    cli.agent.client.provider = "test_provider"
    cli.agent.client.model = "test_model"

    mock_exists.return_value = True

    mock_content = "## [9.9.9] - 2026-12-31\n### New Features\n..."
    with patch("builtins.open", mock_open(read_data=mock_content)):
        cli.handle_command("/version")

    called_with_version = False
    for call in mock_logger_info.call_args_list:
        msg = call[0][0]
        if "AgenticOs v9.9.9" in msg:
            called_with_version = True
            break
    assert called_with_version is True


@patch("os.path.exists")
@patch("kernel.cli.logger.info")
def test_version_cmd_fallback(mock_logger_info, mock_exists):
    """/version command falls back to default version if CHANGELOG.md is missing."""
    cli, _ = _make_cli()
    cli.agent.client.provider = "test_provider"
    cli.agent.client.model = "test_model"

    mock_exists.return_value = False

    cli.handle_command("/version")

    called_with_version = False
    for call in mock_logger_info.call_args_list:
        msg = call[0][0]
        if f"AgenticOs v{DEFAULT_VERSION}" in msg:
            called_with_version = True
            break
    assert called_with_version is True


@patch("os.path.exists")
@patch("os.startfile", side_effect=OSError("Access denied"), create=True)
@patch("kernel.cli.print_error")
def test_cfg_cmd_windows_error(mock_print_error, mock_startfile, mock_exists):
    """/cfg command logs error if explorer fails to open on Windows."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    with patch("sys.platform", "win32"):
        cli.handle_command("/cfg")

    mock_exists.assert_called_once()
    mock_startfile.assert_called_once()
    mock_print_error.assert_called_once()


@patch("os.path.exists")
@patch("kernel.cli.logger.info")
def test_version_cmd_invalid_format(mock_logger_info, mock_exists):
    """/version command falls back to default version if CHANGELOG.md contains invalid header formatting."""
    cli, _ = _make_cli()
    cli.agent.client.provider = "test_provider"
    cli.agent.client.model = "test_model"

    mock_exists.return_value = True

    mock_content = "## [NotAVersion] - 2026-12-31\n### New Features\n..."
    with patch("builtins.open", mock_open(read_data=mock_content)):
        cli.handle_command("/version")

    called_with_version = False
    for call in mock_logger_info.call_args_list:
        msg = call[0][0]
        if f"AgenticOs v{DEFAULT_VERSION}" in msg:
            called_with_version = True
            break
    assert called_with_version is True


# ── Logs CLI command spec ───────────────────────────────────────────────────

@patch("os.path.exists")
@patch("os.startfile", create=True)
def test_logs_cmd_folder_exists_windows(mock_startfile, mock_exists):
    """/logs command opens logs folder on Windows if it exists."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    with patch("sys.platform", "win32"):
        cli.handle_command("/logs")

    mock_exists.assert_called_once()
    mock_startfile.assert_called_once()


@patch("os.path.exists")
@patch("kernel.cli.print_error")
def test_logs_cmd_folder_not_exists(mock_print_error, mock_exists):
    """/logs command prints error if logs folder does not exist."""
    cli, _ = _make_cli()
    mock_exists.return_value = False

    cli.handle_command("/logs")

    mock_exists.assert_called_once()
    mock_print_error.assert_called_once()


@patch("os.path.exists")
@patch("builtins.print")
def test_logs_cmd_tail(mock_print, mock_exists):
    """/logs tail command reads logs file and prints the last lines."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    mock_content = "Line 1\nLine 2\nLine 3\n"
    with patch("builtins.open", mock_open(read_data=mock_content)):
        cli.handle_command("/logs tail")

    print_calls = [call[0][0] for call in mock_print.call_args_list]
    assert any("Line 1" in str(c) for c in print_calls)
    assert any("Line 2" in str(c) for c in print_calls)
    assert any("Line 3" in str(c) for c in print_calls)


@patch("os.path.exists")
@patch("os.walk")
@patch("os.path.getsize")
@patch("os.path.getmtime")
@patch("kernel.cli.logger")
def test_logs_cmd_list(mock_logger, mock_getmtime, mock_getsize, mock_walk, mock_exists):
    """/logs list command prints available log and memory files."""
    cli, _ = _make_cli()
    mock_exists.return_value = True
    
    mock_walk.side_effect = [
        [("/path/to/logs", [], ["agenticos.log"])],
        [("/path/to/memory", [], ["MEMORY.md"])]
    ]
    mock_getsize.return_value = 1024
    mock_getmtime.return_value = 1779450364.0
    
    cli.handle_command("/logs list")
    
    log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
    assert any("AGENTIC OS" in str(c) for c in log_calls)
    assert any("agenticos.log" in str(c) for c in log_calls)
    assert any("MEMORY.md" in str(c) for c in log_calls)


@patch("os.path.exists")
@patch("builtins.print")
def test_logs_cmd_tail_specific_file(mock_print, mock_exists):
    """/logs tail [file] [n] reads a specific log file and prints it."""
    cli, _ = _make_cli()
    mock_exists.return_value = True
    
    mock_content = "Log Item 1\nLog Item 2\nLog Item 3\nLog Item 4\nLog Item 5\n"
    with patch("builtins.open", mock_open(read_data=mock_content)):
        cli.handle_command("/logs tail memory/MEMORY.md 3")
        
    print_calls = [call[0][0] for call in mock_print.call_args_list]
    assert any("Log Item 3" in str(c) for c in print_calls)
    assert any("Log Item 4" in str(c) for c in print_calls)
    assert any("Log Item 5" in str(c) for c in print_calls)
    assert not any("Log Item 1" in str(c) for c in print_calls)


@patch("os.path.exists")
@patch("builtins.print")
def test_logs_cmd_view(mock_print, mock_exists):
    """/logs view [file] [n] reads and colorizes the beginning of a log file."""
    cli, _ = _make_cli()
    mock_exists.return_value = True
    
    mock_content = "First line OK\nSecond line completed\nThird line failed\n"
    with patch("builtins.open", mock_open(read_data=mock_content)):
        cli.handle_command("/logs view agenticos.log 2")
        
    import re
    def strip_ansi(text):
        return re.sub(r"\033\[[0-9;]*m", "", text)
        
    print_calls = [strip_ansi(str(call[0][0])) for call in mock_print.call_args_list]
    assert any("1 │ First line" in c for c in print_calls)
    assert any("2 │ Second line" in c for c in print_calls)
    assert not any("Third line" in c for c in print_calls)


def test_zone_guard_persists_on_reload():
    """Verify that re-running _setup_workspace preserves the active zone settings instead of resetting them."""
    from kernel.agent import Agent
    cfg = {
        "agent": {"provider": "ollama", "workspace": "workspace", "max_iterations": 10},
        "prompts": {},
        "security": {"enable_zone_guard": True, "require_hitm_outside_workspace": True}
    }
    
    agent = Agent.__new__(Agent)
    agent.cfg = cfg
    agent.confirm_handler = None
    agent.workspace = "workspace"
    
    with patch("kernel.cli.SqliteSessionMemory"), patch("kernel.cli.ToolRegistry") as mock_registry_cls:
        mock_registry = MagicMock()
        mock_guard = MagicMock()
        mock_guard.enabled = True
        mock_guard.require_hitm = True
        mock_guard.read_only = False
        mock_registry.guard = mock_guard
        mock_registry_cls.return_value = mock_registry
        
        agent._setup_workspace()
        
        # Change zone state (e.g. switch to red zone: enabled=False)
        agent.ops.guard.enabled = False
        agent.ops.guard.require_hitm = False
        
        # Run setup workspace again (simulating cfg/hot reload)
        new_registry = MagicMock()
        new_guard = MagicMock()
        new_guard.enabled = True  # Default from cfg
        new_guard.require_hitm = True
        new_guard.read_only = False
        new_registry.guard = new_guard
        mock_registry_cls.return_value = new_registry
        
        agent._setup_workspace()
        
        # The new guard should have been restored with the changed values (enabled=False, require_hitm=False)
        assert agent.ops.guard.enabled is False
        assert agent.ops.guard.require_hitm is False


