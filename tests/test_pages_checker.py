from unittest.mock import MagicMock

from trend_pipeline import pages_checker


def _response(json_data=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data or {})
    return resp


def test_wait_for_build_returns_true_immediately_when_already_built():
    mock_get = MagicMock(return_value=_response({"commit": "abc123", "status": "built"}))
    mock_sleep = MagicMock()

    result = pages_checker.wait_for_build("owner/repo", "token", "abc123", get=mock_get, sleep=mock_sleep)

    assert result is True
    mock_sleep.assert_not_called()


def test_wait_for_build_polls_until_built():
    responses = [
        _response({"commit": "abc123", "status": "queued"}),
        _response({"commit": "abc123", "status": "building"}),
        _response({"commit": "abc123", "status": "built"}),
    ]
    mock_get = MagicMock(side_effect=responses)
    mock_sleep = MagicMock()

    result = pages_checker.wait_for_build(
        "owner/repo", "token", "abc123", poll_interval=60, max_attempts=5, get=mock_get, sleep=mock_sleep
    )

    assert result is True
    assert mock_sleep.call_args_list == [((60,),), ((60,),)]


def test_wait_for_build_returns_false_when_errored():
    mock_get = MagicMock(return_value=_response({"commit": "abc123", "status": "errored"}))
    mock_sleep = MagicMock()

    result = pages_checker.wait_for_build("owner/repo", "token", "abc123", get=mock_get, sleep=mock_sleep)

    assert result is False
    mock_sleep.assert_not_called()


def test_wait_for_build_returns_false_after_max_attempts_when_still_pending():
    mock_get = MagicMock(return_value=_response({"commit": "abc123", "status": "building"}))
    mock_sleep = MagicMock()

    result = pages_checker.wait_for_build(
        "owner/repo", "token", "abc123", poll_interval=60, max_attempts=3, get=mock_get, sleep=mock_sleep
    )

    assert result is False
    assert mock_sleep.call_count == 2


def test_wait_for_build_ignores_build_for_different_commit():
    mock_get = MagicMock(return_value=_response({"commit": "other-sha", "status": "built"}))
    mock_sleep = MagicMock()

    result = pages_checker.wait_for_build(
        "owner/repo", "token", "abc123", poll_interval=60, max_attempts=2, get=mock_get, sleep=mock_sleep
    )

    assert result is False
    assert mock_sleep.call_count == 1


def test_wait_for_build_returns_false_when_request_raises():
    def failing_get(*args, **kwargs):
        raise RuntimeError("network error")

    result = pages_checker.wait_for_build(
        "owner/repo", "token", "abc123", poll_interval=60, max_attempts=2, get=failing_get, sleep=MagicMock()
    )

    assert result is False


def test_wait_for_build_sends_auth_header_and_correct_url():
    mock_get = MagicMock(return_value=_response({"commit": "abc123", "status": "built"}))

    pages_checker.wait_for_build("owner/repo", "my-token", "abc123", get=mock_get, sleep=MagicMock())

    args, kwargs = mock_get.call_args
    assert args[0] == "https://api.github.com/repos/owner/repo/pages/builds/latest"
    assert kwargs["headers"]["Authorization"] == "Bearer my-token"
