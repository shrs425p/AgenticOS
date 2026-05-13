import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime_ui import parse_actions

def test_single_json():
    text = "ACTION: {\"tool\": \"read_file\", \"args\": {\"path\": \"test.txt\"}}"
    actions = parse_actions(text)
    assert len(actions) == 1
    assert actions[0][0] == "read_file"
    assert actions[0][1]["path"] == "test.txt"
    print("test_single_json: PASSED")

def test_multi_action():
    text = """
    I will write the file and then run it.
    ACTION: {"tool": "write_file", "args": {"path": "script.py", "content": "print('hello')"}}
    ACTION: run_script(path="script.py")
    """
    actions = parse_actions(text)
    assert len(actions) == 2
    assert actions[0][0] == "write_file"
    assert actions[1][0] == "run_script"
    print("test_multi_action: PASSED")

def test_mangled_json_with_pipes():
    # Scenario where JSON parsing fails but it shouldn't fall back to pipe splitting if it looks like JSON
    text = """
    ACTION: {"tool": "run_python", "args": {"code": "print('a | b'); print(\"quote error\")"}}
    """
    # Note: the JSON above is technically valid, but let's test one that is SLIGHTLY broken
    text_broken = "ACTION: {\"tool\": \"run_python\", \"args\": {\"code\": \"print('a | b')\" " # missing closing brace
    actions = parse_actions(text_broken)
    # It should NOT be split by the pipe into a junk tool name.
    # Currently, my hardened logic just skips it if it doesn't parse as JSON but starts with {
    # This prevents the CoV from seeing junk tool names.
    assert len(actions) == 0 or actions[0][0] == "run_python"
    print("test_mangled_json_with_pipes: PASSED")

def test_legacy_pipe():
    text = "ACTION: read_file | test.txt"
    actions = parse_actions(text)
    assert len(actions) == 1
    assert actions[0][0] == "read_file"
    assert actions[0][1] == ["test.txt"]
    print("test_legacy_pipe: PASSED")

def test_no_action():
    text = "I'm just talking to you."
    actions = parse_actions(text)
    assert len(actions) == 0
    print("test_no_action: PASSED")

if __name__ == "__main__":
    try:
        test_single_json()
        test_multi_action()
        test_mangled_json_with_pipes()
        test_legacy_pipe()
        test_no_action()
        print("\nALL PARSER TESTS PASSED!")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR DURING TESTING: {e}")
        sys.exit(1)
