"""Unit tests for the Multi-Modal Visual Coordinate Mapping Engine."""
from unittest.mock import MagicMock, patch

from tools.plugins.vision_coordinator import _extract_word_boxes, _find_phrase_coords, click_element_by_name, drag_and_drop_visual

def test_find_phrase_coords():
    # Setup test words database
    words = [
        {"text": "File", "x": 10, "y": 20, "w": 40, "h": 20},
        {"text": "Edit", "x": 60, "y": 20, "w": 40, "h": 20},
        {"text": "Google", "x": 100, "y": 100, "w": 50, "h": 30},
        {"text": "Chrome", "x": 160, "y": 100, "w": 60, "h": 30},
    ]

    # 1. Exact Match Single Token
    coords = _find_phrase_coords("File", words)
    assert coords == (30, 30) # center of (10, 20, 40, 20) is (30, 30)

    # 2. Sequence Match Multi-Token
    coords = _find_phrase_coords("Google Chrome", words)
    assert coords == (160, 115) # min_x=100, max_x=220 -> cx=160; min_y=100, max_y=130 -> cy=115

    # 3. Fuzzy case-insensitive Match
    coords = _find_phrase_coords("chrome", words)
    assert coords == (190, 115) # center of (160, 100, 60, 30) is (190, 115)

    # 4. No Match
    coords = _find_phrase_coords("Missing", words)
    assert coords is None

def test_extract_word_boxes_win():
    # Mock WinRT OCR response
    with patch("platform.system", return_value="Windows"), \
         patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.communicate.return_value = (
            "File|10|20|40|20\nEdit|60|20|40|20",
            ""
        )
        mock_popen.return_value = mock_process

        words = _extract_word_boxes("dummy_screenshot.png")
        assert len(words) == 2
        assert words[0]["text"] == "File"
        assert words[0]["x"] == 10
        assert words[0]["y"] == 20

def test_extract_word_boxes_tesseract():
    # Mock Tesseract TSV response
    with patch("platform.system", return_value="Linux"), \
         patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "left\ttop\twidth\theight\ttext\n10\t20\t40\t20\tFile\n60\t20\t40\t20\tEdit"
        mock_run.return_value = mock_res

        words = _extract_word_boxes("dummy_screenshot.png")
        assert len(words) == 2
        assert words[0]["text"] == "File"
        assert words[0]["x"] == 10

def test_click_element_by_name_success():
    with patch("tools.plugins.vision_coordinator._extract_word_boxes") as mock_extract, \
         patch("tools.screen_tools.ScreenManager.take_screenshot", return_value="Screenshot saved: dummy.png"), \
         patch("os.path.exists", return_value=True), \
         patch("tools.terminal.TerminalExecutor.mouse_click", return_value="Clicked left at (30, 30).") as mock_click:
        mock_extract.return_value = [
            {"text": "File", "x": 10, "y": 20, "w": 40, "h": 20}
        ]

        res = click_element_by_name("File")
        assert "Success" in res
        assert "(30, 30)" in res
        mock_click.assert_called_once_with(button="left", x=30, y=30)

def test_drag_and_drop_visual_win():
    with patch("tools.plugins.vision_coordinator._extract_word_boxes") as mock_extract, \
         patch("tools.screen_tools.ScreenManager.take_screenshot", return_value="Screenshot saved: dummy.png"), \
         patch("os.path.exists", return_value=True), \
         patch("platform.system", return_value="Windows"), \
         patch("subprocess.run") as mock_run:
        mock_extract.return_value = [
            {"text": "Source", "x": 10, "y": 20, "w": 40, "h": 20},
            {"text": "Dest", "x": 100, "y": 200, "w": 40, "h": 20}
        ]

        res = drag_and_drop_visual("Source", "Dest")
        assert "Success" in res
        mock_run.assert_called_once()
