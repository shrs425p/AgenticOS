from core.validators import _normalize_path, _resolve_path, validate_tool, _arg_get

def test_normalize_path():
    assert _normalize_path("  test/path  ") == "test/path"
    assert _normalize_path('"test/path"') == "test/path"
    assert _normalize_path("'test/path'") == "test/path"
    assert _normalize_path("") == ""
    assert _normalize_path(None) == ""

def test_resolve_path(tmp_path):
    # Absolute
    abs_path = tmp_path / "foo"
    assert _resolve_path(str(abs_path), tmp_path) == abs_path.resolve()

    # Relative missing workspace name
    rel_path = "bar/baz"
    assert _resolve_path(rel_path, tmp_path) == (tmp_path / "bar/baz").resolve()

    # Relative starting with workspace name
    workspace_name = tmp_path.name
    rel_with_ws = f"{workspace_name}/bar/baz"
    assert _resolve_path(rel_with_ws, tmp_path) == (tmp_path / "bar/baz").resolve()

def test_arg_get():
    # dict
    args_dict = {"path": "foo/bar"}
    assert _arg_get(args_dict, "path") == "foo/bar"
    assert _arg_get(args_dict, "missing") == ""

    # list
    args_list = ["foo", "bar"]
    assert _arg_get(args_list, "path", index=0) == "foo"
    assert _arg_get(args_list, "path", index=1) == "bar"
    assert _arg_get(args_list, "path", index=2) == ""
    assert _arg_get(args_list, "path", index=-1) == ""

    # other
    assert _arg_get(None, "path") == ""

def test_validate_tool(tmp_path):
    # write_file - file exists
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    res = validate_tool("write_file", {"path": str(test_file)}, "", workspace_root=tmp_path)
    assert res == "VALIDATION: file exists"

    # write_file - file missing
    missing_file = tmp_path / "missing.txt"
    res = validate_tool("write_file", {"path": str(missing_file)}, "", workspace_root=tmp_path)
    assert res == f"VALIDATION: file missing ({missing_file.resolve()})"

    # write_file missing path arg
    assert validate_tool("write_file", {}, "", workspace_root=tmp_path) == ""

    # create_dir - dir exists
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()
    res = validate_tool("create_dir", {"path": str(test_dir)}, "", workspace_root=tmp_path)
    assert res == "VALIDATION: dir exists"

    # create_dir - dir missing
    missing_dir = tmp_path / "missingdir"
    res = validate_tool("create_dir", {"path": str(missing_dir)}, "", workspace_root=tmp_path)
    assert res == f"VALIDATION: dir missing ({missing_dir.resolve()})"

    # delete_file - file deleted
    res = validate_tool("delete_file", {"path": str(missing_file)}, "", workspace_root=tmp_path)
    assert res == "VALIDATION: file deleted"

    # delete_file - file still exists
    res = validate_tool("delete_file", {"path": str(test_file)}, "", workspace_root=tmp_path)
    assert res == f"VALIDATION: file still exists ({test_file.resolve()})"

    # delete_dir - dir deleted
    res = validate_tool("delete_dir", {"path": str(missing_dir)}, "", workspace_root=tmp_path)
    assert res == "VALIDATION: dir deleted"

    # delete_dir - dir still exists
    res = validate_tool("delete_dir", {"path": str(test_dir)}, "", workspace_root=tmp_path)
    assert res == f"VALIDATION: dir still exists ({test_dir.resolve()})"

    # copy_file - destination exists
    res = validate_tool("copy_file", {"dst": str(test_file)}, "", workspace_root=tmp_path)
    assert res == "VALIDATION: destination exists"

    # copy_file - destination missing
    res = validate_tool("copy_file", {"dst": str(missing_file)}, "", workspace_root=tmp_path)
    assert res == f"VALIDATION: destination missing ({missing_file.resolve()})"

    # download_file - exists
    res = validate_tool("download_file", {"dest_path": str(test_file)}, "", workspace_root=tmp_path)
    assert res == "VALIDATION: download exists"

    # terminal
    res = validate_tool("run_command", {}, "[exit: 0]", workspace_root=tmp_path)
    assert res == "VALIDATION: command returned exit status (see output)"

    # open_url
    assert validate_tool("open_url", {}, "", workspace_root=tmp_path) == ""

    # unknown tool
    assert validate_tool("unknown", {}, "", workspace_root=tmp_path) == ""
    assert validate_tool("", {}, "", workspace_root=tmp_path) == ""
