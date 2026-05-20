"""Image Processing Plugin using Pillow."""

from __future__ import annotations

import os
import json
from typing import Any, Dict

from core.tool_registry import tool

try:
    from PIL import Image, ExifTags
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


@tool(name="image_get_metadata", category="Image", desc="Get image dimensions, format, mode and EXIF data.")
def image_get_metadata(image_path: str) -> str:
    """Reads basic properties and EXIF metadata from an image.

    Args:
        image_path: Absolute or relative path to the image file.
    """
    if not HAS_PILLOW:
        return "Error: Pillow library is not installed. Add Pillow to requirements.txt."

    if not os.path.exists(image_path):
        return f"Error: Image file not found at {image_path}"

    try:
        with Image.open(image_path) as img:
            info: Dict[str, Any] = {
                "format": img.format,
                "mode": img.mode,
                "width": img.width,
                "height": img.height,
                "is_animated": getattr(img, "is_animated", False),
            }
            
            # Extract EXIF if available
            exif_data = img.getexif()
            if exif_data:
                exif_dict = {}
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    # Exclude huge binary blobs like MakerNote or UserComment if they are bytes
                    if isinstance(value, bytes):
                        continue
                    exif_dict[tag] = str(value)
                if exif_dict:
                    info["exif"] = exif_dict
                    
            return json.dumps(info, indent=2)
    except Exception as e:
        return f"Error processing image: {e}"


@tool(name="image_convert_format", category="Image", desc="Convert an image from one format to another (e.g. png to jpg).")
def image_convert_format(input_path: str, output_path: str) -> str:
    """Converts an image format by saving it to a new extension.
    If converting RGBA to JPEG, it automatically converts the image to RGB.

    Args:
        input_path: Path to the source image.
        output_path: Path to save the converted image (extension dictates format).
    """
    if not HAS_PILLOW:
        return "Error: Pillow library is not installed."

    if not os.path.exists(input_path):
        return f"Error: Input file not found at {input_path}"

    try:
        with Image.open(input_path) as img:
            out_ext = os.path.splitext(output_path)[1].lower()
            
            # JPEG does not support transparency (RGBA)
            if out_ext in [".jpg", ".jpeg"] and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(output_path)
            
        return f"Success: Image converted and saved to {output_path}"
    except Exception as e:
        return f"Error converting image: {e}"


@tool(name="image_resize", category="Image", desc="Resize an image by width/height or scale percentage.")
def image_resize(input_path: str, output_path: str, width: int = 0, height: int = 0, scale: float = 0.0) -> str:
    """Resizes an image. You can specify exact width and height, or just one to preserve aspect ratio, or a scale factor.

    Args:
        input_path: Path to the source image.
        output_path: Path to save the resized image.
        width: Target width in pixels (0 to ignore).
        height: Target height in pixels (0 to ignore).
        scale: Scale multiplier (e.g. 0.5 for 50%, 2.0 for 200%). Ignored if width/height are provided.
    """
    if not HAS_PILLOW:
        return "Error: Pillow library is not installed."

    if not os.path.exists(input_path):
        return f"Error: Input file not found at {input_path}"

    if width == 0 and height == 0 and scale <= 0:
        return "Error: You must provide either width, height, or a positive scale."

    try:
        with Image.open(input_path) as img:
            orig_w, orig_h = img.size
            
            if width > 0 and height > 0:
                new_w, new_h = width, height
            elif width > 0:
                # Maintain aspect ratio based on width
                ratio = width / float(orig_w)
                new_w, new_h = width, int(orig_h * ratio)
            elif height > 0:
                # Maintain aspect ratio based on height
                ratio = height / float(orig_h)
                new_w, new_h = int(orig_w * ratio), height
            else:
                # Scale multiplier
                new_w = int(orig_w * scale)
                new_h = int(orig_h * scale)
                
            # Use high-quality resampling (LANCZOS)
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                # Fallback for older Pillow versions
                resample = Image.LANCZOS
                
            resized_img = img.resize((new_w, new_h), resample)
            
            # Handle RGBA -> JPEG conversion if needed
            out_ext = os.path.splitext(output_path)[1].lower()
            if out_ext in [".jpg", ".jpeg"] and resized_img.mode in ("RGBA", "P"):
                resized_img = resized_img.convert("RGB")
                
            resized_img.save(output_path)
            
        return f"Success: Image resized to {new_w}x{new_h} and saved to {output_path}"
    except Exception as e:
        return f"Error resizing image: {e}"
