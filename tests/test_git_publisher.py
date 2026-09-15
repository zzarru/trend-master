import subprocess
from unittest.mock import MagicMock

from trend_pipeline import git_publisher


def test_publish_runs_git_add_commit_push_in_order():
    mock_run = MagicMock(return_value=MagicMock(returncode=0))

    result = git_publisher.publish(["docs/index.html"], "chore: update trend report", run=mock_run)

    assert result is True
    calls = mock_run.call_args_list
    assert calls[0].args[0] == ["git", "add", "docs/index.html"]
    assert calls[1].args[0] == [
        "git", "commit", "-m", "chore: update trend report", "--", "docs/index.html",
    ]
    assert calls[2].args[0] == ["git", "push"]


def test_publish_returns_false_when_git_command_fails():
    def failing_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    result = git_publisher.publish(["docs/index.html"], "chore: update trend report", run=failing_run)

    assert result is False


def test_publish_returns_false_when_git_executable_missing():
    def missing_git_run(cmd, **kwargs):
        raise FileNotFoundError("git not found")

    result = git_publisher.publish(["docs/index.html"], "chore: update trend report", run=missing_git_run)

    assert result is False


def test_publish_prints_failure_message_on_error(capsys):
    def failing_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    git_publisher.publish(["docs/index.html"], "chore: update trend report", run=failing_run)

    captured = capsys.readouterr()
    assert "git 배포 실패" in captured.out


def test_publish_treats_nothing_to_commit_as_success_and_still_pushes():
    calls = []

    def commit_fails_with_nothing_to_commit(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["git", "commit"]:
            exc = subprocess.CalledProcessError(1, cmd)
            exc.stdout = "nothing to commit, working tree clean"
            raise exc
        return MagicMock(returncode=0)

    result = git_publisher.publish(
        ["docs/index.html"], "chore: update trend report", run=commit_fails_with_nothing_to_commit
    )

    assert result is True
    assert ["git", "push"] in calls
