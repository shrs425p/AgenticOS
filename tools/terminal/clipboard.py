from __future__ import annotations


class ClipboardMixin:
    def clipboard_get(self) -> str:
        try:
            import pyperclip

            return pyperclip.paste() or ""
        except Exception:
            pass

        try:
            import tkinter

            root = tkinter.Tk()
            root.withdraw()
            data = root.clipboard_get()
            root.destroy()
            return data or ""
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    def clipboard_set(self, text: str) -> str:
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
