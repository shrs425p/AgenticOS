from __future__ import annotations


class EditMixin:
    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            if old_text not in text:
                return "Old text not found in file."
            out = text.replace(old_text, new_text)
            p.write_text(out, encoding="utf-8")
            return f"Replaced text in {path}"
        except Exception as e:
            return f"Error editing file: {e}"

    def edit_line(self, path: str, line_number: str, new_content: str) -> str:
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            idx = int(line_number) - 1
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines(True)
            if idx < 0 or idx >= len(lines):
                return f"Error: line_number out of range. File has {len(lines)} lines."
            lines[idx] = new_content.rstrip("\n") + "\n"
            p.write_text("".join(lines), encoding="utf-8")
            return f"Updated line {line_number} in {path}"
        except Exception as e:
            return f"Error editing line: {e}"

    def insert_line(self, path: str, line_number: str, content: str) -> str:
        p = self._resolve(path)
        self._deny_file_modify()
        self._deny_internal_writes(p)
        try:
            idx = int(line_number) - 1
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines(True)
            if idx < 0:
                idx = 0
            if idx > len(lines):
                idx = len(lines)
            lines.insert(idx, content.rstrip("\n") + "\n")
            p.write_text("".join(lines), encoding="utf-8")
            return f"Inserted line before {line_number} in {path}"
        except Exception as e:
            return f"Error inserting line: {e}"
