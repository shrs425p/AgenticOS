from unittest.mock import patch, MagicMock
from ops.addons.git import gitstatus, gitdiff, gitadd, gitcommit, gitlog

@patch("subprocess.run")
def test_gitstatus(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=" M file.py\n?? untracked.py", stderr="")
    res = gitstatus()
    assert "M file.py" in res
    mock_run.assert_called_once_with(["git", "status", "-s"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

@patch("subprocess.run")
def test_gitdiff(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="diff output", stderr="")
    res = gitdiff()
    assert "diff output" in res
    mock_run.assert_called_once_with(["git", "diff"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

    gitdiff(staged=True)
    assert mock_run.call_count == 2

@patch("subprocess.run")
def test_gitadd(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    res = gitadd(["file.py"])
    assert "Success" in res
    mock_run.assert_called_once_with(["git", "add", "file.py"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

@patch("subprocess.run")
def test_gitcommit(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="[main 12345] commit message", stderr="")
    res = gitcommit("commit message")
    assert "commit message" in res
    mock_run.assert_called_once_with(["git", "commit", "-m", "commit message"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

@patch("subprocess.run")
def test_gitlog(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="12345 first commit\n67890 second commit", stderr="")
    res = gitlog(limit=5)
    assert "first commit" in res
    mock_run.assert_called_once_with(["git", "log", "-n", "5", "--oneline"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

@patch("subprocess.run")
def test_git_error_handling(mock_run):
    # Test non-zero exit code
    mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="Not a git repository")
    res = gitstatus()
    assert "Git error" in res
    assert "Not a git repository" in res

@patch("subprocess.run", side_effect=FileNotFoundError)
def test_git_not_found(mock_run):
    res = gitstatus()
    assert "git' command not found" in res
