from unittest.mock import MagicMock

from trend_pipeline import slack_notifier


def test_notify_posts_message_with_report_link():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_post = MagicMock(return_value=mock_response)

    result = slack_notifier.notify(
        "https://hooks.slack.com/services/x", "https://user.github.io/repo/", post=mock_post
    )

    assert result is True
    args, kwargs = mock_post.call_args
    assert args[0] == "https://hooks.slack.com/services/x"
    assert kwargs["json"]["text"] == "오늘의 트렌드 리포트가 준비됐어요: https://user.github.io/repo/"


def test_notify_returns_false_when_request_fails():
    def failing_post(*args, **kwargs):
        raise RuntimeError("network error")

    result = slack_notifier.notify(
        "https://hooks.slack.com/services/x", "https://user.github.io/repo/", post=failing_post
    )

    assert result is False
