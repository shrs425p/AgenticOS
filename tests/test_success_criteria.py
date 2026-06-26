from core.success_criteria import SuccessCriteria

def test_success_criteria_parsing():
    goal = "Create a directory, copy files. Make sure that tests pass and ensure that directory is cleaned up."
    sc = SuccessCriteria(goal)
    assert len(sc.criteria) == 2
    assert sc.criteria[0] == "tests pass"
    assert sc.criteria[1] == "directory is cleaned up"

def test_success_criteria_parsing_case_insensitive():
    goal = "VERIFY THAT file exists, then check that permission is correct."
    sc = SuccessCriteria(goal)
    assert len(sc.criteria) == 2
    assert sc.criteria[0] == "file exists"
    assert sc.criteria[1] == "permission is correct"

def test_success_criteria_met():
    goal = "Ensure that the build succeeds."
    sc = SuccessCriteria(goal)
    assert sc.criteria == ["the build succeeds"]
    
    # Not met yet (build not mentioned)
    history = [{"role": "assistant", "content": "I will run the command."}]
    assert not sc.is_met(history)
    
    # Met (build succeeds mentioned)
    history_met = [
        {"role": "assistant", "content": "Running build..."},
        {"role": "user", "content": "OBSERVATION: The build succeeds with 0 errors."}
    ]
    assert sc.is_met(history_met)
