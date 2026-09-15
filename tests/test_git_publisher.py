import subprocess
from unittest.mock import MagicMock

from trend_pipeline import git_publisher


def test_publish_runs_git_add_commit_push_in_order():
    mock_run = MagicMock(return_value=MagicMock(returncode=0))

    result = git_publisher.publish(["docs/index.html"], "chore: update trend report", run=mock_run)

    assert result is True
    calls = mock_run.call_args_list
    assert calls[0].args[0] == ["git", "add", "docs/index.html"]
    assert calls[1].args[0] == ["git", "commit", "-m", "chore: update trend report"]
    assert calls[2].args[0] == ["git", "push"]


def test_publish_returns_false_when_git_command_fails():
    def failing_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    result = git_publisher.publish(["docs/index.html"], "chore: update trend report", run=failing_run)

    assert result is False
