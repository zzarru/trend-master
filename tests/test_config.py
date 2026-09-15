import os
from trend_pipeline import config


def test_load_config_reads_env_and_applies_defaults(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test-id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "test-agent")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("TREND_PIPELINE_DB_PATH", raising=False)

    cfg = config.load_config()

    assert cfg["reddit_client_id"] == "test-id"
    assert cfg["reddit_client_secret"] == "test-secret"
    assert cfg["reddit_user_agent"] == "test-agent"
    assert cfg["anthropic_api_key"] == "test-key"
    assert cfg["subreddits"] == config.DEFAULT_SUBREDDITS
    assert cfg["rss_feeds"] == config.DEFAULT_RSS_FEEDS
    assert cfg["db_path"] == "trend_pipeline.db"


def test_load_config_raises_when_required_keys_missing(monkeypatch):
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import pytest
    with pytest.raises(ValueError, match="REDDIT_CLIENT_ID"):
        config.load_config()
