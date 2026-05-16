"""Module for ocr_tools.py"""
import os
import subprocess
from pathlib import Path
from core.tool_base import tool
from core.runtime_config import resolve_local_path

class OCRManager:
    """
    AgenticOS OCR Manager.
    Supports both native Windows OCR and Tesseract-OCR.
    """
    def __init__(self, rules: dict = None, base_dir: str = "workspace", registry=None, cfg: dict = None):
        self.rules = rules or {}
        self.cfg = cfg or {}
        self.base_dir = Path(base_dir).resolve()
        self.registry = registry # ToolRegistry instance
        
        # Get Tesseract path from config and resolve it
        media_cfg = self.cfg.get("media", {})
        raw_path = media_cfg.get("tesseract_path", "tools/Tesseract-OCR/tesseract.exe")
        self.tesseract_path = resolve_local_path(raw_path)
        self.default_engine = media_cfg.get("ocr_engine", "auto")
        self.has_tesseract = os.path.exists(self.tesseract_path)

    def _resolve(self, path: str) -> Path:
        """Standard AgenticOS path resolution."""
        p = Path(path)
        if not p.is_absolute():
            return (self.base_dir / p).resolve()
        return p.resolve()

    def _run_tesseract(self, image_path: str) -> str:
        """Run Tesseract-OCR on the image."""
        try:
            # Tesseract command: tesseract [image] stdout
            # We use '-' for stdout in some versions or just 'stdout'
            result = subprocess.run(
                [self.tesseract_path, image_path, "stdout"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
            )
            if result.returncode != 0:
                return f"Tesseract Error: {result.stderr.strip()}"
            return result.stdout.strip()
        except Exception as e:
            return f"Tesseract Exception: {e}"

    def _run_win_ocr_ps(self, image_path: str) -> str:
        """Helper to run the WinRT OCR PowerShell script."""
        if not os.path.exists(image_path):
            return f"Error: Image file not found at {image_path}"

        ps_script = f"""
        [void][Windows.Security.Credentials.PasswordVault, Windows.Security.Credentials, ContentType=WindowsRuntime]
        [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
        [void][Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime]

        $imagePath = "{image_path}"
        $file = Get-Item $imagePath
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
            $ocrResult.Lines | ForEach-Object {{ $_.Text }}
        }} else {{
            "No text found in image."
        }}
        """
        
        try:
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            stdout, stderr = process.communicate(input=ps_script)
            
            if process.returncode != 0:
                return f"Native OCR Error: {stderr.strip()}"
            
            return stdout.strip() or "No text found."
        except Exception as e:
            return f"Native OCR Exception: {str(e)}"

    @tool(
        name="ocr_image",
        desc="Extract text from an image file using Tesseract or Native Windows OCR.",
        category="Media"
    )
    def ocr_image(self, path: str, engine: str = None) -> str:
        """
        Performs OCR on a local image file.
        Args:
            path: Absolute or workspace-relative path to the image.
            engine: 'tesseract', 'native', or 'auto'. Defaults to config.
        """
        engine = engine or self.default_engine
        resolved_path = str(self._resolve(path))
        
        if engine == "tesseract" or (engine == "auto" and self.has_tesseract):
            if not self.has_tesseract:
                return "Error: Tesseract not found at configured path."
            return self._run_tesseract(resolved_path)
        else:
            return self._run_win_ocr_ps(resolved_path)

    @tool(
        name="ocr_screen",
        desc="Captures the entire screen and extracts all visible text.",
        category="Media"
    )
    def ocr_screen(self, engine: str = None) -> str:
        """
        Takes a screenshot of the current screen and runs OCR on it.
        Args:
            engine: 'tesseract', 'native', or 'auto'. Defaults to config.
        """
        engine = engine or self.default_engine
        if not self.registry or not hasattr(self.registry, "screen"):
            return "Error: Screen tools not available."
            
        try:
            screenshot_res = self.registry.screen.take_screenshot()
            if "Error" in screenshot_res:
                return screenshot_res
            
            path = screenshot_res.replace("Screenshot saved: ", "").strip()
            return self.ocr_image(path, engine=engine)
        except Exception as e:
            return f"Error during screen OCR: {e}"
