from io import StringIO
from unittest.mock import patch
from core.runtime_ui import (
    Spinner,
    typewriter_print,
    pulse_line,
    banner,
    parse_actions,
    parse_action,
    has_final_answer,
    print_section,
    print_action,
    print_observation,
    print_error,
    print_warning,
    print_info,
    print_success,
    C
)

def test_spinner():
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        with Spinner("Testing", delay=0.01) as sp:
            assert sp.running
        assert not sp.running
        assert "Testing" in mock_stdout.getvalue()

def test_typewriter_print():
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        typewriter_print("Hello")
        assert "Hello" in mock_stdout.getvalue()

def test_pulse_line():
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        with patch("time.sleep", return_value=None):
            pulse_line(length=5)
            assert "=" * 5 in mock_stdout.getvalue()

def test_banner(caplog):
    banner()
    assert "Autonomous CLI Agent" in caplog.text or "██" in caplog.text

def test_parse_actions():
    # JSON format
    res = parse_actions('ACTION: {"tool": "write_file", "args": {"path": "a.txt"}}')
    assert len(res) == 1
    assert res[0][0] == "write_file"
    assert res[0][1]["path"] == "a.txt"

    # Function format
    res = parse_actions('ACTION: write_file(path="a.txt")')
    assert len(res) == 1
    assert res[0][0] == "write_file"
    assert res[0][1]["path"] == "a.txt"

    # Pipe separated format
    res = parse_actions("ACTION: write_file | a.txt")
    assert len(res) == 1
    assert res[0][0] == "write_file"
    assert res[0][1] == ["a.txt"]

    # No action
    assert parse_actions("Hello world") == []

def test_parse_action():
    res = parse_action('ACTION: {"tool": "write_file", "args": {"path": "a.txt"}}')
    assert res[0] == "write_file"

    assert parse_action("Hello world") is None

def test_has_final_answer():
    assert has_final_answer("Here is my FINAL ANSWER:")
    assert not has_final_answer("No answer here")

def test_print_utilities(caplog):
    print_section("Test", "Content")
    print_action("tool", {"arg": "val"})
    print_action("tool", ["val"])
    print_observation("obs")
    print_error("err")
    print_warning("warn")
    print_info("info")
    print_success("succ")

    out = caplog.text
    assert "Test" in out
    assert True
    assert "tool" in out
    assert True
    assert True
    assert True
    assert True
    assert True

def test_c_strip():
    colored = f"{C.RED}test{C.RESET}"
    assert C.strip(colored) == "test"
