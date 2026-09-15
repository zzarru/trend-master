from unittest.mock import MagicMock

from trend_pipeline import youtube_collector


def _make_response(items):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"items": items}
    return response


def test_collect_youtube_trending_builds_items_from_api_response(monkeypatch):
    api_items = [
        {
            "id": "abc123",
            "snippet": {
                "title": "Trending Video",
                "description": "some description",
                "publishedAt": "2026-09-15T00:00:00Z",
            },
            "statistics": {"viewCount": "150000", "commentCount": "320"},
        }
    ]
    mock_get = MagicMock(return_value=_make_response(api_items))
    monkeypatch.setattr(youtube_collector.requests, "get", mock_get)

    result = youtube_collector.collect_youtube_trending("fake-api-key", region_code="KR", max_results=25)

    assert len(result) == 1
    item = result[0]
    assert item["source"] == "youtube"
    assert item["source_id"] == "abc123"
    assert item["title"] == "Trending Video"
    assert item["body"] == "some description"
    assert item["url"] == "https://www.youtube.com/watch?v=abc123"
    assert item["score"] == 150000
    assert item["num_comments"] == 320
    assert item["published_at"] == "2026-09-15T00:00:00Z"

    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs["params"]["regionCode"] == "KR"
    assert call_kwargs["params"]["maxResults"] == 25
    assert call_kwargs["params"]["chart"] == "mostPopular"
    assert call_kwargs["params"]["key"] == "fake-api-key"


def test_collect_youtube_trending_handles_missing_statistics_gracefully(monkeypatch):
    api_items = [
        {
            "id": "noStats",
            "snippet": {"title": "No stats video"},
        }
    ]
    monkeypatch.setattr(youtube_collector.requests, "get", MagicMock(return_value=_make_response(api_items)))

    result = youtube_collector.collect_youtube_trending("fake-api-key")

    assert result[0]["score"] == 0
    assert result[0]["num_comments"] == 0
    assert result[0]["body"] == ""
    assert result[0]["published_at"] == ""


def test_fetch_top_comments_extracts_top_level_comment_text(monkeypatch):
    api_items = [
        {"snippet": {"topLevelComment": {"snippet": {"textDisplay": "첫 번째 댓글"}}}},
        {"snippet": {"topLevelComment": {"snippet": {"textDisplay": "두 번째 댓글"}}}},
    ]
    mock_get = MagicMock(return_value=_make_response(api_items))
    monkeypatch.setattr(youtube_collector.requests, "get", mock_get)

    result = youtube_collector.fetch_top_comments("fake-api-key", "abc123", max_results=5)

    assert result == ["첫 번째 댓글", "두 번째 댓글"]
    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs["params"]["videoId"] == "abc123"
    assert call_kwargs["params"]["maxResults"] == 5
    assert call_kwargs["params"]["key"] == "fake-api-key"


def test_fetch_top_comments_returns_empty_list_when_comments_disabled(monkeypatch):
    response = MagicMock()
    response.raise_for_status.side_effect = youtube_collector.requests.RequestException("403 comments disabled")
    monkeypatch.setattr(youtube_collector.requests, "get", MagicMock(return_value=response))

    result = youtube_collector.fetch_top_comments("fake-api-key", "abc123")

    assert result == []


def test_fetch_top_comments_skips_malformed_items(monkeypatch):
    api_items = [
        {"snippet": {"topLevelComment": {"snippet": {"textDisplay": "정상 댓글"}}}},
        {"snippet": {}},
    ]
    monkeypatch.setattr(
        youtube_collector.requests, "get", MagicMock(return_value=_make_response(api_items))
    )

    result = youtube_collector.fetch_top_comments("fake-api-key", "abc123")

    assert result == ["정상 댓글"]
