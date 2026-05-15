import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime_config import load_config
from core.tool_registry import ToolRegistry
from tools.screen_tools import ScreenManager


def test_screen_perception_tools_are_registered():
    registry = ToolRegistry(load_config())

    for name in [
        "screen_screenshot",
        "screen_observe",
        "screen_screenshot_with_cursor",
        "screen_size",
        "mouse_position",
        "active_window_info",
        "ui_tree",
        "active_window_elements",
        "virtual_cursor_position",
        "virtual_cursor_move",
        "screen_ocr",
        "screen_find_text",
        "screen_find_image",
    ]:
        assert name in registry.registry


def test_screen_find_text_requires_query(tmp_path):
    manager = ScreenManager(base_dir=str(tmp_path))

    assert manager.screen_find_text("").startswith("Error: text required")


def test_virtual_cursor_moves_without_real_mouse(tmp_path):
    manager = ScreenManager(base_dir=str(tmp_path))

    manager.virtual_cursor_move(123, 456)

    assert '"x": 123' in manager.virtual_cursor_position()
    assert '"y": 456' in manager.virtual_cursor_position()


def test_mouse_drag_tool_is_registered():
    registry = ToolRegistry(load_config())

    assert "mouse_drag" in registry.registry


def test_uia_script_includes_text_pattern_extraction(tmp_path):
    manager = ScreenManager(base_dir=str(tmp_path))
    script = manager._uia_script("$null", 1)

    assert "ValuePattern" in script
    assert "TextPattern" in script
    assert "text = $textSample" in script
