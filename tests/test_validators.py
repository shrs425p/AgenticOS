import os
from core.validators import _normalize_path

def test_normalize_path_normal_string():
    p = os.path.join("path", "to", "file")
    assert _normalize_path(p) == p

def test_normalize_path_with_spaces():
    p = os.path.join("path", "to", "file")
    assert _normalize_path(f"  {p}  ") == p

def test_normalize_path_with_double_quotes():
    p = os.path.join("path", "to", "file")
    assert _normalize_path(f'"{p}"') == p

def test_normalize_path_with_single_quotes():
    p = os.path.join("path", "to", "file")
    assert _normalize_path(f"'{p}'") == p

def test_normalize_path_with_none():
    assert _normalize_path(None) == ""

def test_normalize_path_empty_string():
    assert _normalize_path("") == ""

def test_normalize_path_mixed_quotes_and_spaces():
    p = os.path.join("path", "to", "file")
    assert _normalize_path(f'  "{p}"  ') == p
    assert _normalize_path(f"  '{p}'  ") == p
