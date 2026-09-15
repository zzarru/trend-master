from unittest.mock import MagicMock, patch

import run_pipeline


@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_collects_saves_and_returns_summary(
    mock_load_config, mock_collect_youtube, mock_extract_batch
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
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
    mock_extract_batch.return_value = [
        {
            "content_item": mock_collect_youtube.return_value[0],
            "keywords": ["trend"],
            "usage_context": "ctx",
            "success": True,
        }
    ]

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary == {
        "youtube_collected": 1,
        "keywords_success": 1,
        "keywords_failed": 0,
    }
    mock_collect_youtube.assert_called_once_with("yt-key", region_code="KR", max_results=25)


@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_continues_when_youtube_collection_fails(
    mock_load_config, mock_collect_youtube, mock_extract_batch
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
    }
    mock_collect_youtube.side_effect = RuntimeError("quota exceeded")
    mock_extract_batch.return_value = []

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary == {
        "youtube_collected": 0,
        "keywords_success": 0,
        "keywords_failed": 0,
    }


@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_redacts_api_key_from_failure_message(
    mock_load_config, mock_collect_youtube, mock_extract_batch, capsys
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
    }
    mock_collect_youtube.side_effect = RuntimeError(
        "403 Client Error: https://www.googleapis.com/youtube/v3/videos?"
        "part=snippet&key=SUPER_SECRET_VALUE&chart=mostPopular"
    )
    mock_extract_batch.return_value = []

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        run_pipeline.run()

    captured = capsys.readouterr()
    assert "SUPER_SECRET_VALUE" not in captured.out
    assert "유튜브 수집 실패" in captured.out
    assert "key=***REDACTED***" in captured.out
