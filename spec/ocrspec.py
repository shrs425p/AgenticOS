import pytest
import os
from unittest.mock import MagicMock, patch
from ops.ocr import OCRManager

@pytest.fixture
def ocr_manager():
    rules = {"allow_reserved_path_patterns": True}
    cfg = {"media": {"ocr_engine": "auto"}}
    mgr = OCRManager(rules=rules, base_dir="workspace", cfg=cfg)
    mgr.has_tesseract = False # Default to false for deterministic testing
    return mgr

def test_ocrimage_missing_file(ocr_manager):
    # Ensure native OCR is used
    res = ocr_manager.ocrimage("non_existent.png", engine="native")
    assert "Error: Image file not found" in res

@patch("subprocess.Popen")
@patch("os.path.exists")
def test_ocrimage_native_success(mock_exists, mock_popen, ocr_manager):
    mock_exists.return_value = True
    
    # Mock subprocess to return "Sample OCR Text"
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("Sample OCR Text", "")
    mock_process.returncode = 0
    mock_popen.return_value = mock_process
    
    # Force native engine
    res = ocr_manager.ocrimage("test_image.png", engine="native")
    assert res == "Sample OCR Text"

@patch("os.path.exists")
def test_ocrscreen_logic(mock_exists, ocr_manager):
    mock_exists.return_value = True
    
    # Mock registry and screen tool
    mock_registry = MagicMock()
    # Use os.path.join to build cross-platform paths instead of hardcoding Windows paths
    screenshot_path = os.path.join("path", "to", "shot.png")
    mock_registry.screen.takescreenshot.return_value = f"Screenshot saved: {screenshot_path}"
    ocr_manager.registry = mock_registry
    
    # Mock ocrimage to return text
    ocr_manager.ocrimage = MagicMock(return_value="Extracted Screen Text")
    
    res = ocr_manager.ocrscreen()
    
    mock_registry.screen.takescreenshot.assert_called_once()
    ocr_manager.ocrimage.assert_called_with(screenshot_path, engine="auto")
    assert res == "Extracted Screen Text"

@patch("subprocess.run")
@patch("os.path.exists")
def test_tesseract_success(mock_exists, mock_run, ocr_manager):
    mock_exists.return_value = True
    ocr_manager.has_tesseract = True
    
    mock_result = MagicMock()
    mock_result.stdout = "Tesseract Text Output"
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    res = ocr_manager.ocrimage("test.png", engine="tesseract")
    assert res == "Tesseract Text Output"
    mock_run.assert_called_once()
