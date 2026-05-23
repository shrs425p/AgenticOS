"""Unit tests for the /zone CLI command."""

from unittest.mock import MagicMock, patch, mock_open
from core.runtime import CLI


# ── Shared fixture helpers ─────────────────────────────────────────────────────

def _make_cli(enabled: bool = True, require_hitm: bool = True, read_only: bool = False):
    """Build a minimal CLI instance with a mocked agent/guard."""
    cli = CLI.__new__(CLI)

    # Minimal config so CLI.__init__ is bypassed
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

    # Wire the guard into a mock agent / tools
    mock_tools = MagicMock()
    mock_tools.guard = mock_guard
    cli.agent = MagicMock()
    cli.agent.tools = mock_tools

    return cli, mock_guard


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_zone_toggle_green_to_yellow():
    """Starting at green (enabled+hitm) → toggle → yellow (enabled, no hitm)."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone")

    assert guard.enabled is True
    assert guard.require_hitm is False


def test_zone_toggle_yellow_to_red():
    """Starting at yellow (enabled, no hitm) → toggle → red (disabled)."""
    cli, guard = _make_cli(enabled=True, require_hitm=False)
    cli.handle_command("/zone")

    assert guard.enabled is False
    assert guard.require_hitm is False


def test_zone_toggle_red_to_blue():
    """Starting at red (disabled) → toggle → blue (read-only)."""
    cli, guard = _make_cli(enabled=False, require_hitm=False, read_only=False)
    cli.handle_command("/zone")

    assert guard.enabled is True
    assert guard.require_hitm is False
    assert guard.read_only is True


def test_zone_toggle_blue_to_green():
    """Starting at blue (read_only) → toggle wraps back to green."""
    cli, guard = _make_cli(enabled=True, require_hitm=False, read_only=True)
    cli.handle_command("/zone")

    assert guard.enabled is True
    assert guard.require_hitm is True
    assert guard.read_only is False


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


def test_zone_numeric_alias_1_green():
    """'/zone 1' is an alias for green."""
    cli, guard = _make_cli(enabled=False, require_hitm=False)
    cli.handle_command("/zone 1")

    assert guard.enabled is True
    assert guard.require_hitm is True


def test_zone_numeric_alias_2_yellow():
    """'/zone 2' is an alias for yellow."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone 2")

    assert guard.enabled is True
    assert guard.require_hitm is False


def test_zone_numeric_alias_3_red():
    """'/zone 3' is an alias for red."""
    cli, guard = _make_cli(enabled=True, require_hitm=True)
    cli.handle_command("/zone 3")

    assert guard.enabled is False
    assert guard.require_hitm is False


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
    """If tools.guard is None, the command prints an error but doesn't crash."""
    cli, _guard = _make_cli()
    cli.agent.tools.guard = None  # Simulate missing guard

    # Should not raise
    cli.handle_command("/zone")


# ── Blue Zone CLI command tests ────────────────────────────────────────────────

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


# ── Config CLI command tests ──────────────────────────────────────────────────

@patch("os.path.exists")
@patch("os.startfile", create=True)
def test_config_cmd_windows(mock_startfile, mock_exists):
    """/config command on Windows invokes os.startfile."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    with patch("sys.platform", "win32"):
        cli.handle_command("/config")

    mock_exists.assert_called_once()
    mock_startfile.assert_called_once()


@patch("os.path.exists")
@patch("subprocess.Popen")
def test_config_cmd_darwin(mock_popen, mock_exists):
    """/config command on macOS (darwin) invokes open via subprocess."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    with patch("sys.platform", "darwin"):
        cli.handle_command("/config")

    mock_exists.assert_called_once()
    mock_popen.assert_called_once_with(["open", unittest_config_dir_match()])


@patch("os.path.exists")
@patch("subprocess.Popen")
def test_config_cmd_linux(mock_popen, mock_exists):
    """/config command on Linux invokes xdg-open via subprocess."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    with patch("sys.platform", "linux"):
        cli.handle_command("/config")

    mock_exists.assert_called_once()
    mock_popen.assert_called_once_with(["xdg-open", unittest_config_dir_match()])


@patch("os.path.exists")
@patch("core.runtime.print_error")
def test_config_cmd_not_exists(mock_print_error, mock_exists):
    """/config command prints an error if the directory does not exist."""
    cli, _ = _make_cli()
    mock_exists.return_value = False

    cli.handle_command("/config")

    mock_exists.assert_called_once()
    mock_print_error.assert_called_once()


class unittest_config_dir_match:
    """Helper to check if a path matches config_dir."""
    def __eq__(self, other):
        return isinstance(other, str) and other.endswith("config")


# ── Version CLI command tests ─────────────────────────────────────────────────

@patch("os.path.exists")
@patch("core.runtime.logger.info")
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
@patch("core.runtime.logger.info")
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
        if "AgenticOs v2.1.1" in msg:
            called_with_version = True
            break
    assert called_with_version is True


@patch("os.path.exists")
@patch("os.startfile", side_effect=OSError("Access denied"), create=True)
@patch("core.runtime.print_error")
def test_config_cmd_windows_error(mock_print_error, mock_startfile, mock_exists):
    """/config command logs error if explorer fails to open on Windows."""
    cli, _ = _make_cli()
    mock_exists.return_value = True

    with patch("sys.platform", "win32"):
        cli.handle_command("/config")

    mock_exists.assert_called_once()
    mock_startfile.assert_called_once()
    mock_print_error.assert_called_once()


@patch("os.path.exists")
@patch("core.runtime.logger.info")
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
        if "AgenticOs v2.1.1" in msg:
            called_with_version = True
            break
    assert called_with_version is True


# ── Logs CLI command tests ───────────────────────────────────────────────────

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
@patch("core.runtime.print_error")
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
@patch("core.runtime.logger")
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

