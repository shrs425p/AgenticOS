import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.terminal_tools import TerminalExecutor


def test_mouse_control_can_be_disabled_by_config():
    term = TerminalExecutor(rules={"allow_mouse_control": False})

    assert "disabled by config" in term.mouse_move(10, 10)


def test_blocked_click_region_blocks_clicks():
    term = TerminalExecutor(
        rules={
            "blocked_click_regions": [
                {"x": 0, "y": 0, "width": 100, "height": 100, "name": "test-zone"}
            ]
        }
    )

    assert "test-zone" in term.mouse_click("left", 50, 50)


def test_safe_region_blocks_outside_coordinates():
    term = TerminalExecutor(
        rules={"mouse_safe_regions": [{"x": 10, "y": 10, "width": 20, "height": 20}]}
    )

    assert "outside configured mouse_safe_regions" in term.mouse_drag(0, 0, 15, 15)
