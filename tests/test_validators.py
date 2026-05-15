from core.validators import _normalize_path

def test_normalize_path_normal_string():
    assert _normalize_path("path/to/file") == "path/to/file"

def test_normalize_path_resolves_dot_dot():
    assert _normalize_path("path/to/../file") == "path/file"

def test_normalize_path_resolves_dot():
    assert _normalize_path("path/./to/file") == "path/to/file"

def test_normalize_path_removes_redundant_slashes():
    assert _normalize_path("path//to///file") == "path/to/file"

def test_normalize_path_with_none():
    assert _normalize_path(None) == "None"

def test_normalize_path_with_integer():
    assert _normalize_path(123) == "123"

def test_normalize_path_empty_string():
    assert _normalize_path("") == "."

def test_normalize_path_with_list():
    assert _normalize_path(["path"]) == "['path']"
