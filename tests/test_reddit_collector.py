from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from trend_pipeline import reddit_collector


def test_filter_surging_posts_keeps_only_high_relative_score():
    posts = [
        {"subreddit": "marketing", "score": 10},
        {"subreddit": "marketing", "score": 12},
        {"subreddit": "marketing", "score": 100},  # surges above 2x avg of ~40.7
    ]

    result = reddit_collector.filter_surging_posts(posts, min_score=5, surge_multiplier=2.0)

    assert result == [{"subreddit": "marketing", "score": 100}]


def test_filter_surging_posts_applies_min_score_floor():
    posts = [
        {"subreddit": "trends", "score": 1},
        {"subreddit": "trends", "score": 2},
    ]

    result = reddit_collector.filter_surging_posts(posts, min_score=5, surge_multiplier=2.0)

    assert result == []


def _make_submission(post_id, title, score, num_comments, created_utc, selftext="", url="https://x.com"):
    submission = MagicMock()
    submission.id = post_id
    submission.title = title
    submission.selftext = selftext
    submission.url = url
    submission.score = score
    submission.num_comments = num_comments
    submission.created_utc = created_utc
    return submission


def test_collect_reddit_posts_builds_items_and_filters_by_lookback():
    now = datetime.now(timezone.utc)
    recent = _make_submission("p1", "Recent surging post", 200, 50, now.timestamp())
    old = _make_submission("p2", "Old post", 500, 100, (now - timedelta(days=5)).timestamp())
    baseline = _make_submission("p3", "Baseline post", 5, 1, now.timestamp())

    mock_client = MagicMock()
    mock_client.subreddit.return_value.new.return_value = [recent, old, baseline]

    result = reddit_collector.collect_reddit_posts(mock_client, ["marketing"], lookback_hours=24)

    assert len(result) == 1
    item = result[0]
    assert item["source"] == "reddit"
    assert item["source_id"] == "p1"
    assert item["title"] == "Recent surging post"
    assert item["score"] == 200
    assert item["num_comments"] == 50
    assert item["subreddit"] == "marketing"
