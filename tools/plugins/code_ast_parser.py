"""Code AST Parser Plugin for reading Python skeletons."""

from __future__ import annotations

import os
import ast
import json
from typing import Any, Dict, List, Optional

from core.tool_registry import tool


class ASTMapVisitor(ast.NodeVisitor):
    """Visitor to extract class and function structures from a parsed AST."""
    
    def __init__(self):
        self.structure: List[Dict[str, Any]] = []
        # Keep track of current parent context
        self._current_parent: Optional[List[Dict[str, Any]]] = None
        self._root: List[Dict[str, Any]] = self.structure

    def _get_docstring(self, node: ast.AST) -> str:
        doc = ast.get_docstring(node)
        if doc:
            # truncate very long docstrings
            doc = doc.strip()
            if len(doc) > 150:
                return doc[:147] + "..."
            return doc
        return ""

    def visit_ClassDef(self, node: ast.ClassDef):
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        cls_info = {
            "type": "class",
            "name": node.name,
            "line": node.lineno,
            "bases": bases,
            "docstring": self._get_docstring(node),
            "methods": []
        }
        
        # Save previous parent, set current parent to this class's methods
        prev_parent = self._current_parent
        self._current_parent = cls_info["methods"]
        
        # Visit children (methods, nested classes)
        self.generic_visit(node)
        
        # Restore parent
        self._current_parent = prev_parent
        
        # Append to wherever we are
        if self._current_parent is not None:
            self._current_parent.append(cls_info)
        else:
            self._root.append(cls_info)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node, is_async=True)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool = False):
        # Extract arguments
        args = []
        for a in node.args.args:
            arg_str = a.arg
            if getattr(a, "annotation", None):
                try:
                    arg_str += f": {ast.unparse(a.annotation)}"
                except Exception:
                    pass
            args.append(arg_str)
            
        returns = ""
        if getattr(node, "returns", None):
            try:
                returns = ast.unparse(node.returns)
            except Exception:
                pass
                
        func_info = {
            "type": "async_method" if is_async else "method",
            "name": node.name,
            "line": node.lineno,
            "args": args,
            "returns": returns,
            "docstring": self._get_docstring(node)
        }
        
        if self._current_parent is not None:
            self._current_parent.append(func_info)
        else:
            self._root.append(func_info)


@tool(name="ast_parse_file", category="Code", desc="Parse a Python file and return its skeleton (classes, functions, docs).")
def ast_parse_file(file_path: str) -> str:
    """Parses a Python file using AST and returns a JSON outline of its structural skeleton.
    This saves massive amounts of context tokens compared to reading the full file.
    
    Args:
        file_path: Absolute or relative path to the Python file.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    if not file_path.endswith(".py"):
        return f"Error: File {file_path} is not a Python (.py) file."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
            
        tree = ast.parse(source)
        visitor = ASTMapVisitor()
        visitor.visit(tree)
        
        result = {
            "file": os.path.basename(file_path),
            "structure": visitor.structure
        }
        return json.dumps(result, indent=2)
    except SyntaxError as e:
        return f"Syntax Error parsing file {file_path}: {e}"
    except Exception as e:
        return f"Error processing file {file_path}: {e}"


@tool(name="ast_map_directory", category="Code", desc="Map the Python AST skeleton of an entire directory.")
def ast_map_directory(dir_path: str) -> str:
    """Recursively scans a directory and parses the AST of all Python files, returning a structural map.
    
    Args:
        dir_path: Path to the directory to scan.
    """
    if not os.path.exists(dir_path):
        return f"Error: Directory not found at {dir_path}"
        
    if not os.path.isdir(dir_path):
        return f"Error: {dir_path} is not a directory."

    directory_map = {}
    
    try:
        for root, dirs, files in os.walk(dir_path):
            # Skip hidden dirs, virtual environments, node_modules
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "__pycache__", "node_modules")]
            
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, dir_path)
                    
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            source = f.read()
                        tree = ast.parse(source)
                        visitor = ASTMapVisitor()
                        visitor.visit(tree)
                        
                        if visitor.structure:
                            directory_map[rel_path] = visitor.structure
                    except Exception:
                        directory_map[rel_path] = "Parse Error"
                        
        return json.dumps(directory_map, indent=2)
    except Exception as e:
        return f"Error mapping directory: {e}"
