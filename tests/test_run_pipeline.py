from datetime import datetime
from unittest.mock import MagicMock, patch

import run_pipeline


def _today_str():
    return datetime.now().astimezone().strftime("%Y-%m-%d")


@patch("run_pipeline.content_analyzer.analyze_content_batch")
@patch("run_pipeline.youtube_collector.fetch_top_comments")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_collects_saves_and_returns_summary(
    mock_load_config, mock_collect_youtube, mock_fetch_comments, mock_analyze_batch, tmp_path
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(tmp_path / "index.html"),
        "report_base_url": "",
        "slack_webhook_url": "",
    }
    mock_collect_youtube.return_value = [
        {
            "source": "youtube",
            "source_id": "v1",
            "title": "YouTube Trend",
            "body": "body",
            "url": "https://www.youtube.com/watch?v=v1",
            "score": 1000,
            "num_comments": 20,
            "published_at": "2026-09-15T00:00:00",
        }
    ]
    mock_fetch_comments.return_value = ["댓글1", "댓글2"]
    mock_analyze_batch.return_value = [
        {
            "content_item": mock_collect_youtube.return_value[0],
            "category": "음악",
            "summary": "요약",
            "success": True,
        }
    ]

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary["youtube_collected"] == 1
    assert summary["analysis_success"] == 1
    assert summary["analysis_failed"] == 0
    mock_collect_youtube.assert_called_once_with("yt-key", region_code="KR", max_results=25)
    mock_fetch_comments.assert_called_once_with("yt-key", "v1")


@patch("run_pipeline.content_analyzer.analyze_content_batch")
@patch("run_pipeline.youtube_collector.fetch_top_comments")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_continues_when_youtube_collection_fails(
    mock_load_config, mock_collect_youtube, mock_fetch_comments, mock_analyze_batch, tmp_path
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(tmp_path / "index.html"),
        "report_base_url": "",
        "slack_webhook_url": "",
    }
    mock_collect_youtube.side_effect = RuntimeError("quota exceeded")
    mock_analyze_batch.return_value = []

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary["youtube_collected"] == 0
    assert summary["analysis_success"] == 0
    assert summary["analysis_failed"] == 0
    mock_fetch_comments.assert_not_called()


@patch("run_pipeline.content_analyzer.analyze_content_batch")
@patch("run_pipeline.youtube_collector.fetch_top_comments")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_redacts_api_key_from_failure_message(
    mock_load_config, mock_collect_youtube, mock_fetch_comments, mock_analyze_batch, capsys, tmp_path
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(tmp_path / "index.html"),
        "report_base_url": "",
        "slack_webhook_url": "",
    }
    mock_collect_youtube.side_effect = RuntimeError(
        "403 Client Error: https://www.googleapis.com/youtube/v3/videos?"
        "part=snippet&key=SUPER_SECRET_VALUE&chart=mostPopular"
    )
    mock_analyze_batch.return_value = []

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        run_pipeline.run()

    captured = capsys.readouterr()
    assert "SUPER_SECRET_VALUE" not in captured.out
    assert "유튜브 수집 실패" in captured.out
    assert "key=***REDACTED***" in captured.out


@patch("run_pipeline.slack_notifier.notify")
@patch("run_pipeline.git_publisher.publish")
@patch("run_pipeline.report_generator.generate_report")
@patch("run_pipeline.content_analyzer.analyze_content_batch")
@patch("run_pipeline.youtube_collector.fetch_top_comments")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_publishes_report_and_notifies_slack_when_configured(
    mock_load_config, mock_collect_youtube, mock_fetch_comments, mock_analyze_batch,
    mock_generate_report, mock_publish, mock_notify, tmp_path,
):
    report_path = tmp_path / "index.html"
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(report_path),
        "report_base_url": "https://user.github.io/repo/",
        "slack_webhook_url": "https://hooks.slack.com/services/x",
    }
    mock_collect_youtube.return_value = []
    mock_analyze_batch.return_value = []
    mock_generate_report.return_value = "<html>report</html>"
    mock_publish.return_value = True
    mock_notify.return_value = True

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    archive_path = tmp_path / "archive" / f"{_today_str()}.html"
    archive_index_path = tmp_path / "archive" / "index.html"

    assert report_path.read_text(encoding="utf-8") == "<html>report</html>"
    assert archive_path.read_text(encoding="utf-8") == "<html>report</html>"
    assert archive_index_path.exists()
    assert summary["report_published"] is True
    assert summary["slack_notified"] is True
    mock_publish.assert_called_once_with(
        [str(report_path), str(archive_path), str(archive_index_path)], "chore: update trend report"
    )
    mock_notify.assert_called_once_with(
        "https://hooks.slack.com/services/x", "https://user.github.io/repo/", 1
    )
    mock_generate_report.assert_called_once()
    assert mock_generate_report.call_args.args[2] == 1


