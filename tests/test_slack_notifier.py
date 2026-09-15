from unittest.mock import MagicMock

from trend_pipeline import slack_notifier


def test_notify_posts_message_with_report_link():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_post = MagicMock(return_value=mock_response)

    result = slack_notifier.notify(
        "https://hooks.slack.com/services/x", "https://user.github.io/repo/", 7, post=mock_post
    )

    assert result is True
    args, kwargs = mock_post.call_args
    assert args[0] == "https://hooks.slack.com/services/x"
    assert kwargs["json"]["text"] == "트렌드위클리 7호가 발행됐어요: https://user.github.io/repo/"


def test_notify_returns_false_when_request_fails():
    def failing_post(*args, **kwargs):
        raise RuntimeError("network error")

    result = slack_notifier.notify(
        "https://hooks.slack.com/services/x", "https://user.github.io/repo/", 7, post=failing_post
    )

    assert result is False


def test_notify_prints_generic_failure_message_without_leaking_webhook_url(capsys):
    def failing_post(*args, **kwargs):
        raise RuntimeError("connection error to https://hooks.slack.com/services/SECRET_TOKEN")

    slack_notifier.notify(
        "https://hooks.slack.com/services/SECRET_TOKEN",
        "https://user.github.io/repo/",
        7,
        post=failing_post,
    )

    captured = capsys.readouterr()
    assert "SECRET_TOKEN" not in captured.out
    assert "슬랙 알림 실패" in captured.out
