from unittest.mock import patch, MagicMock
from tools.plugins.git_manager import git_status, git_diff, git_add, git_commit, git_log

@patch("subprocess.run")
def test_git_status(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=" M file.py\n?? untracked.py", stderr="")
    res = git_status()
    assert "M file.py" in res
    mock_run.assert_called_once_with(["git", "status", "-s"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

@patch("subprocess.run")
def test_git_diff(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="diff output", stderr="")
    res = git_diff()
    assert "diff output" in res
    mock_run.assert_called_once_with(["git", "diff"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

    git_diff(staged=True)
    assert mock_run.call_count == 2

@patch("subprocess.run")
def test_git_add(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    res = git_add(["file.py"])
    assert "Success" in res
    mock_run.assert_called_once_with(["git", "add", "file.py"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

@patch("subprocess.run")
def test_git_commit(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="[main 12345] commit message", stderr="")
    res = git_commit("commit message")
    assert "commit message" in res
    mock_run.assert_called_once_with(["git", "commit", "-m", "commit message"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

@patch("subprocess.run")
def test_git_log(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="12345 first commit\n67890 second commit", stderr="")
    res = git_log(limit=5)
    assert "first commit" in res
    mock_run.assert_called_once_with(["git", "log", "-n", "5", "--oneline"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

@patch("subprocess.run")
def test_git_error_handling(mock_run):
    # Test non-zero exit code
    mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="Not a git repository")
    res = git_status()
    assert "Git error" in res
    assert "Not a git repository" in res

@patch("subprocess.run", side_effect=FileNotFoundError)
def test_git_not_found(mock_run):
    res = git_status()
    assert "git' command not found" in res
