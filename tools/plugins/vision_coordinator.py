"""Plugin module for unified multi-modal visual coordinate mapping and hardware actions."""
import os
import logging
import platform
import subprocess
import shutil
import time
from typing import Optional, List, Dict, Any

from core.tool_base import tool
from tools.screen_tools import ScreenManager
from tools.terminal import TerminalExecutor
from core.platform_api import PlatformAPI

def _extract_word_boxes(image_path: str) -> List[Dict[str, Any]]:
    """Runs high-speed WinRT OCR or Tesseract to extract word bounding boxes from image.

    Args:
        image_path (str): File path to screenshot.

    Returns:
        List[Dict[str, Any]]: List of parsed words with text and coordinates.
    """
    sys_name = platform.system()
    words = []

    if sys_name == "Windows":
        # Native WindowsRT OCR PowerShell script
        ps_script = f"""
        [void][Windows.Security.Credentials.PasswordVault, Windows.Security.Credentials, ContentType=WindowsRuntime]
        [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
        [void][Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime]

        $file = Get-Item "{image_path}"
        $stream = [Windows.Storage.Streams.RandomAccessStreamReference]::CreateFromFile($file).OpenReadAsync().GetResults()
        $decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream).GetResults()
        $bitmap = $decoder.GetSoftwareBitmapAsync().GetResults()

        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
        if (-not $engine) {{
            "Error: OCR Engine could not be initialized."
            exit
        }}
        $ocrResult = $engine.RecognizeAsync($bitmap).GetResults()

        if ($ocrResult.Lines) {{
            $ocrResult.Lines | ForEach-Object {{
                $_.Words | ForEach-Object {{
                    $rect = $_.BoundingRect
                    "$($_.Text)|$($rect.X)|$($rect.Y)|$($rect.Width)|$($rect.Height)"
                }}
            }}
        }}
        """
        try:
            process = PlatformAPI.popen_powershell(
                "-",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            stdout, _ = process.communicate(input=ps_script)

            for line in stdout.splitlines():
                parts = line.strip().split("|")
                if len(parts) == 5:
                    try:
                        words.append({
                            "text": parts[0],
                            "x": int(float(parts[1])),
                            "y": int(float(parts[2])),
                            "w": int(float(parts[3])),
                            "h": int(float(parts[4]))
                        })
                    except ValueError:
                        pass
        except Exception as e:
            logging.error(f"Vision Coordinator: WinRT OCR failed: {e}")

    # Fallback or Non-Windows: Tesseract TSV
    if not words:
        tesseract_bin = "tesseract"
        from core.runtime_config import resolve_local_path
        local_tess = resolve_local_path("tools/Tesseract-OCR/tesseract.exe")
        if os.path.exists(local_tess):
            tesseract_bin = local_tess

        try:
            result = subprocess.run(
                [tesseract_bin, image_path, "stdout", "tsv"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
            )
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                if lines:
                    header = lines[0].split("\t")
                    try:
                        l_idx = header.index("left")
                        t_idx = header.index("top")
                        w_idx = header.index("width")
                        h_idx = header.index("height")
                        txt_idx = header.index("text")

                        for line in lines[1:]:
                            parts = line.split("\t")
                            if len(parts) > txt_idx:
                                text_val = parts[txt_idx].strip()
                                if text_val:
                                    words.append({
                                        "text": text_val,
                                        "x": int(parts[l_idx]),
                                        "y": int(parts[t_idx]),
                                        "w": int(parts[w_idx]),
                                        "h": int(parts[h_idx])
                                    })
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            logging.error(f"Vision Coordinator: Tesseract TSV failed: {e}")

    return words

def _find_phrase_coords(label: str, words: List[Dict[str, Any]]) -> Optional[tuple]:
    """Scans the coordinates matrix to locate adjacent words matching the label.

    Args:
        label (str): Label string to search.
        words (List[Dict[str, Any]]): Parsed words list.

    Returns:
        Optional[tuple]: The (x, y) center pixel coordinates.
    """
    label_tokens = [t.lower().strip() for t in label.split() if t.strip()]
    if not label_tokens or not words:
        return None

    num_tokens = len(label_tokens)

    # Sequence alignment search
    for i in range(len(words) - num_tokens + 1):
        match = True
        sequence = []
        for j in range(num_tokens):
            word_item = words[i + j]
            token = label_tokens[j]
            word_text = word_item["text"].lower()

            clean_word = word_text.strip(".,:;!?()[]{}'\"")
            clean_token = token.strip(".,:;!?()[]{}'\"")

            if clean_token not in clean_word and clean_word not in clean_token:
                match = False
                break
            sequence.append(word_item)

        if match:
            min_x = min(w["x"] for w in sequence)
            min_y = min(w["y"] for w in sequence)
            max_x = max(w["x"] + w["w"] for w in sequence)
            max_y = max(w["y"] + w["h"] for w in sequence)

            center_x = min_x + (max_x - min_x) // 2
            center_y = min_y + (max_y - min_y) // 2
            return center_x, center_y

    # Fallback to single token lookup
    for item in words:
        word_text = item["text"].lower().strip(".,:;!?()[]{}'\"")
        for token in label_tokens:
            if token == word_text or (len(token) > 2 and token in word_text):
                center_x = item["x"] + item["w"] // 2
                center_y = item["y"] + item["h"] // 2
                return center_x, center_y

    return None

@tool(name="click_element_by_name", desc="Capture screen, find a text element matching the label using OCR coordinate mapping, and click it. Args: label", category="Plugins")
def click_element_by_name(label: str) -> str:
    """Captures the current screen, resolves coordinates of the label text using WinRT/Tesseract OCR, and performs a native mouse click.

    Args:
        label (str): Text label or phrase to click on screen (e.g. 'File', 'Settings', 'Cancel').

    Returns:
        str: Success detail or error message.
    """
    try:
        sm = ScreenManager()
        scr_res = sm.take_screenshot()
        if "Error" in scr_res:
            return f"Error: Failed to capture screen: {scr_res}"

        screenshot_path = scr_res.replace("Screenshot saved: ", "").strip()
        if not os.path.exists(screenshot_path):
            return f"Error: Screen capture file not found at {screenshot_path}"

        words = _extract_word_boxes(screenshot_path)
        if not words:
            return "Error: No visible text was detected on the current screen."

        coords = _find_phrase_coords(label, words)
        if not coords:
            return f"Error: Could not locate text matching '{label}' on screen."

        cx, cy = coords

        term = TerminalExecutor()
        click_res = term.mouse_click(button="left", x=cx, y=cy)
        return f"Success: Located '{label}' at coordinate ({cx}, {cy}) and triggered click. Click response: {click_res}"
    except Exception as e:
        return f"Error during click_element_by_name: {type(e).__name__}: {e}"

@tool(name="drag_and_drop_visual", desc="Perform visual drag and drop from source text label to destination text label. Args: source, destination", category="Plugins")
def drag_and_drop_visual(source: str, destination: str) -> str:
    """Finds coordinates of source and destination labels using visual coordinate mapping and performs a smooth mouse drag-and-drop.

    Args:
        source (str): Label of the item to drag.
        destination (str): Label of the drop target.

    Returns:
        str: Success or failure description.
    """
    try:
        sm = ScreenManager()
        scr_res = sm.take_screenshot()
        if "Error" in scr_res:
            return f"Error: Failed to capture screen: {scr_res}"

        screenshot_path = scr_res.replace("Screenshot saved: ", "").strip()

        words = _extract_word_boxes(screenshot_path)
        if not words:
            return "Error: No text found on screen to coordinate drag-and-drop."

        src_coords = _find_phrase_coords(source, words)
        dest_coords = _find_phrase_coords(destination, words)

        if not src_coords:
            return f"Error: Could not locate source element '{source}'."
        if not dest_coords:
            return f"Error: Could not locate destination element '{destination}'."

        sx, sy = src_coords
        dx, dy = dest_coords

        sys_name = platform.system()
        if sys_name == "Windows":
            # Run smooth Windows mouse drag
            ps_script = f"""
            Add-Type -TypeDefinition @'
            using System;
            using System.Runtime.InteropServices;
            public class Mouse {{
                [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, int dwExtraInfo);
                [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
            }}
            '@ -ErrorAction SilentlyContinue;

            # Press down at source
            [Mouse]::SetCursorPos({sx}, {sy});
            Start-Sleep -Milliseconds 100;
            [Mouse]::mouse_event(0x0002, 0, 0, 0, 0); # MOUSEEVENTF_LEFTDOWN
            Start-Sleep -Milliseconds 100;

            # Smooth movement interpolation
            $steps = 15
            for ($i = 1; $i -le $steps; $i++) {{
                $px = {sx} + (($i * ({dx} - {sx})) / $steps)
                $py = {sy} + (($i * ({dy} - {sy})) / $steps)
                [Mouse]::SetCursorPos([int]$px, [int]$py);
                Start-Sleep -Milliseconds 15;
            }}

            # Release at destination
            [Mouse]::SetCursorPos({dx}, {dy});
            Start-Sleep -Milliseconds 100;
            [Mouse]::mouse_event(0x0004, 0, 0, 0, 0); # MOUSEEVENTF_LEFTUP
            """
            PlatformAPI.run_powershell(ps_script)
        elif sys_name == "Darwin":
            term = TerminalExecutor()
            term.mouse_move(sx, sy)
            time.sleep(0.1)
            term.mouse_click(button="left")
            time.sleep(0.5)
            term.mouse_move(dx, dy)
            time.sleep(0.1)
            term.mouse_click(button="left")
        else:
            if shutil.which("xdotool"):
                subprocess.run(["xdotool", "mousemove", str(sx), str(sy), "mousedown", "1", "mousemove", str(dx), str(dy), "mouseup", "1"])
            else:
                return "Error: Missing xdotool on Linux for drag-and-drop actions."

        return f"Success: Performed visual drag-and-drop from '{source}' ({sx}, {sy}) to '{destination}' ({dx}, {dy})."
    except Exception as e:
        return f"Error during drag_and_drop_visual: {type(e).__name__}: {e}"
