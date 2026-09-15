from unittest.mock import MagicMock, patch

import run_pipeline


@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.rss_collector.collect_rss_entries")
@patch("run_pipeline.reddit_collector.collect_reddit_posts")
@patch("run_pipeline.reddit_collector.get_reddit_client")
@patch("run_pipeline.config.load_config")
def test_run_collects_saves_and_returns_summary(
    mock_load_config, mock_get_reddit_client, mock_collect_reddit, mock_collect_rss, mock_extract_batch
):
    mock_load_config.return_value = {
        "reddit_client_id": "id",
        "reddit_client_secret": "secret",
        "reddit_user_agent": "agent",
        "anthropic_api_key": "key",
        "subreddits": ["marketing"],
        "rss_feeds": ["https://example.com/rss"],
        "db_path": ":memory:",
    }
    mock_get_reddit_client.return_value = MagicMock()
    mock_collect_reddit.return_value = [
        {
            "source": "reddit",
            "source_id": "r1",
            "title": "Reddit Trend",
            "body": "body",
            "url": "https://reddit.com/r1",
            "score": 100,
            "num_comments": 10,
            "published_at": "2026-09-15T00:00:00",
        }
    ]
    mock_collect_rss.return_value = [
        {
            "source": "rss",
            "source_id": "rss1",
            "title": "RSS Trend",
            "body": "body",
            "url": "https://example.com/rss1",
            "score": None,
            "num_comments": None,
            "published_at": "2026-09-15T00:00:00",
        }
    ]
    mock_extract_batch.return_value = [
        {
            "content_item": mock_collect_reddit.return_value[0],
            "keywords": ["trend"],
            "usage_context": "ctx",
            "success": True,
        },
        {
            "content_item": mock_collect_rss.return_value[0],
            "keywords": None,
            "usage_context": None,
            "success": False,
        },
    ]

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary == {
        "reddit_collected": 1,
        "rss_collected": 1,
        "keywords_success": 1,
        "keywords_failed": 1,
    }


@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.rss_collector.collect_rss_entries")
@patch("run_pipeline.reddit_collector.collect_reddit_posts")
@patch("run_pipeline.reddit_collector.get_reddit_client")
@patch("run_pipeline.config.load_config")
def test_run_continues_when_reddit_collection_fails(
    mock_load_config, mock_get_reddit_client, mock_collect_reddit, mock_collect_rss, mock_extract_batch
):
    mock_load_config.return_value = {
        "reddit_client_id": "id",
        "reddit_client_secret": "secret",
        "reddit_user_agent": "agent",
        "anthropic_api_key": "key",
        "subreddits": ["marketing"],
        "rss_feeds": ["https://example.com/rss"],
        "db_path": ":memory:",
    }
    mock_get_reddit_client.return_value = MagicMock()
    mock_collect_reddit.side_effect = Exception("bad credentials")
    mock_collect_rss.return_value = [
        {
            "source": "rss",
            "source_id": "rss1",
            "title": "RSS Trend",
            "body": "body",
            "url": "https://example.com/rss1",
            "score": None,
            "num_comments": None,
            "published_at": "2026-09-15T00:00:00",
        }
    ]
    mock_extract_batch.return_value = [
        {
            "content_item": mock_collect_rss.return_value[0],
            "keywords": ["trend"],
            "usage_context": "ctx",
            "success": True,
        },
    ]

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    mock_collect_rss.assert_called_once()
    assert summary == {
        "reddit_collected": 0,
        "rss_collected": 1,
        "keywords_success": 1,
        "keywords_failed": 0,
    }