@patch("run_pipeline.slack_notifier.notify")
@patch("run_pipeline.git_publisher.publish")
@patch("run_pipeline.report_generator.generate_report")
@patch("run_pipeline.content_analyzer.analyze_content_batch")
@patch("run_pipeline.youtube_collector.fetch_top_comments")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_skips_publish_and_slack_when_report_base_url_missing(
    mock_load_config, mock_collect_youtube, mock_fetch_comments, mock_analyze_batch,
    mock_generate_report, mock_publish, mock_notify, tmp_path,
):
    report_path = tmp_path / "index.html"
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(report_path),
        "report_base_url": "",
        "slack_webhook_url": "",
    }
    mock_collect_youtube.return_value = []
    mock_analyze_batch.return_value = []
    mock_generate_report.return_value = "<html>report</html>"

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary["report_published"] is False
    assert summary["slack_notified"] is False
    mock_publish.assert_not_called()
    mock_notify.assert_not_called()


@patch("run_pipeline.slack_notifier.notify")
@patch("run_pipeline.git_publisher.publish")
@patch("run_pipeline.report_generator.generate_report")
@patch("run_pipeline.content_analyzer.analyze_content_batch")
@patch("run_pipeline.youtube_collector.fetch_top_comments")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_continues_when_report_generation_fails(
    mock_load_config, mock_collect_youtube, mock_fetch_comments, mock_analyze_batch,
    mock_generate_report, mock_publish, mock_notify, tmp_path,
):
    report_path = tmp_path / "index.html"
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(report_path),
        "report_base_url": "https://user.github.io/repo/",
        "slack_webhook_url": "https://hooks.slack.com/services/x",
    }
    mock_collect_youtube.return_value = []
    mock_analyze_batch.return_value = []
    mock_generate_report.side_effect = RuntimeError("report generation exploded")

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary["report_published"] is False
    assert summary["slack_notified"] is False
    mock_publish.assert_not_called()
    mock_notify.assert_not_called()


@patch("run_pipeline.slack_notifier.notify")
@patch("run_pipeline.git_publisher.publish")
@patch("run_pipeline.report_generator.generate_report")
@patch("run_pipeline.content_analyzer.analyze_content_batch")
@patch("run_pipeline.youtube_collector.fetch_top_comments")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_increments_issue_number_based_on_existing_archive_dates(
    mock_load_config, mock_collect_youtube, mock_fetch_comments, mock_analyze_batch,
    mock_generate_report, mock_publish, mock_notify, tmp_path,
):
    report_path = tmp_path / "index.html"
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    (archive_dir / "2020-01-01.html").write_text("old issue 1", encoding="utf-8")
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(report_path),
        "report_base_url": "https://user.github.io/repo/",
        "slack_webhook_url": "https://hooks.slack.com/services/x",
    }
    mock_collect_youtube.return_value = []
    mock_analyze_batch.return_value = []
    mock_generate_report.return_value = "<html>report</html>"
    mock_publish.return_value = True
    mock_notify.return_value = True

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        run_pipeline.run()

    assert mock_generate_report.call_args.args[2] == 2
    mock_notify.assert_called_once_with(
        "https://hooks.slack.com/services/x", "https://user.github.io/repo/", 2
    )


@patch("run_pipeline.content_analyzer.analyze_content_batch")
@patch("run_pipeline.youtube_collector.fetch_top_comments")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_attaches_fetched_comments_to_content_item_before_analysis(
    mock_load_config, mock_collect_youtube, mock_fetch_comments, mock_analyze_batch, tmp_path
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(tmp_path / "index.html"),
        "report_base_url": "",
        "slack_webhook_url": "",
    }
    mock_collect_youtube.return_value = [
        {
            "source": "youtube",
            "source_id": "v1",
            "title": "YouTube Trend",
            "body": "body",
            "url": "https://www.youtube.com/watch?v=v1",
            "score": 1000,
            "num_comments": 20,
            "published_at": "2026-09-15T00:00:00",
        }
    ]
    mock_fetch_comments.return_value = ["댓글1", "댓글2"]
    mock_analyze_batch.return_value = [
        {"content_item": mock_collect_youtube.return_value[0], "category": "음악", "summary": "요약", "success": True}
    ]

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        run_pipeline.run()

    analyzed_items = mock_analyze_batch.call_args.args[1]
    assert analyzed_items[0]["top_comments"] == ["댓글1", "댓글2"]
