"""Module for clipboard.py"""
from __future__ import annotations


from kernel.base import tool
class ClipboardMixin:
    @tool(name="clipboardget", desc="Get clipboard text.", category="Terminal")
    def clipboardget(self) -> str:
        """clipboardget function."""
        try:
            import pyperclip

            return pyperclip.paste() or ""
        except Exception:
            pass

        try:
            import tkinter

            root = tkinter.Tk()
            root.withdraw()
            data = root.clipboardget()
            root.destroy()
            return data or ""
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @tool(name="clipboardset", desc="Set clipboard text. Args: text", category="Terminal")
    def clipboardset(self, text: str) -> str:
        """clipboardset function."""
        try:
            import pyperclip

            pyperclip.copy(text or "")
            return "OK"
        except Exception:
            pass

        try:
            import tkinter

            root = tkinter.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text or "")
            root.update()
            root.destroy()
            return "OK"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"
