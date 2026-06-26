"""Unit spec for the image ops plugin."""

import os
import json
import pytest
import tempfile
from PIL import Image

from ops.addons.image import (
    imagegetmetadata,
    imageconvertformat,
    imageresize,
    HAS_PILLOW
)


@pytest.fixture
def temp_image():
    """Fixture to create a temporary dummy PNG image."""
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    
    # Create a 100x100 solid blue PNG image
    img = Image.new("RGBA", (100, 100), color=(0, 0, 255, 255))
    img.save(path)
    
    yield path
    
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def temp_output():
    """Fixture for a temporary output path."""
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    
    yield path
    
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow is not installed")
def test_imagegetmetadata(temp_image):
    result = imagegetmetadata(temp_image)
    
    # Should return valid JSON string with width/height 100
    assert "Error" not in result
    data = json.loads(result)
    assert data["width"] == 100
    assert data["height"] == 100
    assert data["format"] == "PNG"


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow is not installed")
def test_imagegetmetadata_not_found():
    result = imagegetmetadata("nonexistent_image_path.jpg")
    assert "Error: Image file not found" in result


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow is not installed")
def test_imageconvertformat(temp_image, temp_output):
    # Convert RGBA PNG -> RGB JPG
    result = imageconvertformat(temp_image, temp_output)
    assert "Success" in result
    
    # Verify the output is valid
    with Image.open(temp_output) as img:
        assert img.format == "JPEG"
        assert img.mode == "RGB"
        assert img.size == (100, 100)


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow is not installed")
def test_imageresize_exact(temp_image, temp_output):
    # Resize to exact dimensions (200x50)
    result = imageresize(temp_image, temp_output, width=200, height=50)
    assert "Success" in result
    
    with Image.open(temp_output) as img:
        assert img.size == (200, 50)


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow is not installed")
def test_imageresize_scale(temp_image, temp_output):
    # Scale by 50%
    result = imageresize(temp_image, temp_output, scale=0.5)
    assert "Success" in result
    
    with Image.open(temp_output) as img:
        assert img.size == (50, 50)


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow is not installed")
def test_imageresize_aspect_ratio(temp_image, temp_output):
    # Provide only width (250). Since orig is 100x100, height should be 250 too
    result = imageresize(temp_image, temp_output, width=250)
    assert "Success" in result
    
    with Image.open(temp_output) as img:
        assert img.size == (250, 250)


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow is not installed")
def test_imageresize_no_args(temp_image, temp_output):
    # Should error if no resize criteria provided
    result = imageresize(temp_image, temp_output)
    assert "Error: You must provide either width, height, or a positive scale." in result
